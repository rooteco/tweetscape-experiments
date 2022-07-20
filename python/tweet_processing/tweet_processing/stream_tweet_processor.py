import os
import concurrent.futures
from tqdm import tqdm
import pandas as pd
from tweet_processing import pull_tweets, get_user_following


class StreamTweetProcessor:
    def __init__(self, twarc_client, data_dir=None):
        self.twarc_client = twarc_client
        if data_dir:
            if not os.path.isdir(data_dir):
                raise Exception(f"directory '{data_dir}' does not exist... please supply existing directory")
            else:
                self.data_dir = data_dir
        else: 
            self.data_dir = "data" #assuming data in local directory

    def save_stream_seed_data(self, group_name, usernames): 
        df_tweets = None 
        df_ref_tweets = None
        df_following = None
        df_following = None
        for username in usernames: 
            i_df_following = get_user_following(self.twarc_client, username)
            if df_following is None:
                df_following = i_df_following
            else: 
                df_following = pd.concat([df_following, i_df_following])
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Start the load operations and mark each future with its URL
            futures = {executor.submit(pull_tweets, self.twarc_client, username): username for username in usernames}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(usernames)):
                # _ = future_to_url[future]
                i_username, i_df_tweets, i_df_ref_tweets = future.result()
                if isinstance(i_df_tweets, pd.DataFrame):
                    if df_tweets is None:
                        df_tweets = i_df_tweets
                    else: 
                        df_tweets = pd.concat([df_tweets, i_df_tweets])
                if isinstance(i_df_ref_tweets, pd.DataFrame):
                    if df_ref_tweets is None:
                        df_ref_tweets = i_df_ref_tweets
                    else: 
                        df_ref_tweets = pd.concat([df_ref_tweets, i_df_ref_tweets])
        os.makedirs(f"{self.data_dir}/{group_name}", exist_ok=True) 

        for type_, df_ in [("tweets",df_tweets), ("ref_tweets", df_ref_tweets), ("following",df_following)]:
            df_.to_csv(f"{self.data_dir}/{group_name}/{type_}.csv")
        return df_following, df_tweets, df_ref_tweets
    
    def load_stream_seed_data(self, group_name):
        dir_ = f"{self.data_dir}/{group_name}"
        df_following = pd.read_csv(f"{dir_}/following.csv")
        df_tweets = pd.read_csv(f"{dir_}/tweets.csv")
        df_ref_tweets = pd.read_csv(f"{dir_}/ref_tweets.csv")

        return df_following, df_tweets, df_ref_tweets