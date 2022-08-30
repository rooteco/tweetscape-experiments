from copy import deepcopy
import os
import json
import streamlit as st
import tweepy
import redis
import pandas as pd 
from twarc import Twarc2
from dotenv import load_dotenv
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

from tweet_processing import get_user_following, pull_tweets


load_dotenv()

SKIP_PIN_AUTH = True 
REDIS_CLIENT = redis.Redis(port=6370, password=os.environ["REDIS_PASSWORD_WTF"])

CONSUMER_KEY = os.environ["consumer_key"]
CONSUMER_SECRET = os.environ["consumer_secret"]
AUTH = tweepy.OAuth1UserHandler(CONSUMER_KEY, CONSUMER_SECRET,callback="oob")

# REDIS_CLIENT = redis.Redis(host= "streams-mvp-redis.internal", port=6379, password=os.environ["REDIS_PASSWORD"])

def set_oauth_verifier():
    ACCESS_TOKEN, ACCESS_TOKEN_SECRET = AUTH.get_access_token(st.session_state.oauth_verifier_verifier_input)
    AUTH.set_access_token(ACCESS_TOKEN,ACCESS_TOKEN_SECRET)
    st.session_state.oauth_objects["access_token"] = ACCESS_TOKEN
    st.session_state.oauth_objects["access_token_secret"] = ACCESS_TOKEN_SECRET

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

def lookup_users(usernames, twarc_client):
        """
        usernames (list): list of usernames to lookup

        Returns:
            successful_users (dict): dict of metadata for the user as retreived from twitter
            error_usernames (list): list of usernames that were not successfully found
        """
        user_gen = twarc_client.user_lookup(users=usernames, usernames=True)
        successful_users = {}
        error_usernames = []
        for res in user_gen:
            if "data" in res:
                for user_data in res["data"]:
                    # successful_usernames.append(user_data["username"])
                    successful_users[user_data["username"]] = user_data
            if "errors" in res:
                for error in res["errors"]:
                    error_usernames.append(error["value"])
        return successful_users, error_usernames

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

if "seed_users" not in st.session_state:
    st.session_state.seed_users = {}
if "oauth_objects" not in st.session_state:
    if SKIP_PIN_AUTH:
        st.session_state.oauth_objects = {"a": "yo"}
    else: 
        st.session_state.oauth_objects = {}

INITIAL_SELECTED_USERS = None
INITIAL_NUM_STREAM_USERS = None

if not len(st.session_state.oauth_objects):
    st.write("Login with twitter to create new streams!")
    if st.button("Sign In With Twitter"):
        st.text("Go to this link in another tab and grab the pin: ")
        st.write(AUTH.get_authorization_url())
        verifier = st.text_input("Enter PIN: ", False, type="password", on_change=set_oauth_verifier, key="oauth_verifier_verifier_input")

available_streams = [i.decode("utf-8") for i in REDIS_CLIENT.scan_iter()]
st.write(available_streams)

stream_name = st.selectbox(
    "load stream", 
    ["start new"] + [i.decode("utf-8") for i in REDIS_CLIENT.scan_iter()],    
)

if stream_name != "start new":
    stream_obj = REDIS_CLIENT.hgetall(stream_name)
    st.session_state.seed_users = json.loads(stream_obj[b'seed_users'])
    for username, data in st.session_state.seed_users.items():
        data["following"] = pd.DataFrame(json.loads(data["following"]))
    INITIAL_SELECTED_USERS = json.loads(stream_obj[b'selected_recommended_users'])
    INITIAL_NUM_STREAM_USERS = stream_obj[b'num_stream_users']
    
selected = st.text_input("search for users", value="")#, on_change=add_seed_users, key="user_text_key")
usernames = [i.lower().strip() for i in selected.split(",")]
usernames = [i for i in usernames if i not in st.session_state.seed_users and len(i) > 0]
if len(usernames):
    for i_username in usernames:
        if len(i_username) > 15: #TODO: handle this better
            raise Exception(f"username '{i_username}' is greater than the 15 character limit... please check this and try again")
    successful_lookups, failed_lookups = lookup_users(usernames, init_twarc_client())
    for username, data in successful_lookups.items():
        print(username)
        username = username.lower()
        st.session_state.seed_users[username] = data
        st.session_state.seed_users[username]["following"] = get_user_following(init_twarc_client(), username)

