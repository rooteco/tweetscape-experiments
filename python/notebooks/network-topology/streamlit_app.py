from dis import dis
import os
from dotenv import load_dotenv
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from minio import Minio
from twarc import Twarc2, expansions
from tweet_processing import StreamTweetProcessor, get_time_interval, lookup_users_by_username

load_dotenv()

class TweetHtml(object):
    def __init__(self, s, embed_str=False):
        if not embed_str:
            # Use Twitter's oEmbed API
            # https://dev.twitter.com/web/embedded-tweets
            api = "https://publish.twitter.com/oembed?url={}".format(s)
            response = requests.get(api)
            self.text = response.json()["html"]
        else:
            self.text = s

    def component(self):
        return components.html(self.text, scrolling=True, height=250)

def explore_feed(df_following, df_tweets, df_ref_tweets):
    st.header("Exploring Tweets from Seed Accounts")
    num_days_for_feed = st.number_input(
        "Number of days to include for feed",
        min_value=1, 
        max_value=1000, 
        value=10
    )
    end_time, start_time = get_time_interval(hours=24*num_days_for_feed)
    tweets_range = df_tweets[df_tweets["created_at"] > start_time]
    tweets_range = tweets_range[~tweets_range["tweet_type"].str.contains("rt")]
    tweet_types = list(df_tweets["tweet_type"].unique())
    selected_tweet_types = st.multiselect(
        'which types of tweets to include in feed...',
        tweet_types,
        default=tweet_types
    )
    tweets_choose_type = tweets_range[tweets_range["tweet_type"].isin(selected_tweet_types)]  
    st.text(f"{tweets_choose_type.shape[0]} tweets in range and type from seed accounts. Here is the breakdown of which accounts the tweets are from:")
    st.dataframe(tweets_choose_type["author.username"].value_counts())
    def filter_by_quantile(group, metric, quantile):
        thresh = group[f"public_metrics.{metric}"].quantile(quantile)
        return group[group[f"public_metrics.{metric}"] > thresh]

    st.header("Tweet by metric quartile, relative to user")
    metric = st.selectbox("metric to sort by", ["like_count", "retweet_count", "quote_count", "reply_count"])
    quantile = st.slider("quantile", min_value=0, max_value=100, step=5, value=90)
    quantile /= 100
    tweets_quantile = tweets_choose_type.groupby(["author.username"]).apply(lambda x: filter_by_quantile(x, metric, quantile)).drop("author.username", axis=1).reset_index()
    st.dataframe(tweets_quantile)
    st.write(f"showing {tweets_quantile.shape[0]}/{tweets_range.shape[0]} tweets above the {quantile*100} quantile for {metric} in the last {num_days_for_feed} days")
    st.dataframe(tweets_quantile["author.username"].value_counts())
    for index, row in tweets_quantile.sort_values(["author.username", f"public_metrics.{metric}"], ascending=False).iterrows():
        st.write("------------")
        st.write(f"tweet (type={row.tweet_type}) by {row['author.username']} with {metric}={row[f'public_metrics.{metric}']}")
        TweetHtml(row.tweet_link).component() #just this line shows the component, you don't need to st.write it        

