FROM python:3.10-slim-buster

WORKDIR /app

COPY optimizer-worker/requirements.txt /app/grow_worker/requirements.txt
RUN pip install -r /app/grow_worker/requirements.txt --no-cache-dir

COPY ../omotes-sdk-protocol/python/ /omotes-sdk-protocol/python/
COPY ../omotes-sdk-python/ /omotes-sdk-python/
RUN pip install /omotes-sdk-python/
RUN pip install /omotes-sdk-protocol/python/

COPY optimizer-worker/src/grow_worker                 /app/grow_worker/

CMD ["python3", "-m", "grow_worker.worker"]
