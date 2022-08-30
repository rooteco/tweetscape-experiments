import os
import concurrent.futures
import requests
from time import sleep
import pandas as pd
import streamlit as st 
import streamlit.components.v1 as components
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from stqdm import stqdm
from minio import Minio, error
import redis
from functools import partial
from dotenv import load_dotenv
from twarc import Twarc2
import tweepy

from streamlit_twitter_feed import streamlit_twitter_feed, _RELEASE
import json 
load_dotenv()

from io import BytesIO


from tweet_processing import StreamTweetProcessor, get_time_interval, lookup_users_by_username
from tweet_processing import get_user_following, pull_tweets


from streams import BUCKET, Stream 

data_dir = "data/current"

REDIS_CLIENT = redis.Redis(port=6370, password=os.environ["REDIS_PASSWORD"])

host = "localhost:9000" if not _RELEASE else "experiment-data-minio.internal:9000"
MINIO_CLIENT = Minio(
    host, 
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False
)

CONSUMER_KEY = os.environ["consumer_key"]
CONSUMER_SECRET = os.environ["consumer_secret"]
AUTH = tweepy.OAuth1UserHandler(CONSUMER_KEY, CONSUMER_SECRET,callback="oob")

SKIP_PIN_AUTH = True  

def minio_read_json(path):
    read_res = MINIO_CLIENT.get_object(BUCKET, path)
    return json.loads(read_res.data)


def minio_read_csv(path):
    __docstring = """
    replace calls to df.to_csv
    """
    read_res = MINIO_CLIENT.get_object(
        BUCKET, 
        path
    )
    df = pd.read_csv(BytesIO(read_res.data))
    return df

def minio_path_exists():
    __docstring = """
    replace calls to os.path.exists
    """
    pass 

def init_twarc_client():
    if SKIP_PIN_AUTH:
        return Twarc2(
            consumer_key=os.environ["consumer_key"], 
            consumer_secret=os.environ["consumer_secret"],
            access_token=os.environ["access_token"],
            access_token_secret=os.environ["access_token_secret"],
        )
    return Twarc2(
            consumer_key=os.environ["consumer_key"], 
            consumer_secret=os.environ["consumer_secret"],
            access_token=st.session_state.oauth_objects["access_token"],
            access_token_secret=st.session_state.oauth_objects["access_token_secret"],
        )

def set_oauth_verifier():
    ACCESS_TOKEN, ACCESS_TOKEN_SECRET = AUTH.get_access_token(st.session_state.oauth_verifier_verifier_input)
    AUTH.set_access_token(ACCESS_TOKEN,ACCESS_TOKEN_SECRET)
    st.session_state.oauth_objects["access_token"] = ACCESS_TOKEN
    st.session_state.oauth_objects["access_token_secret"] = ACCESS_TOKEN_SECRET

def add_seed_users():
    usernames = [i.strip() for i in st.session_state.user_text_key.split(",")]
    usernames = [i for i in usernames if len(i)>0]
    if len(usernames) < 1:
        return [], []
    st.session_state.stream.add_seed_users(usernames, init_twarc_client())

def update_load_stream_name():
    import time
    
    print("LOADING TIMEs")

    start = time.time()
    loaded_from_redis = REDIS_CLIENT.hgetall(st.session_state.load_stream_name_input)
    end = time.time()
    print(f"it took {end-start} seconds to load {st.session_state.load_stream_name_input} from redis")

    start = time.time()
    st.session_state.stream.load_from_json_safe_dict(loaded_from_redis)
    end=time.time()
    print(f"it took {end-start} seconds convert dtypes of {st.session_state.load_stream_name_input}")

    st.session_state.load_stream_name = st.session_state.load_stream_name_input
    ### Keeping this as their own state vars until I can debug reload issues more... 
    st.session_state.all_recommended_users = st.session_state.stream.all_recommended_users
    st.session_state.selected_recommended_users = st.session_state.stream.selected_recommended_users

