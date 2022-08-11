import os
import concurrent.futures
import requests
import pandas as pd
import streamlit as st 
import streamlit.components.v1 as components
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from stqdm import stqdm
from functools import partial
from dotenv import load_dotenv
from twarc import Twarc2, expansions

from streamlit_twitter_feed import streamlit_twitter_feed

load_dotenv()


from tweet_processing import StreamTweetProcessor, get_time_interval, lookup_users_by_username
from tweet_processing import get_user_following, pull_tweets

data_dir = "data/current"



def lookup_users(usernames):
    """
    
        usernames (list): list of usernames to lookup

    Returns:
        successful_users (dict): dict of metadata for the user as retreived from twitter
        error_usernames (list): list of usernames that were not successfully found
    """
    user_gen = twarc_client.user_lookup(users=usernames, usernames=True)
    successful_users = {}

    successful_usernames = []
    error_usernames = []
    for res in user_gen:
        if "data" in res:
            for user_data in res["data"]:
                successful_usernames.append(user_data["username"])
                successful_users[user_data["username"]] = user_data
        if "errors" in res:
            for error in res["errors"]:
                error_usernames.append(error["value"])
    return successful_users, error_usernames

twarc_client = Twarc2(
    consumer_key=os.environ["consumer_key"], 
    consumer_secret=os.environ["consumer_secret"],
    access_token=os.environ["access_token"], 
    access_token_secret=os.environ["access_token_secret"]
)

if "seed_accounts" not in st.session_state:
    st.session_state.seed_accounts = {}
    st.session_state.error_user_group = set()
    # st.session_state.recced_users_dict = {}
    # st.session_state.selected_recommended_users = set()
    st.session_state.current_feed_users_dict = {}

def checkbox_func(selected_username):
    print('CHECKBOX CLICKED')
    print(st.session_state.recced_users_dict)

    if st.session_state.recced_users_dict[selected_username] is False:
        st.session_state.selected_recommended_users.add(selected_username)
    else: 
        st.session_state.selected_recommended_users.remove(selected_username)



def build_group_list():
    print(f"I'm in build group list with input {st.session_state.user_text_key}")
    print(f"current user group session: {st.session_state.seed_accounts}")

    usernames = [i.strip() for i in st.session_state.user_text_key.split(",")]
    print("USERNAMES")
    print(usernames)
    usernames = [i for i in usernames if len(i)>0]
    if len(usernames) < 1:
        return [], []
    successful_userdata, errors = lookup_users(usernames) # TWITTER API BEING A BITCH JUST PUT FAKE DATA FOR NOW...

    # success = ["nicktorba", "rhyslindmark"]
    # errors = ["yoyoufakeadsf", "nowaysfdsfdsimreal"]

    for username, user_data in successful_userdata.items():
        follows_fpath = os.path.join(data_dir, "following", f"{username}_following.csv")
        if os.path.exists(follows_fpath):
            df_following = pd.read_csv(follows_fpath)
        else: 
            df_following = get_user_following(twarc_client, username)
            df_following.to_csv(follows_fpath, index=False)
        st.session_state.seed_accounts[username] = {}
        st.session_state.seed_accounts[username]["following"] = df_following
        st.session_state.seed_accounts[username]["user_data"] = user_data
    
    for username in errors: 
        # st.warning(f"User '{username}' not found, please check your entry and try again")
        st.session_state.error_user_group.add(username)


@st.cache
def recommend_by_following(df_following):
    ## Get a set of usernames that each seed account follows

    # st.subheader("Account Recommendation by follows")
    # st.markdown(
    #     """
    #     This below, we will show accounts that are followed by some number of seed accounts. **You control the minimum number of accounts.**

    #     For example, most groups have three accounts. If you set the input field `minimum number of seed accounts followed by` to 3, you will only 
    #     see recommended accounts who are followed by __all three seed accounts__. You can drop the number to 2 to see many more recommendations. 

        
    #     Under that, you can control how many recomendations to show (default is 5). They are **sorted by follower_count**, which means that the top recommendations are the accounts with the least amount of followers. 
        
    #     """
    # )
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
    return overlap_df 
    # NUM_SEED_ACCOUNTS = 3
    # minimum_seed_accounts = st.number_input(
    #     "minimum number seed accounts followed by",
    #     min_value=1, 
    #     max_value=df_following["referencer.username"].nunique()+1, 
    #     value=df_following["referencer.username"].nunique()
    # )
    # present_df = overlap_df[overlap_df["num_stream_users"]>=minimum_seed_accounts].sort_values("num_followers_of_followed")
    # max_show = st.slider("num recommendations to show", min_value=1, max_value=present_df.shape[0], value=5)
    # st.write(f"showing {max_show} recommended accounts, sorted by follower count")
    # for index, row in present_df.iloc[:max_show].iterrows():
    #     st.markdown(f"![profile_image]({row.profile_image_url}), {row['followed.username']}, num_followers={row.num_followers_of_followed}, [profile_link]({row.profile_link})", unsafe_allow_html=True)

