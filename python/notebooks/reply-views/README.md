

## Reply Views
The idea for this app started in [this thread](https://twitter.com/nicktorba/status/1537894010269814786?s=20&t=Fshmnc_FkX4JpX8p8CckyA) and this question: 
* how can I find out who is talking the most, and what about, among the people I follow on twitter? 

## Streamlit App
This is the streamlit app that is currently hosted on fly. Any updates to this app should be made here. 

## receiving_replies.ipynb
This was the notebook originally used for development

## Deployment
`fly launch` was used to create the `fly.toml`. 

The Dockerfile is used to create image for deployment, which is a simple streamlit app. 

```
fly deploy
```