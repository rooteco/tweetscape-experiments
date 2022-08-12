ARG PYTHON_VERSION=3.10

FROM python:${PYTHON_VERSION}

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    python3-wheel

RUN mkdir -p /app
WORKDIR /app

COPY streams-mvp/requirements.txt .
RUN pip install -r requirements.txt


COPY streams-mvp/streamlit_app.py . 
COPY tweet_processing ./tweet_processing
COPY streamlit_twitter_feed ./streamlit_twitter_feed

RUN pip install ./tweet_processing
RUN pip install ./streamlit_twitter_feed

EXPOSE 8501

# replace APP_NAME with module name
ENTRYPOINT ["streamlit", "run"]
CMD ["streamlit_app.py"]
