

## Deploy Minio to Fly 
The point of this is to store experimental data remotely so it is easily accessible to anyone without having to pull again from twitter api. 

Will be useful for streamlit experiments and hosted notebooks. 

### Guide
Fly has a [deployment guide](https://fly.io/docs/app-guides/minio/), but it is outdated, so some changes had to be made. 

#### Preparing
Create the dockerfile
```
FROM minio/minio

EXPOSE 9000
EXPOSE 9001 

CMD [ "server", "/data", "--console-address", ":9001"]
```
Ports 9000 and 9001 are used for the console and the api.
The console is the UI, the api is how the python client executes commands. 

#### Init and Launch
```
fly launch --name experiment-data-minio --org tweetscape
```
This command creates the `fly.toml` file. 

Following the fly.io guide, I appended the following the section: 
```
[mounts]
  source="miniodata"
  destination="/data"
```

I also changed the internal_ports field to 9001, to match the console service. 

#### Disk Storage
Same as fly.io guide. 
```
fly vol create miniodata --region ewr
```

#### Secrets
```
fly secrets set MINIO_ROOT_USER=appkatarootuserkey MINIO_ROOT_PASSWORD=appkatarootpasskey
```

#### Deploying 
```
fly deploy
```

## Access Via Console
This will open to port 9001 to an s3-like experience. 
```
fly open
```

## Commands via python
Using the [python minio client](https://docs.min.io/docs/python-client-quickstart-guide.html) with the following client init:
 
```python
minio_client = Minio(
    # 'experiment-data-minio.fly.dev:9000',
    'localhost:9000', # running a local proxy to fly
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False
)
```