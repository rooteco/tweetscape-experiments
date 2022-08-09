## Remote Dev Environment Notes

Because of crazy bad latency, I needed to get a remote dev environment running on fly.io. 

Did so by following [this template](https://github.com/fly-apps/vscode-remote). 

Had to run the following commands manually (not sure why): 
```
fly deploy --build-arg USER=$(whoami) --build-arg EXTRA_PKGS="$extrapackages" $usedocker

fly volumes create data --region ewr $disksize
```

Then I could connect with vscode remote extension with the following thing: 
```
nick@follows-views-remote-dev.fly.dev
```

## Miniconda 
```
source miniconda3/bin/activate
conda activate tweetscape
```

## Proxy 
```
fly proxy 8501:8501 -a follows-views-remote-dev
```

## Streamlit
With the proxy running, I can access the app at localhost:8501  
```
streamlit run streamlit_app.py
```


