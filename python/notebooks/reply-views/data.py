import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import pandas as pd
import concurrent.futures

from sqlalchemy import create_engine #importing sqlalchemy engine to create engine for the database
import click
from tqdm import tqdm
from twarc import Twarc2
from twarc_csv import DataFrameConverter
import twarc
from sqlalchemy.types import BigInteger, Integer, Text, String, DateTime, JSON

load_dotenv()

ECHO = False

def fetch_data_db(pull_data_id, engine):
    query_template = "select * from {} where pull_data_id='{}'"
    print(f"pulling data for {pull_data_id} from db")
    df_following = pd.read_sql(query_template.format("following", pull_data_id), engine)
    df_f_tweets = pd.read_sql(query_template.format("tweets", pull_data_id), engine)
    df_f_ref_tweets = pd.read_sql(query_template.format("ref_tweets", pull_data_id), engine)
    return df_following, df_f_tweets, df_f_ref_tweets

def save_follows_and_tweets(engine_url, df_following, df_f_tweets, df_f_ref_tweets):
    def save_df(table, df, pull_data_id):
        engine = create_engine(engine_url, echo=ECHO)
        print(f"saving data for  table {table}")
        try: 
            df.to_sql(
                table, 
                engine,
                if_exists="append",
                dtype={
                    'id': BigInteger,
                    'created_at': DateTime, 
                    'author.username': String(15), 
                    'author.id': BigInteger, 
                    'referenced_tweets.replied_to.id': BigInteger, 
                    'referenced_tweets.retweeted.id': BigInteger,
                    'referenced_tweets.quoted.id': BigInteger, 
                    'in_reply_to_user_id': BigInteger,
                    "entities.mentions": JSON,
                    "public_metrics.reply_count": BigInteger, 
                    "author.public_metrics.followers_count": BigInteger, 
                    "attachments.poll.end_datetime": DateTime,
                    "entities.description.cashtags": Text
                }
            )
        except Exception as err: 
            fpath = f"error_data/{table}-{pull_data_id}.csv"
            print(f"error saving data in table {table} for id {pull_data_id}. saving data to '{fpath}' printing exception below")
            print(err)
            df.to_csv(fpath)

    pull_data_id = df_following["pull_data_id"].unique()[0]
    if df_following["pull_data_id"].unique()[0] != df_f_tweets["pull_data_id"].unique()[0] or df_f_tweets["pull_data_id"].unique()[0] != df_f_ref_tweets["pull_data_id"].unique()[0]:
        raise Exception("Dataframes do not have matching pull_data_ids. Will not save")
    
    save_df("following", df_following, pull_data_id)
    save_df("tweets", df_f_tweets, pull_data_id)
    save_df("ref_tweets", df_f_ref_tweets, pull_data_id)

def get_follows_and_tweets(engine_url, pull_data_id=None, client=None, username=None, start_time=None, end_time=None):
    def prepare_df(df_):
        if "" in df_.columns:
            df_.drop(columns=[""], inplace=True)
        df_["pull_data_id"] = pull_data_id
        return df_
    engine = create_engine(engine_url, echo=ECHO)
    if pull_data_id is None:
        if client is None or username is None or start_time is None or end_time is None: 
            raise Exception("If pull_data_id not provided, you must pass client, engine, username, start_time, and end_time vars")

        pull_data_id = f"{username}----{start_time}----{end_time}"
        df_following = get_user_following(client, username)
        df_following = prepare_df(df_following)

        df_f_tweets, df_f_ref_tweets = get_user_following_tweets(client, df_following.id.tolist(), start_time, end_time)
        df_f_tweets = prepare_df(df_f_tweets)
        df_f_ref_tweets = prepare_df(df_f_ref_tweets)

    else: 
        df_following, df_f_tweets, df_f_ref_tweets = fetch_data_db(pull_data_id, engine)
    return df_following, df_f_tweets, df_f_ref_tweets

