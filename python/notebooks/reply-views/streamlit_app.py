import os
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from twarc import Twarc2
from sqlalchemy import create_engine #importing sqlalchemy engine to create engine for the database
from dotenv import load_dotenv

load_dotenv()

from data import get_follows_and_tweets, get_time_interval, extract_double_mention, extract_num_mentions, extract_tweet_type, extract_usernames

def get_previous_ids(engine):
    query = "select distinct pull_data_id from tweets;"
    ids = pd.read_sql(query, engine)
    return ids["pull_data_id"].tolist()

USER = "nicktorba" 
HOURS = 24


host=os.environ["Hostname"]
database=os.environ["Hostname"]
user=os.environ["Username"]
password=os.environ["Password"]
port=os.environ["Proxy_Port"] # in integer
# engine_url = f'postgresql://postgres:{password}@localhost:15432' #need a fly proxy running on this port
engine_url = f'postgresql://{user}:{password}@{host}:{port}'
engine = create_engine(engine_url)

data_pull_ids = get_previous_ids(engine)

cont = True
pull_data_id = st.selectbox("Select User and Date Range to Display from Options Below", data_pull_ids)

def main():
    USER = pull_data_id.split("----")[0]
    start_time = pull_data_id.split("----")[1]
    end_time = pull_data_id.split("----")[2]

    st.header(f"Landscape Tweet View for {USER}")
    st.text(f"All data is from `{start_time}` to `{end_time}`")

    df_following, df_f_tweets, df_f_ref_tweets = get_follows_and_tweets(engine_url=engine_url, pull_data_id=pull_data_id)
    df_following = df_following.set_index("username")

    st.text(df_following.shape)

    for df_ in [df_f_tweets, df_f_ref_tweets]:
        df_["tweet_link"] = df_.apply(lambda row: f"https://twitter.com/{row['author.username']}/status/{row.id}", axis=1)
        df_.loc[:, "created_at"] = pd.to_datetime(df_.loc[:, "created_at"], utc=True)
        df_["created_at.hour"] = df_["created_at"].dt.floor('h')

    df_f_tweets["entities.mentions.usernames"] = df_f_tweets["entities.mentions"].apply(extract_usernames)
    df_f_tweets["entities.mentions.num_mentions"] = df_f_tweets["entities.mentions"].apply(extract_num_mentions)
    df_f_tweets["entities.mentions.double_mention"] = df_f_tweets["entities.mentions"].apply(extract_double_mention)
    df_f_tweets["tweet_type"] = df_f_tweets.apply(lambda x: extract_tweet_type(x), axis=1)


    st.subheader("Account Cloud, based on tweet activity")
    st.text("Pick which types of tweets to include below")
    tweet_types = list(df_f_tweets["tweet_type"].unique())
    options = st.multiselect(
        'You can select which types of tweets to include here',
        tweet_types,
        tweet_types
    )

    # Create and generate a word cloud image:
    words = " ".join(df_f_tweets[df_f_tweets["tweet_type"].isin(tweet_types)]["author.username"].tolist())
    wordcloud = WordCloud(collocations=False).generate(words)
    # Display the generated image:
    fig, ax = plt.subplots()
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    st.pyplot(fig)

    ######
    st.subheader("Tweet Type Distribution")
    st.text("Next, we look at the types of tweets being sent by these users. ")
    fig = px.bar(
        df_f_tweets["tweet_type"].value_counts().reset_index(), 
        x="index", 
        y="tweet_type", 
        labels={
            "tweet_type": "count of type",
            "index": "tweet type",
        },
        color="index")
    st.plotly_chart(fig)


    ###### 
    st.header("Top X Tweeter by Tweet Type")

    X = 25

    st.subheader("All Types")

    plot_df = df_f_tweets.groupby(["author.username"]).count()["id"].sort_values(ascending=False).reset_index().iloc[:X]
    fig = px.bar(plot_df, x="author.username", y="id", color="author.username", title="Top Tweeters - All Types")
    st.plotly_chart(fig)


    st.subheader("STandalone")

    plot_df = df_f_tweets[df_f_tweets["tweet_type"]=="standalone"].groupby(["author.username"]).count()["id"].sort_values(ascending=False).reset_index().iloc[:X]
    fig = px.bar(plot_df, x="author.username", y="id", color="author.username", title="Top Standalone Tweeters")
    st.plotly_chart(fig)

    st.subheader("Replies")

    plot_df = df_f_tweets[(df_f_tweets["tweet_type"]=="reply")].groupby(["author.username"]).count()["id"].sort_values(ascending=False).reset_index().iloc[:X]
    fig = px.bar(plot_df, x="author.username", y="id", color="author.username", title="Top Reply Tweeters")
    st.plotly_chart(fig)

    st.subheader("Retweets")
    plot_df = df_f_tweets[(df_f_tweets["tweet_type"]=="rt")].groupby(["author.username"]).count()["id"].sort_values(ascending=False).reset_index().iloc[:X]
    fig = px.bar(plot_df, x="author.username", y="id", color="author.username", title="Top Retweeters")
    st.plotly_chart(fig)


    #######
    st.header("Replies Received")
    X = 25
    plot_df = df_f_tweets[(df_f_tweets["tweet_type"] != "rt") & (df_f_tweets["public_metrics.reply_count"] > 0)]
    plot_df = plot_df.groupby(["author.username", "author.id"])["public_metrics.reply_count"].sum().reset_index().sort_values("public_metrics.reply_count", ascending=False).iloc[:X]
    fig = px.bar(plot_df, x="author.username", y="public_metrics.reply_count", color="author.username", title="Num Replies")
    st.plotly_chart(fig)

    st.subheader("Num Replies vs. num followers")

    MAX_FOLLOWERS = st.number_input(
        "max followers", 
        min_value=0, 
        max_value=1000000,
        step=50, 
        value=10000
    )

    MIN_REPLIES_RECEIVED = st.number_input(
        "minimum replies received", 
        min_value=0, 
        step=1, 
        value=5
    )

    plot_df = df_f_tweets[(df_f_tweets["tweet_type"] != "rt") & (df_f_tweets["public_metrics.reply_count"] > 0)]

    plot_df = plot_df.groupby(["author.username"])["public_metrics.reply_count"].sum().reset_index().sort_values("public_metrics.reply_count", ascending=False).iloc[:300]

    plot_df["num_followers"] = plot_df["author.username"].map(lambda x: df_following.loc[x]["public_metrics.followers_count"] if x in df_following.index else None)

    fig = px.scatter(
        plot_df[ 
            (plot_df["num_followers"] < MAX_FOLLOWERS) & 
            (plot_df["public_metrics.reply_count"] > MIN_REPLIES_RECEIVED)
        ], 
        x="num_followers", 
        y="public_metrics.reply_count", 
        color="author.username", 
        height=1000, 
        title=f"Top Lowbies, {start_time}, {end_time}"
    )#, log_x=True, log_y=True)

    for d in fig.data:
        url = df_following.loc[d.name]["profile_image_url"]
        if url: 
            fig.add_layout_image(
                    source=url,
                    xref="x",
                    yref="y",
                    x=d.x[0],
                    y=d.y[0],
                    xanchor="center",
                    yanchor="middle",
                    sizex=200,
                    sizey=200,
                    # sizex=0.05,
                    # sizey=0.05,
                )

    st.plotly_chart(fig)


    #####
    st.subheader("Num Tweets vs. Num Replies")
    st.text("Let's find out who is active but not getting as much action")

    MIN_TWEETS_SENT = st.number_input(
        "minimum tweets sent", 
        min_value=0, 
        step=1, 
        value=5
    )

    plot_df = df_f_tweets[(df_f_tweets["tweet_type"] != "rt") & (df_f_tweets["public_metrics.reply_count"] > 0)]
    if st.checkbox("Only Include Reply Tweets"):
        plot_df = df_f_tweets[df_f_tweets["tweet_type"] == "reply"]
    plot_df = plot_df.groupby(["author.username"])["public_metrics.reply_count"].agg(["sum", "count"]).reset_index()
    plot_df["num_followers"] = plot_df["author.username"].map(lambda x: df_following.loc[x]["public_metrics.followers_count"] if x in df_following.index else None)

    fig = px.scatter(
        plot_df[(plot_df["num_followers"] < MAX_FOLLOWERS) & (plot_df["count"] > MIN_TWEETS_SENT)], 
        x="sum", 
        y="count", 
        labels={
            "sum": "Num replies",
            "count": "Num Tweets"
        },
        color="author.username", 
        height=1000, 
        size="num_followers",
        title=f"Num Tweets vs. Num Replies, {start_time}, {end_time}"
    )

    st.plotly_chart(fig)


    st.subheader("Num Tweets vs. Num Replies 3D")

    fig = px.scatter_3d(
        plot_df[(plot_df["num_followers"] < MAX_FOLLOWERS) & (plot_df["count"] > MIN_TWEETS_SENT)], 
        x="sum", 
        y="count", 
        labels={
            "sum": "Num replies",
            "count": "Num Tweets"
        },
        z="num_followers",
        color="author.username", 
        height=1000, 
        title=f"Num Tweets vs. Num Replies, {start_time}, {end_time}"
    )

    st.plotly_chart(fig)


    ##### 
    st.header("Look at an Individual User")
    st.text("One of the main ideas of this dashboard is to pick a user deemed interesting from the above plots then go look at what they are talking about below.")

    INVESTIGATE_USER = st.selectbox("Pick User", list(df_following.index.unique()))

    st.subheader("Tweet Type Distribution")
    plot_df = df_f_tweets[(df_f_tweets["author.username"]==INVESTIGATE_USER)].groupby("tweet_type").count()["id"].sort_values(ascending=False).reset_index()
    plot_df.rename(columns={"id":"count"}, inplace=True)
    fig = px.bar(plot_df, x="tweet_type", y="count", color="tweet_type", text="tweet_type", title=f"{INVESTIGATE_USER} tweet distribution")
    st.plotly_chart(fig)


if pull_data_id: 
    main()
else: 
    st.text("select an option from list above to display data")