def update_load_stream_name_after_save():
    st.session_state.available_streams.append(st.session_state.stream.get_name())
    st.session_state.load_stream_name_input = st.session_state.stream.get_name()
    
def load_stream(stream_name):
    stream_config = minio_read_json(os.path.join(stream_name, "stream_config.json"))
    for username in stream_config["seed_accounts"].keys():
        following_fpath = os.path.join(stream_name, "seed_accounts_following", f"{username}_following.csv")
        df_following = minio_read_csv(following_fpath)
        stream_config["seed_accounts"][username]["following"] = df_following
    return Stream(
        end_time=stream_config["end_time"],
        start_time=stream_config["start_time"],
        seed_accounts=stream_config["seed_accounts"],
        recommended_users=stream_config["recommended_users"],
        selected_recommended_users=stream_config["selected_recommended_users"]
    )

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
            following_overlap.setdefault(followed_user, []).append(stream_user) # add the stream user that follows this account

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
    
if "oauth_objects" not in st.session_state:
    if SKIP_PIN_AUTH:
        st.session_state.oauth_objects = {"a": "yo"}
    else: 
        st.session_state.oauth_objects = {}
if "stream" not in st.session_state: 
    end_time, start_time = get_time_interval(hours=24*14)
    st.session_state.stream = Stream(
            end_time,
            start_time
        )
if "available_streams" not in st.session_state:
    st.session_state.available_streams = ["start new"] + [i.decode("utf-8") for i in REDIS_CLIENT.scan_iter()]

if "load_stream_name" not in st.session_state:
    st.session_state.load_stream_name = "start new"
if "all_recommended_users" not in st.session_state:
    st.session_state.all_recommended_users = []
if "selected_recommended_users" not in st.session_state:
    print("RESTING SELECTED")
    st.session_state.selected_recommended_users = []
else: 
    print("here is selected users list form the or else of the initializer")
    print(st.session_state.selected_recommended_users)

# with st.expander("Choose a Stream to Start With", expanded=False):
st.selectbox(
    "load stream", 
    st.session_state.available_streams,
    on_change=update_load_stream_name,
    key="load_stream_name_input"      
)

# with st.expander("Search for and Add Seed Users", expanded=False):
if not len(st.session_state.oauth_objects):
    st.write("Login with twitter to create new streams!")
    if st.button("Sign In With Twitter"):
        st.text("Go to this link in another tab and grab the pin: ")
        st.write(AUTH.get_authorization_url())
        verifier = st.text_input("Enter PIN: ", False, type="password", on_change=set_oauth_verifier, key="oauth_verifier_verifier_input")
else: 
    selected = st.text_input("search for users", value="", on_change=add_seed_users, key="user_text_key")
    st.write(f"current seed users: {list(st.session_state.stream.seed_accounts.keys())}")
    st.write(f"current stream time frame: `{st.session_state.stream.start_time}` to `{st.session_state.stream.end_time}`")
    if len(st.session_state.stream.last_failed_lookup):
        st.warning(f"errors adding following users: {list(st.session_state.stream.last_failed_lookup)}. Please check your entry and try again for these")

with st.sidebar:
    rec_method = st.radio("recommendation method", ["follows", "interaction"])
    tweet_types = ['reply', 'qt,mention', 'rt', 'rt,mention', 'self-reply,mention',
    'standalone,mention', 'qt,reply', 'self-reply', 'standalone', 'qt']
    selected_tweet_types = st.multiselect(
        'which types of tweets to include',
        tweet_types,
        default=tweet_types
    )


def display_seed_accounts():
    st.subheader("Seed Users")
    data = {"username": list(st.session_state.stream.seed_accounts.keys())}
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
    # selected_seed_rows = seed_grid_table["selected_rows"]

