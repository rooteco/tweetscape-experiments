

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