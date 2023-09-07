FROM python:3.8-slim-buster

WORKDIR /app

RUN mkdir /app/input_esdl_files/ /app/output_esdl_files/
ENV PYTHONPATH='/app/'

COPY requirements.txt /app/optimizer_worker/requirements.txt
RUN pip install -r /app/optimizer_worker/requirements.txt

COPY src/optimizer_worker                 /app/optimizer_worker/
COPY src/optimization_runner              /app/optimization_runner/

CMD ["python3", "-u", "-m", "optimizer_worker.main"]