def get_time_interval(hours=24):
    """
    ## Get dates for a 24 hour window to pass to twarc2 timeline command

    Return EndTime, StartTime, from current time
    """
    now = datetime.now(timezone.utc)
    (now - timedelta(hours=24)).isoformat("T")[:-3] + "Z"
    return now.isoformat("T")[:-13]+"Z",  (now - timedelta(hours=24)).isoformat("T")[:-13] + "Z"


def get_user_following(client, username):
    """
    
    """
    print(f"fetching accounts followed by {username}")
    dfs = []
    for res in client.following(username):
        dfs.append(DataFrameConverter("users").process(res["data"]))
    df_following = pd.concat(dfs)
    return df_following

def get_user_following_tweets(client: twarc.client2.Twarc2, following_ids: list, start_time: str, end_time: str):
    """
    client: twarc clieint for grabbing tweets
    following_ids (list): list of ids to pull tweets for 
    start_time (string, datetime formatted): 
    end_time

    returns:
        df_tweets (pandas DF) all tweets from start_time to end_time of all accounts in follwing_ids
        df_ref_tweets (pandas DF): all tweets referenced by the tweets in df_ref_tweets 
    """
    def pull_tweets(id_):
        df_tweets = None
        df_ref_tweets = None
        timeline_gen = client.timeline(id_, start_time=start_time, end_time=end_time, max_results=100)
        try: 
            for res in timeline_gen:
                df_tweets_next = converter.process([res])
                
                if df_tweets is None:
                    df_tweets = df_tweets_next
                else: 
                    df_tweets = pd.concat([df_tweets, df_tweets_next])
                    
                if "tweets" in res["includes"]:
                    df_ref_tweets_next = converter.process(res["includes"]["tweets"])
                    if df_ref_tweets is None:
                        df_ref_tweets = df_ref_tweets_next
                    else: 
                        df_ref_tweets = pd.concat([df_ref_tweets, df_ref_tweets_next])
        except HTTPError as err: 
            print(f"400 client error for id {id_}... skipping")
            return None, None
        return df_tweets, df_ref_tweets     
    
    print("fetching tweets")
    converter = DataFrameConverter("tweets", allow_duplicates=True) # allow duplicates because I'm process data and includes separate, so it wasn't allowing all tweets when going through the includes
    
    df_tweets_list = []
    df_ref_tweets_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(pull_tweets, id_): id_ for id_ in following_ids}
        for future in tqdm(concurrent.futures.as_completed(future_to_url), total=len(following_ids)):
            url = future_to_url[future]
            i_df_tweets, i_df_ref_tweets = future.result()
            if isinstance(i_df_tweets, pd.DataFrame):
                df_tweets_list.append(i_df_tweets)
            if isinstance(i_df_ref_tweets, pd.DataFrame):
                df_ref_tweets_list.append(i_df_ref_tweets)

    df_tweets = pd.concat(df_tweets_list)
    df_ref_tweets = pd.concat(df_ref_tweets_list)
    return df_tweets, df_ref_tweets

def get_user_following_mentions(client: twarc.client2.Twarc2, following_usernames: list, start_time: str, end_time: str):
    """
    Get all tweets that mention the accounts included in following_ids 
    
    This func is limited by the search api, which is only the past 7 days
    """
    print("getting mentions")
    converter = DataFrameConverter("tweets", inline_referenced_tweets=False) #includes "included" tweets, aka referenced tweets
    df = None
    for username in following_usernames:
        query = f"to:{username}"
        for i in client.search_recent(query, start_time=start_time, end_time=end_time):
            if df is None:
                df = converter.process([i])
            else: 
                df = pd.concat([df, converter.process([i])])
    return df


import json 

def extract_usernames(mention_list: str):
    if not isinstance(mention_list, str): # this means it is nan
        return mention_list
    # When someone replies, but then also includes a mention, it results in a double mention. Removing those by creating a set first
    return ", ".join(list(set([i["username"] for i in json.loads(mention_list)]))) 

