

import requests
from IPython.display import display, Markdown

class Tweet(object):
    """
    This class is used to display tweets in feeds in the notebook
    """
    def __init__(self, s, embed_str=False):
        if not embed_str:
            # Use Twitter's oEmbed API
            # https://dev.twitter.com/web/embedded-tweets
            api = 'https://publish.twitter.com/oembed?url={}'.format(s)
            response = requests.get(api)
            self.text = response.json()["html"]
        else:
            self.text = s

    def _repr_html_(self):
        return self.text
    
def display_feed(tweet_links): 
    feed = ""

    for link in tweet_links:
        feed += Tweet(link)._repr_html_()

    display(Markdown(feed))
    