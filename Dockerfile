FROM python:3.8-slim-buster

WORKDIR /app

RUN mkdir /app/input_esdl_files/ /app/output_esdl_files/
ENV PYTHONPATH='/app/'
ENV INPUT_FILES_DIR="/app/input_esdl_files/"
ENV OUTPUT_FILES_DIR="/app/output_esdl_files/"

COPY requirements.txt /app/grow_worker/requirements.txt
RUN pip install -r /app/grow_worker/requirements.txt --no-cache-dir

COPY src/grow_worker                 /app/grow_worker/
COPY src/grow_runner              /app/grow_runner/

ENTRYPOINT grow_worker/celery.sh