def recommend_by_following(df_following):
    ## Get a set of usernames that each seed account follows
    users_following = {}
    for user in df_following["referencer.username"].unique().tolist():
        users_following[user] = set(df_following[df_following["referencer.username"] == user]["username"].tolist())
        
    ## index will be useful to access metadata (followers_count) about these accounts
    df_following.set_index("username", inplace=True)

    ### Create a dataframe that will show the following_overlap for each of the accounts followed by at least 1 of the seed accounts. 
    ### We are most interested in the intersection among the following of those accounts
    ### If the accounts are picked well, they will likely have interesting intersection among their shared interest

    following_overlap = {}

    for stream_user, following in users_following.items():
        for followed_user in following: 
            following_overlap.setdefault(followed_user, []).append(stream_user)

    df_data = []

    for followed_user, stream_users in following_overlap.items():
        num_followers_of_followed = df_following.loc[followed_user]["public_metrics.followers_count"]
        profile_image_url = df_following.loc[followed_user]["profile_image_url"]
        if isinstance(num_followers_of_followed, pd.Series):
            num_followers_of_followed = num_followers_of_followed.iloc[0]
            profile_image_url = profile_image_url.iloc[0]
        df_data.append([profile_image_url, followed_user, stream_users, len(stream_users), num_followers_of_followed, f"https://twitter.com/{followed_user}"])
        
    overlap_df = pd.DataFrame(df_data, columns=["profile_image_url", "followed.username", "stream_users", "num_stream_users", "num_followers_of_followed", "profile_link"])
    overlap_df["num_stream_users"].value_counts()


    NUM_SEED_ACCOUNTS = 3
    minimum_seed_accounts = st.number_input(
        "minimum number seed accounts followed by",
        min_value=1, 
        max_value=df_following["referencer.username"].nunique()+1, 
        value=df_following["referencer.username"].nunique()
    )
    present_df = overlap_df[overlap_df["num_stream_users"]>=minimum_seed_accounts].sort_values("num_followers_of_followed")
    max_show = st.slider("num recommendations to show", min_value=1, max_value=present_df.shape[0], value=5)
    st.header(f"Accounts followed by at least {minimum_seed_accounts} seed users")
    st.write(f"showing {max_show} recommended accounts, sorted by follower count")
    for index, row in present_df.iloc[:max_show].iterrows():
        st.markdown(f"![profile_image]({row.profile_image_url}), {row['followed.username']}, num_followers={row.num_followers_of_followed}, [profile_link]({row.profile_link})", unsafe_allow_html=True)
    
def recommend_by_interactions(df_following, df_tweets, df_ref_tweets):
    st.header("Which Accounts have multiple Seed Accounts Interacted with in the last X weeks?")
    num_weeks = st.number_input(
        "Number of weeks to include",
        min_value=1, 
        max_value=1000, 
        value=4
    )
    end_time, start_time = get_time_interval(hours=24*7*num_weeks)

    df_x_tweets = df_tweets[df_tweets["created_at"]>start_time]
    df_x_ref_tweets = df_ref_tweets[df_ref_tweets["created_at"]>start_time]

    # reply_tweets = df_x_tweets[df_x_tweets["referenced_tweets.replied_to.id"].notna()]
    # no_self_replies = reply_tweets[~reply_tweets["tweet_type"].str.contains("self-reply")]

    interaction_columns = ["referenced_tweets.replied_to.id", "referenced_tweets.quoted.id", "referenced_tweets.retweeted.id"]

    interaction_overlap = {}
    for i_column in interaction_columns: 
        for author_username, referenced_id_, tweet_id in zip(df_x_tweets["author.username"].tolist(), df_x_tweets[i_column].tolist(), df_x_tweets["id"].tolist()):
            ref_ = df_ref_tweets[df_ref_tweets["id"] == referenced_id_]
            if ref_.shape[0] > 0:
                # interaction_overlap.setdefault(ref_.iloc[0]["author.username"], set()).add(author_username)
                interaction_overlap.setdefault(ref_.iloc[0]["author.username"], {"stream_users":set(), "interaction_ids": []}) #.add(author_username)
                interaction_overlap[ref_.iloc[0]["author.username"]]["stream_users"].add(author_username)
                interaction_overlap[ref_.iloc[0]["author.username"]]["interaction_ids"].append(tweet_id)


    df_data = []
    for interacted_user, interaction_data in interaction_overlap.items():
        df_data.append(
            [
                interacted_user, 
                interaction_data["stream_users"],
                len(interaction_data["stream_users"]),
                interaction_data["interaction_ids"], 
                f"https://twitter.com/{interacted_user}",
            ]
        )
    overlap_df = pd.DataFrame(
        df_data, 
        columns=[
            "interacted.username", 
            "stream_users", 
            "num_stream_users", 
            "interaction_ids",
            "profile_link", 
        ]
    )
    minimum_seed_accounts_interactions = st.number_input(
        "minimum number seed accounts referenced by",
        min_value=1, 
        max_value=df_following["referencer.username"].nunique(), 
        value=df_following["referencer.username"].nunique()-1
    )
    filtered_overlap_df = overlap_df[overlap_df["num_stream_users"]>=minimum_seed_accounts_interactions]

    usernames = filtered_overlap_df["interacted.username"].tolist()
    if len(usernames) > 0:
        print("usernames")
        print(usernames)
        user_df = lookup_users_by_username(twarc_client, usernames).set_index("username")
    
    filtered_overlap_df["num_followers_of_interacted"] = [user_df.loc[username]["public_metrics.followers_count"] for username in filtered_overlap_df["interacted.username"].tolist()]
    filtered_overlap_df["profile_image_url_of_interacted"] = [user_df.loc[username]["profile_image_url"] for username in filtered_overlap_df["interacted.username"].tolist()]

    cur_val = 5 if filtered_overlap_df.shape[0] > 5 else filtered_overlap_df.shape[0]
    st.write(f"Showing accounts that at least {minimum_seed_accounts_interactions} seed accounts have interacted with in the last {num_weeks} weeks")
    max_show = st.slider("num recommendations to show, based on interactions", min_value=1, max_value=filtered_overlap_df.shape[0], value=cur_val)
    st.write(f"showing {max_show} recommended accounts based on interaction, sorted by follower count")
    for index, row in filtered_overlap_df.iloc[:max_show].iterrows():
        st.markdown(f"![profile_image]({row.profile_image_url_of_interacted}), {row['interacted.username']}, num_followers={row.num_followers_of_interacted}, [profile_link]({row.profile_link})", unsafe_allow_html=True)

