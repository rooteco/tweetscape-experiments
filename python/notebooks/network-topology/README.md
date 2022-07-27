

## Streamlit App
**Important note**
* the fly commands are run from the `tweetscape-experiments/python`, **not from this directory.** This is because we need to copy over the `tweetscape-experiments/python/tweet_processing/` directory, but you have no access to parent directories when buliding docker images. 

See the the line `COPY tweet_processing ./tweet_processing` in Dockerfile to see why this is necessary.

### Create Fly App
```
fly launch --name tweetscape-experiments-seeded-streams --dockerfile notebooks/network-topology/Dockerfile --org tweetscape --path notebooks/network-topology --region ewr
```
### Deployment 

Deploy command: 
```
fly deploy -c notebooks/network-topology/fly.toml
```

The following secrets are requried and set in fly: 
```
consumer_key
consumer_secret
access_token
access_token_secret

MINIO_ROOT_USER 
MINIO_ROOT_PASSWORD
```

### Twitter Feed in Notebook 
Throwing this code here to save it for the future.
```
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
```