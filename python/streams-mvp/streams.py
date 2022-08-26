

import os
import json
from io import BytesIO
from random import seed
import pandas as pd
from minio import Minio, error
from twarc import Twarc2
from tweet_processing import get_user_following, pull_tweets

# Stream().add_selected_users()
# Stream().update_selected_users()
# recommended_users = Stream().get_recommended_users(
#             rec_method="following", 
#             num_seed_accounts_following=2
#         )

# Stream().save()
# Stream().load() 

# tweets = Stream().get_feed()

# host = "localhost:9000" if not _RELEASE else "experiment-data-minio.internal:9000"
host = "localhost:9000"
MINIO_CLIENT = Minio(
    host, 
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False
)

BUCKET = "streams-mvp"

def minio_write_json(obj, path):
    import json
    obj_s = json.dumps(obj, indent=4)
    write_result = MINIO_CLIENT.put_object(
        BUCKET, #bucket-name,
        path,
        data=BytesIO(obj_s.encode("utf-8")),
        length=len(obj_s),
        content_type='application/json'
    )
    return write_result

def minio_read_json(path):
    read_res = MINIO_CLIENT.get_object(BUCKET, path)
    return json.loads(read_res.data)

def minio_to_csv(df, path):
    # def remote_write_seed_df(self, object_fpath, df):
    __docstring = """
    bucket: minio bucket to write to
    object_fpath: fpath of object to write to
    df: the dataframe to save
    """

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)
    write_result = MINIO_CLIENT.put_object(
        BUCKET, #bucket-name,
        path,
        data=csv_buffer,
        length=len(csv_bytes),
        content_type='application/csv'
    )
    return write_result

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

