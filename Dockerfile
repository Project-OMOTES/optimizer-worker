FROM python:3.8-slim-buster

WORKDIR /app

RUN mkdir /app/input_esdl_files/ /app/output_esdl_files/
ENV PYTHONPATH='/app/'
ENV INPUT_FILES_DIR="/app/input_esdl_files/"
ENV OUTPUT_FILES_DIR="/app/output_esdl_files/"

COPY requirements.txt /app/optimizer_worker/requirements.txt
RUN pip install -r /app/optimizer_worker/requirements.txt && \
    pip cache purge

COPY src/optimizer_worker                 /app/optimizer_worker/
COPY src/optimization_runner              /app/optimization_runner/

CMD ["python3", "-u", "-m", "optimizer_worker.main"]
