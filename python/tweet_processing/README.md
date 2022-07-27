## Tweet Processing

This is the start of a repo with common tweet processing utilities we can use across experiments. 

## Install
`pip install .`

if you are making edits to this library as well, which will likely be the case, use

`pip install -e .`

### StreamTweetProcessor
This object can be used to pull the initial data for a stream. 

```python
tp = StreamTweetProcessor(
    twarc_client=twarc_client, 
    minio_client=minio_client, 
    bucket="stream-seeding"
)
group_name = "longevity" 
group = ["ArtirKel", "celinehalioua", "LauraDeming"] #list of twiter usernames
df_following, df_tweets, df_ref_tweets = tp.save_stream_seed_data(group_name, group)
```

The above code stores data for each of these users in the following files, in the minio bucket passed to the twarc client initialization: 
* `data/group_name/following.csv`: df of accounts followed by user. Grouped by column `referencer.username`
* `data/group_name/tweets.csv`: df of tweets from these users in group. Group by `author.id` or `author.username`
* `data/group_name/ref_tweets.csv`: df of tweets referenced in df_tweets. Group by column `referencer.username` 

### StreamTweetProcessor Examples
* notebooks/network-topology/streamlit_app.py
* notebooks/network-topology/seed_users_following_overlap.ipynb
* notebooks/network-topology/seed_users_ref_tweet_overlap.ipynb