def get_feed(start_time, selected_rows):
    print("woah")
    fetch_usernames = list(st.session_state.seed_accounts) + [i["username"] for i in selected_rows] #list(st.session_state.selected_recommended_users)
    # fetch_usernames = [username for username in usernames if username not in st.session_state.current_feed_users_dict]
    twitter_fetch_usernames = []
    for i_username in fetch_usernames: 
        tweets_fpath = os.path.join(data_dir, "tweets", f"{i_username}_tweets.csv")
        ref_tweets_fpath = os.path.join(data_dir, "ref_tweets", f"{i_username}_ref_tweets.csv")
        if os.path.exists(tweets_fpath):
            st.session_state.current_feed_users_dict[i_username] = {}
            st.session_state.current_feed_users_dict[i_username]["tweets"] = pd.read_csv(tweets_fpath)
        if os.path.exists(ref_tweets_fpath):
            st.session_state.current_feed_users_dict[i_username]["ref_tweets"] = pd.read_csv(ref_tweets_fpath)
        else: 
            twitter_fetch_usernames.append(i_username)
   # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    #     futures = {executor.submit(pull_tweets, twarc_client, username, start_time=start_time): username for username in twitter_fetch_usernames}
    #     progress_bar = stqdm
    #     for future in progress_bar(concurrent.futures.as_completed(futures), total=len(usernames)):
    #         i_username, i_df_tweets, i_df_ref_tweets = future.result()
    #         st.session_state.current_feed_users_dict[i_username] = {}
    #         st.session_state.current_feed_users_dict[i_username]["start_time"] = start_time
    #         st.session_state.current_feed_users_dict[i_username]["tweets"] = i_df_tweets
    #         st.session_state.current_feed_users_dict[i_username]["ref_tweets"] = i_df_ref_tweets
    #         tweets_fpath = os.path.join(data_dir, "tweets", f"{username}_tweets.csv")
    #         ref_tweets_fpath = os.path.join(data_dir, "ref_tweets", f"{username}_ref_tweets.csv")
    #         i_df_tweets.to_csv(tweets_fpath, index=False)
    #         i_df_ref_tweets.to_csv(ref_tweets_fpath, index=False)

    progress_bar = stqdm
    for i_username in twitter_fetch_usernames:
        print(f"fetching tweets for {i_username} since {start_time}")
        i_username, i_df_tweets, i_df_ref_tweets = pull_tweets(twarc_client, i_username, start_time=start_time)
        if i_df_tweets is None: 
            print(f"no tweets found for {i_username}")
            continue
        print(f"{i_df_tweets.shape[0]} tweets for {i_username}")
        st.session_state.current_feed_users_dict[i_username] = {}
        st.session_state.current_feed_users_dict[i_username]["start_time"] = start_time
        st.session_state.current_feed_users_dict[i_username]["tweets"] = i_df_tweets
        st.session_state.current_feed_users_dict[i_username]["ref_tweets"] = i_df_ref_tweets
        tweets_fpath = os.path.join(data_dir, "tweets", f"{i_username}_tweets.csv")
        ref_tweets_fpath = os.path.join(data_dir, "ref_tweets", f"{i_username}_ref_tweets.csv")
        if i_df_tweets is not None:
            i_df_tweets.to_csv(tweets_fpath, index=False)
        if i_df_ref_tweets is not None:
            i_df_ref_tweets.to_csv(ref_tweets_fpath, index=False)

with st.expander("Search for Seed Users", expanded=True):
    still_creating_group = True
    selected = st.text_input("search for users", "artirkel,celinehalioua,laurademing", on_change=build_group_list, key="user_text_key")
    # button_clicked = st.button("Create New Group with currently selected users")
    st.write(f"current seed users: {list(st.session_state.seed_accounts.keys())}")
    if len(st.session_state.error_user_group):
        st.warning(f"errors adding following users: {list(st.session_state.error_user_group)}. Please check your entry and try again for these")


with st.sidebar:
    rec_method = st.radio("recommendation method", ["follows", "interaction"])
    include_tweets_from_seed_accounts = st.checkbox("Include Tweets from Seed Accounts?")
    tweet_types = ['reply', 'qt,mention', 'rt', 'rt,mention', 'self-reply,mention',
       'standalone,mention', 'qt,reply', 'self-reply', 'standalone', 'qt']
    selected_tweet_types = st.multiselect(
        'which types of tweets to include',
        tweet_types,
        default=tweet_types
    )

col1, col2 = st.columns(2)