st.write(st.session_state.seed_users.keys())


col1, col2 = st.columns(2)

with col1: 
    if len(st.session_state.seed_users) > 1:
        st.subheader("Seed Users")
        data = {"username": list(st.session_state.seed_users.keys())}
        df = pd.DataFrame(data)
        gd = GridOptionsBuilder.from_dataframe(df)
        gd.configure_selection(selection_mode='multiple', use_checkbox=True, pre_selected_rows=list(df.index))
        gd.configure_default_column(min_column_width=2)
        gridoptions = gd.build()
        seed_grid_table = AgGrid(
            df, 
            height=115, 
            fit_columns_on_grid_load=True,
            gridOptions=gridoptions,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
        )
        selected_seed_rows = seed_grid_table["selected_rows"]
    
    if len(st.session_state.seed_users) < 3:
        st.write("add at least 3 seed users for recommendations")
    else: 
        df_following = pd.concat([v["following"] for k, v in st.session_state.seed_users.items()])
        overlap_df = recommend_by_following(df_following)
        num_stream_users = st.slider(
            "number of stream users", 
            min_value=1, 
            max_value=df_following["referencer.username"].nunique(), 
            value=df_following["referencer.username"].nunique() if INITIAL_NUM_STREAM_USERS is None else INITIAL_NUM_STREAM_USERS
        )
        present_df = overlap_df[overlap_df["num_stream_users"]>=num_stream_users].sort_values(["num_stream_users","num_followers_of_followed"])
        
        st.write(f"{present_df.shape[0]} accounts recommended")

        data = {
            "username": [],
            "num_followers": [],
            "num_seed_users_followed_by": [], 
        }

        for _, row in present_df.iterrows():
            if row["followed.username"] not in st.session_state.seed_users:
                data["username"].append(row['followed.username'])
                data["num_seed_users_followed_by"].append(row["num_stream_users"])
                data["num_followers"].append(row["num_followers_of_followed"])

        df = pd.DataFrame(data)
        df = df[["username", "num_followers", "num_seed_users_followed_by"]]

        gd = GridOptionsBuilder.from_dataframe(df)
        df["username"] = [i.lower() for i in df["username"].to_list()]

        gd.configure_selection(
            selection_mode='multiple', 
            use_checkbox=True, 
            # pre_selected_rows=list(df[df["username"].isin(INITIAL_SELECTED_USERS)].index) if INITIAL_SELECTED_USERS is not None else []
        )
        gridoptions = gd.build()
        grid_table = AgGrid(
            df, 
            height=250, 
            gridOptions=gridoptions,
            update_mode=GridUpdateMode.SELECTION_CHANGED
        )
        selected_recommended_rows = grid_table["selected_rows"]
        st.write(selected_recommended_rows)

if st.button("Save Current Stream"): 
    name = "--".join(list(st.session_state.seed_users.keys()))
    stream_object = {
        "seed_users": {},
        "selected_recommended_users": [i["username"].lower() for i in selected_recommended_rows], 
        "num_stream_users": num_stream_users
    }
    su_json = deepcopy(st.session_state.seed_users)
    for username, data in su_json.items():
        data["following"] = data["following"].to_json(orient="records")
        for k, obj in data.items():
            if isinstance(obj, dict):
                obj = json.dumps(obj)
    
    stream_object["seed_users"] = su_json
    for key, value in stream_object.items():
        REDIS_CLIENT.hset(name, key, json.dumps(value))
    available_streams.append(name)
    st.write(available_streams)
    # res = REDIS_CLIENT.hset(name, stream_object)
    # if res: 
    #     st.write(f"Saved stream {name}!!!")
        
    # else: 
    #     raise Exception(f"Failed Saving stream {name}")