def extract_double_mention(mention_list: str):
    if not isinstance(mention_list, str): # this means it is nan
        return mention_list
    mention_list = json.loads(mention_list) # transform string to python obj
    mention_list = [i["username"] for i in mention_list]
    mention_set = set(mention_list)
    if len(mention_list) != len(mention_set):
        return True
    else:
        return False

def extract_num_mentions(mention_list: str):
    if not isinstance(mention_list, str): # this means it is nan
        return mention_list
    mention_list = json.loads(mention_list) # transform string to python obj
    return len(mention_list)

def extract_tweet_type(row):
    """
    Current Categories are 
    reply - reply that doesn't include a quoted tweet (I could expand to include mentions, but I don't feel like it right now)                 
    rt                     
    qt,reply - reply tweet that includes a quoted tweet
    standalone - classic tweet, just text          
    self-reply - reply to yourself          
    qt                     
    standalone,mention - classic tweet, but you also mention another user  
    qt,self-reply - quote tweet in reply to your own account      
    qt,mention - quote tweet where you mention another account, not a reply 
    """
    standalone = "standalone,"
    reply = "reply,"
    rt = "rt,"
    qt = "qt,"
    mention = "mention,"
    
    type_str = ""
    
    ## Standalone means that there is no in_reply_to_user_id or a referenced_tweet
    if (
        pd.isna(row["in_reply_to_user_id"]) and 
        pd.isna(row['referenced_tweets.replied_to.id']) and 
        pd.isna(row['referenced_tweets.retweeted.id']) and 
        pd.isna(row['referenced_tweets.quoted.id'])
    ):
        type_str += standalone
        
        if not pd.isna(row["entities.mentions"]):
            type_str += mention
    
    ## I think this is a special case where user starts there own standlone tweet with a mention, so twitter reads it weird
    # Here is an example: https://twitter.com/deepfates/status/1536434435075280898, it starts with a mention, with twitter reads into the in_reply_to_user_id field
    elif pd.isna(row['referenced_tweets.replied_to.id']) and not pd.isna(row["in_reply_to_user_id"]):
        type_str += standalone
        type_str += mention 
    
    ## Retweet
    elif not pd.isna(row['referenced_tweets.retweeted.id']):
        type_str += rt 
    
    ## Quote Tweet 
    elif not pd.isna(row['referenced_tweets.quoted.id']):
        type_str += qt 
        
        ## Quote Tweet that is a reply 
        if not pd.isna(row['referenced_tweets.replied_to.id']):
            if pd.isna(row["entities.mentions"]):
                type_str += "self-reply,"
            else:
                type_str += reply
        elif not pd.isna(row["entities.mentions"]): ## This logic is shaky
            type_str += mention
    
    ## Replies
    elif not pd.isna(row['referenced_tweets.replied_to.id']):
        if pd.isna(row["entities.mentions"]):
            type_str += "self-reply,"
        else:
            type_str += reply
        
    return type_str[:-1]

@click.command()
@click.option('--usernames', '-u', help='username of twitter user to pull the follows of', multiple=True)
def fetch_data(usernames):
    host=os.environ["Hostname"]
    database=os.environ["Hostname"]
    user=os.environ["Username"]
    password=os.environ["Password"]
    port=os.environ["Proxy_Port"] # in integer
    # engine_url = f'postgresql://postgres:{password}@localhost:15432' #need a fly proxy running on this port
    engine_url = f'postgresql://{user}:{password}@{host}:{port}'
    engine = create_engine(engine_url, echo=ECHO)

    client = Twarc2(
        consumer_key=os.environ["consumer_key"], 
        consumer_secret=os.environ["consumer_secret"],
        access_token=os.environ["access_token"], 
        access_token_secret=os.environ["access_token_secret"]
    )

    end_time, start_time = get_time_interval()
    for username in usernames:
        df_following, df_f_tweets, df_f_ref_tweets = get_follows_and_tweets(engine_url, client=client, username=username, start_time=start_time, end_time=end_time)
        save_follows_and_tweets(engine_url, df_following, df_f_tweets, df_f_ref_tweets)

if __name__ == "__main__":
    fetch_data()
    