with col1:
    st.subheader("Seed Users")
    # dictionary checkbox trick from: https://stackoverflow.com/questions/66718228/select-multiple-options-in-checkboxes-in-streamlit/66738130#66738130
    # seeded_users = {
    #     username: st.checkbox(username, True) for username in st.session_state.seed_accounts
    # }

    data = {"username": list(st.session_state.seed_accounts)}
    df = pd.DataFrame(data)
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_selection(selection_mode='multiple', use_checkbox=True, pre_selected_rows=list(df.index))
    gd.configure_default_column(min_column_width=2)
    # gd.configure_auto_height(True)
    gridoptions = gd.build()
    seed_grid_table = AgGrid(
        df, 
        height=115, 
        fit_columns_on_grid_load=True,
        gridOptions=gridoptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
    )

    selected_seed_rows = seed_grid_table["selected_rows"]

    st.subheader("Recommended Users")
    df_following_list = [v["following"] for k, v in st.session_state.seed_accounts.items()]
    if len(df_following_list):
        if rec_method == "follows":
            df_following = pd.concat(df_following_list)
            overlap_df = recommend_by_following(df_following)
        else: 
            raise Exception("Not implemented yet...")

        present_df = overlap_df[overlap_df["num_stream_users"]>=3].sort_values(["num_stream_users","num_followers_of_followed"])
        st.write(f"{present_df.shape[0]} accounts recommended")
        # st.write(f"currently selected users = {st.session_state.selected_recommended_users}")
        # st.session_state.recced_users_dict = {
        #     row["followed.username"]: st.checkbox(
        #         f"{row['followed.username']}, num_seed_users_followed_by={row['num_stream_users']}, num_followers={row['num_followers_of_followed']}", 
        #         on_change=partial(checkbox_func, selected_username=row["followed.username"]),
        #         ) for _, row in present_df.iterrows()
        # }

        data = {
            "username": [],
            "num_followers": [],
            "num_seed_users_followed_by": [], 
        }
        for _, row in present_df.iterrows():
            data["username"].append(row['followed.username'])
            data["num_seed_users_followed_by"].append(row["num_stream_users"])
            data["num_followers"].append(row["num_followers_of_followed"])

        df = pd.DataFrame(data)
        df = df[["username", "num_followers", "num_seed_users_followed_by"]]
        gd = GridOptionsBuilder.from_dataframe(df)
        gd.configure_selection(selection_mode='multiple', use_checkbox=True)
        gridoptions = gd.build()

        grid_table = AgGrid(df, height=250, gridOptions=gridoptions,
                            update_mode=GridUpdateMode.SELECTION_CHANGED)

        st.write('## Selected')
        selected_rows = grid_table["selected_rows"]
        # st.write(selected_rows[0])
        df = pd.DataFrame(selected_rows)
        st.dataframe(df)#, "num_seed_users_followed_by", "num_followers"]])

_, start_time = get_time_interval(hours=24*28)

with col2:
    st.subheader("your feed")
    
    if st.checkbox("generate_feed"):
        get_feed(start_time, selected_seed_rows+selected_rows)
        feed_usernames = [i["username"] for i in selected_seed_rows+selected_rows]
        df_feed = None 
        for username, user_data in st.session_state.current_feed_users_dict.items():
            if username not in feed_usernames:
                continue
            if df_feed is None: 
                df_feed = user_data["tweets"]
            else: 
                df_feed = pd.concat([df_feed, user_data["tweets"]])
        if df_feed is not None:
            df_feed["created_at"] = pd.to_datetime(df_feed["created_at"], utc=True)
            # st.write(df_feed["author.username"].value_counts())
            tweets = df_feed.sort_values(["created_at"], ascending=False)
            def filter_by_quantile(group, metric, quantile):
                thresh = group[f"public_metrics.{metric}"].quantile(quantile)
                return group[group[f"public_metrics.{metric}"] > thresh]

            # tweets = df_feed.groupby(["author.username"]).apply(lambda x: filter_by_quantile(x, "like_count", 0.9)).drop("author.username", axis=1).reset_index()

            tweets["created_at"] = [i.isoformat() for i in tweets["created_at"].to_list()]

            tweets = tweets[tweets["tweet_type"].isin(selected_tweet_types)]

            # st.write(tweets["author.username"].value_counts())
            st.dataframe(tweets["author.username"].value_counts())
            tweets = tweets[
                [
                    "id",
                    "tweet_link",
                    "text", 
                    "author.username", 
                    "created_at", 
                    "author.profile_image_url", 
                    "author.name", 
                    "public_metrics.like_count", 
                    "public_metrics.reply_count", 
                    "public_metrics.quote_count", 
                    "public_metrics.retweet_count"
                ]
            ].to_dict("records")
            num_clicks = streamlit_twitter_feed("World", tweets, key="unique")

st.markdown("""<hr style="height:10px;border:none;color:#333;background-color:#333;" /> """, unsafe_allow_html=True)

