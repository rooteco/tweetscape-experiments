import os
import pandas as pd
import json
import concurrent.futures
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
from requests.exceptions import HTTPError
import click
from twarc import Twarc2
from twarc_csv import DataFrameConverter

from dotenv import load_dotenv

load_dotenv()

converter = DataFrameConverter("users", allow_duplicates=True)


def lookup_users_by_username(client, usernames): 
    user_gen = client.user_lookup(users=usernames, usernames=True)
    df_users = None
    for res in user_gen:
        df_next = converter.process(res["data"])
        if df_users is None:
            df_users = df_next
        else: 
            df_tweets = pd.concat([df_tweets, df_next])
    return df_users
                