class Stream:
    def __init__(
        self, 
        end_time=None, 
        start_time=None,
        # twarc_client=None,
        seed_accounts = {},
        recommended_users = [], 
        selected_recommended_users = [],
    ):
        """
        Args:
            end_time (str): datetime string that defines the end time of tweets pulled for all users
            start_time (str): datetime string that defines the start time of tweets pulled for all users
            twarc_client (str): 
        """
        #1 check for existance of seed accounts.. 
        #2 save the account info for the seed accounts
        self.end_time = end_time  # TODO: add check for formatting of string
        self.start_time = start_time 

        # if twarc_client is None: 
        #     print("twarc_client is None, so many methods will not yet be available!")
        #     self.twarc_client = None
        # elif isinstance(twarc_client, Twarc2): 
        #     self.twarc_client = twarc_client
        # else: 
        #     raise Exception(f"provided twarc_client {twarc_client} is not of required type {Twarc2}")
        self.last_failed_lookup = []
        if isinstance(seed_accounts, dict):
            self.seed_accounts = seed_accounts
        else:
            # self.seed_accounts, _ = self.add_seed_users(seed_accounts) if len(seed_accounts) > 0 else {}, None
            raise Exception("lookup seed users by twitter with `add_seed_users` func")
        self.selected_recommended_users = selected_recommended_users
        self.recommended_users = recommended_users
        self.tweets = {}

    def add_twarc_client(self, twarc_client):
        """
        """
        if isinstance(twarc_client, Twarc2):
            self.twarc_client = twarc_client 
        else:
            raise Exception(f"provided twarc_client {twarc_client} is not of required type {Twarc2}")

    def add_seed_users(self, usernames, twarc_client):
        """
        Args:
            usernames (list[str]): list of usernames to add seed users

        Returns:
            successful_lookups (dict): dictionary, keyed by username, of user data for successful lookups
            # failed_lookups (list): list of usernames that did not return data for the user
        """
        for i in usernames:
            if len(i) > 15: #TODO: handle this better
                raise Exception(f"username {i} is greater than the 15 character limit... please check this and try again")

        
        successful_lookups, self.last_failed_lookup = self.lookup_users(usernames, twarc_client)
        for username, user_data in successful_lookups.items():
            if username not in self.seed_accounts:
                self.seed_accounts[username] = {}
                self.seed_accounts[username]["user_data"] = user_data
                self.seed_accounts[username]["following"] = get_user_following(twarc_client, username)
        return successful_lookups

    def get_feed(self, twarc_client, recommended_users):
        """
        Args: 
            twarc_client (Twarc2): 
            recommended_users (list[str]): list of usernames 
        Returns: 
            df (pd.DataFrame): df of tweets from seed users and recommended users 
        """
        if not len(self.seed_accounts):
            raise Exception("Must add seed accounts before fetching feed")
        for username in self.seed_accounts: 
            if username not in self.tweets: 
                i_username, i_df_tweets, i_df_ref_tweets = pull_tweets(
                    twarc_client, 
                    username, 
                    start_time=self.start_time, 
                    end_time=self.end_time
                )
                self.tweets[username] = {}
                if i_df_tweets is None: 
                    i_df_tweets = []
                else:
                    self.tweets[username]["tweets"] = i_df_tweets 
                if i_df_ref_tweets is None: 
                    self.tweets[username]["ref_tweets"] = []
                else:    
                    self.tweets[username]["ref_tweets"] = i_df_ref_tweets

        for username in recommended_users:
            if username not in self.tweets: 
                i_username, i_df_tweets, i_df_ref_tweets = pull_tweets(
                    twarc_client, 
                    username, 
                    start_time=self.start_time, 
                    end_time=self.end_time
                )
                self.tweets[username] = {}
                if i_df_tweets is None: 
                    i_df_tweets = []
                else:
                    self.tweets[username]["tweets"] = i_df_tweets 
                if i_df_ref_tweets is None: 
                    self.tweets[username]["ref_tweets"] = []
                else:    
                    self.tweets[username]["ref_tweets"] = i_df_ref_tweets
        feed_list = []
        for username, tweet_dict in self.tweets.items():
            if username in self.seed_accounts or username in recommended_users:
                feed_list.append(tweet_dict["tweets"])
        return pd.concat(feed_list)

    def get_name(self):
        return ",".join(self.seed_accounts.keys()) + "---" + self.end_time

    def set_recommended_users(self, recommended_users):
        self.recommended_users = recommended_users
    
    def set_selected_recommended_users(self, selected_recommended_users):
        self.selected_recommended_users = selected_recommended_users

    @classmethod
    def load_cls(cls, stream_name, twarc_client=None):
        stream_config = minio_read_json(os.path.join(stream_name, "stream_config.json"))
        for username in stream_config["seed_accounts"].keys():
            following_fpath = os.path.join(stream_name, "seed_accounts_following", f"{username}_following.csv")
            df_following = minio_read_csv(following_fpath)
            stream_config["seed_accounts"][username]["following"] = df_following
        return cls(
            stream_config["end_time"], 
            stream_config["start_time"], 
            twarc_client=twarc_client, 
            seed_accounts = stream_config["seed_accounts"], 
            recommended_users = stream_config["recommended_users"], 
            selected_recommended_users = stream_config["selected_recommended_users"]
        )
    
    def save(self, stream_name=None, all_recommended_users=[], selected_recommended_users=[]):
        """
        Need figure out structure

        stream-name-directory
            stream_config.json
                name
                end_time
                start_time
            seed_accounts_following
                username1_following.csv
                username2_follwing.csv
            tweets
                username1_tweets.csv
                username1_ref_tweets.csv
                username2_tweets.csv
                username2_ref_tweets.csv

        """
        BUCKET = "streams-mvp"
        stream_name = stream_name if stream_name else self.get_name()
        
        ### Save df_following for seed accounts
        # Doing this first to build seed_accounts_userdata for saving the config
        seed_accounts_following_dir = os.path.join(stream_name, "seed_accounts_following")
        seed_accounts_userdata = {}
        for username, data in self.seed_accounts.items():
            seed_accounts_userdata[username] = {}
            seed_accounts_userdata[username]["user_data"] = data["user_data"]
            following_fpath = os.path.join(seed_accounts_following_dir, f"{username}_following.csv")
            minio_to_csv(data["following"],following_fpath)

        ### Save json Config
        config_fpath = os.path.join(stream_name, "stream_config.json")
        config = {
            "name": stream_name, 
            "end_time": self.end_time, 
            "start_time": self.start_time, 
            "seed_accounts": seed_accounts_userdata, 
            "recommended_users": all_recommended_users, 
            "selected_recommended_users": selected_recommended_users,
        }

        write_result = minio_write_json(
            config, 
            config_fpath
        )
        
        ### Save tweets for all users
        tweets_json_fpath = os.path.join(stream_name, "tweets.json")
        tweets_json =  {username: {} for username in self.tweets}
        for username in self.tweets:
            print(f"saving tweets for {username}")
            tweets_json[username]["tweets"] = self.tweets[username]["tweets"].to_json(orient="records") if len(self.tweets[username]["tweets"])>0 else []
            tweets_json[username]["ref_tweets"] = self.tweets[username]["ref_tweets"].to_json(orient="records") if len(self.tweets[username]["ref_tweets"]) > 0 else []
            
        write_result = minio_write_json(
            tweets_json, 
            tweets_json_fpath
        )
        return write_result

    def load(self, stream_name):
        stream_config = minio_read_json(os.path.join(stream_name, "stream_config.json"))
        for username in stream_config["seed_accounts"].keys():
            following_fpath = os.path.join(stream_name, "seed_accounts_following", f"{username}_following.csv")
            df_following = minio_read_csv(following_fpath)
            stream_config["seed_accounts"][username]["following"] = df_following
        
        tweets_json = minio_read_json(os.path.join(stream_name, "tweets.json"))
        self.tweets =  {username: {} for username in tweets_json}
        for username in self.tweets:
            self.tweets[username]["tweets"] = pd.read_json(tweets_json[username]["tweets"]) if isinstance(tweets_json[username]["tweets"], str) else []
            self.tweets[username]["ref_tweets"] = pd.read_json(tweets_json[username]["ref_tweets"]) if isinstance(tweets_json[username]["ref_tweets"], str) else []
        self.end_time = stream_config["end_time"]
        self.start_time = stream_config["start_time"]
        self.seed_accounts = stream_config["seed_accounts"]
        self.all_recommended_users = stream_config["recommended_users"]
        self.selected_recommended_users = stream_config["selected_recommended_users"]

    def delete(self):
        for i in MINIO_CLIENT.list_objects(BUCKET, self.get_name()):
            MINIO_CLIENT.remove_object(BUCKET, i.object_name)

    def lookup_users(self, usernames, twarc_client):
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

    def update_seed_account_info(self):
        for username, info in self.seed_accounts.items():
            df_following = "df of following"
            self.seed_accounts[username]["following"] = df_following 
    
    def update_stream_tweets(self):
        stream_users = "the selected accounts..."
