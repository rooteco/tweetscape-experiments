import os
import concurrent.futures
from io import BytesIO
from tqdm import tqdm
from stqdm import stqdm
import pandas as pd
from tweet_processing import pull_tweets, get_user_following

class StreamTweetProcessor:
    def __init__(self, twarc_client, minio_client, bucket):
        self.twarc_client = twarc_client
        self.minio_client = minio_client
        self.bucket = bucket

    def save_stream_seed_data(self, group_name, usernames, streamlit_progress_bar=False): 
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
            progress_bar = stqdm if streamlit_progress_bar else tqdm
            for future in progress_bar(concurrent.futures.as_completed(futures), total=len(usernames)):
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

        for type_, df_ in [("tweets",df_tweets), ("ref_tweets", df_ref_tweets), ("following",df_following)]:
            self.remote_write_seed_df(f"{group_name}/{type_}.csv", df_)
        return df_following, df_tweets, df_ref_tweets

class RemoteStreamTweetProcessor(StreamTweetProcessor):
    def remote_write_seed_df(self, object_fpath, df):
        """
        bucket: minio bucket to write to
        object_fpath: fpath of object to write to
        df: the dataframe to save
        """
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        csv_buffer = BytesIO(csv_bytes)
        write_result = self.minio_client.put_object(
            self.bucket, #bucket-name,
            object_fpath,
            # f'{group_name}/following.csv',#bucket-path
            data=csv_buffer,
            length=len(csv_bytes),
            content_type='application/csv'
        )
        return write_result

    def remote_read_seed_data(self, group_name):
        dfs = []
        for type_ in ["following.csv", "tweets.csv", "ref_tweets.csv"]:
            read_res = self.minio_client.get_object(
                self.bucket, 
                f"{group_name}/{type_}"
            )
            df = pd.read_csv(BytesIO(read_res.data))
            dfs.append(df)
        df_following, df_tweets, df_ref_tweets = dfs
        return df_following, df_tweets, df_ref_tweets


    