def display_recommendations():
    st.subheader("Recommended Users")
    if len(st.session_state.stream.seed_accounts) < 2:
        st.write("Add at least 2 seed accounts to generate a feed")
    else: 
        df_following_list = [v["following"] for k, v in st.session_state.stream.seed_accounts.items()]
        if len(df_following_list):
            if rec_method == "follows":
                df_following = pd.concat(df_following_list)
                overlap_df = recommend_by_following(df_following)
            else: 
                raise Exception("Not implemented yet...")

            num_stream_users = st.slider("number of stream users", min_value=1, max_value=len(df_following_list), value=len(df_following_list))
            present_df = overlap_df[overlap_df["num_stream_users"]>=num_stream_users].sort_values(["num_stream_users","num_followers_of_followed"])
            st.write(f"{present_df.shape[0]} accounts recommended")

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
            df["username"] = [i.lower() for i in df["username"].to_list()]

            # DEBUG
            # st.write(f"pre selected index: {list(df[df['username'].isin(st.session_state.selected_recommended_users)].index)}")
            # st.write(f"selected reccs = {st.session_state.selected_recommended_users}")


            print("here is the pre selected index")
            print(
                list(df[df["username"].isin(st.session_state.selected_recommended_users)].index)
            )
            gd.configure_selection(
                selection_mode='multiple', 
                use_checkbox=True, 
                pre_selected_rows=list(df[df["username"].isin(st.session_state.selected_recommended_users)].index)
            )
            gridoptions = gd.build()
            grid_table = AgGrid(
                df, 
                height=250, 
                gridOptions=gridoptions,
                update_mode=GridUpdateMode.SELECTION_CHANGED
            )
            selected_rows = grid_table["selected_rows"]
            st.session_state.SELECTED_ROWS = [i["username"] for i in selected_rows]
        if st.button("Save Current Stream", on_click=update_load_stream_name_after_save): 
            # TODO: Save twitter List: https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/create-manage-lists/api-reference/post-lists-create
            REDIS_CLIENT.hmset(st.session_state.stream.get_name(), st.session_state.stream.to_json_safe_dict())

## COLUMNS
if len(st.session_state.stream.seed_accounts):
    if st.session_state.load_stream_name != "start new":
        st.write(f"loaded starting stream: {st.session_state.stream.get_name()}")
    col1, col2 = st.columns(2)
    with col1:
        display_seed_accounts()
        display_recommendations()
    with col2:
        if len(st.session_state.stream.seed_accounts) < 2:
            st.write("Add at least 2 seed accounts to generate a feed")
        else: 
            st.subheader("Stream Feed")
            if "SELECTED_ROWS" in st.session_state:
                ru = st.session_state.SELECTED_ROWS
            else: 
                ru = []
            tweets_df = st.session_state.stream.get_feed(
                init_twarc_client(),
                recommended_users = ru #st.session_state.selected_recommended_users
            )

            tweets_df["created_at"] = pd.to_datetime(tweets_df["created_at"], utc=True)
            tweets_df.sort_values(["created_at"], ascending=False, inplace=True) 
                
            def filter_by_quantile(group, metric, quantile):
                thresh = group[f"public_metrics.{metric}"].quantile(quantile)
                return group[group[f"public_metrics.{metric}"] > thresh]
            
            # tweets = df_feed.groupby(["author.username"]).apply(lambda x: filter_by_quantile(x, "like_count", 0.9)).drop("author.username", axis=1).reset_index()
            tweets_df["created_at"] = [i.isoformat() for i in tweets_df["created_at"].tolist()]
            tweets_df = tweets_df[tweets_df["tweet_type"].isin(selected_tweet_types)]

            # st.write(tweets["author.username"].value_counts())
            # DEBUG
            # st.dataframe(tweets_df["author.username"].value_counts())
            tweets_df = tweets_df[
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
            num_clicks = streamlit_twitter_feed("World", tweets_df, key="unique")

    st.markdown("""<hr style="height:10px;border:none;color:#333;background-color:#333;" /> """, unsafe_allow_html=True)        
else: 
    st.write("load a previous stream, or login with twitter and seed users to start a new one!")    
