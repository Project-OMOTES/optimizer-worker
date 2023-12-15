FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt /app/grow_worker/requirements.txt
RUN pip install -r /app/grow_worker/requirements.txt --no-cache-dir

COPY src/grow_worker                 /app/grow_worker/

ENTRYPOINT grow_worker/celery.sh