def main(group_name="CA-Abundance-Economy"):
    df_following, df_tweets, df_ref_tweets = tp.remote_read_seed_data(group_name) 
    recommend_by_following(df_following)
    recommend_by_interactions(df_following, df_tweets, df_ref_tweets)
    explore_feed(df_following, df_tweets, df_ref_tweets)

twarc_client = Twarc2(
    consumer_key=os.environ["consumer_key"], 
    consumer_secret=os.environ["consumer_secret"],
    access_token=os.environ["access_token"], 
    access_token_secret=os.environ["access_token_secret"]
)

minio_client = Minio(
    "experiment-data-minio.internal:9000",
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False
)

tp = StreamTweetProcessor(twarc_client=twarc_client, minio_client=minio_client, bucket="stream-seeding")


st.header("Select Previously Available Group")
available_groups = ["create new group"]
for obj in minio_client.list_objects("stream-seeding", recursive=False):
    available_groups.append(obj.object_name)
group = st.selectbox("Select Pre-fetched group below... Leave blank if you want to create a new group", available_groups)


if "new_user_group" not in st.session_state:
    st.session_state.new_user_group = set()

def build_group_list():
    print(f"I'm in build group list with input {st.session_state.user_text_key}")
    print(f"current user group session: {st.session_state.new_user_group}")

    res = lookup_users_by_username(twarc_client, [st.session_state.user_text_key])
    if "errors" in res: 
        print(f"User '{st.session_state.user_text_key}' not found, please check your entry and try again")
        st.warning(f"User '{st.session_state.user_text_key}' not found, please check your entry and try again")
    else: 
        st.session_state.new_user_group.add(st.session_state.user_text_key)

if group != "create new group": 
    main(group_name=group[:-1])
else: 
    st.header("Create a new Group")
    still_creating_group = True

    selected = st.text_input("search for users", "", on_change=build_group_list, key="user_text_key")
    button_clicked = st.button("Create New Group with currently selected users")
    st.write(f"your users to create group with: {st.session_state.new_user_group}")

