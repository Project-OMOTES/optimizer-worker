import base64
import io
import sys
import socket

import jsonpickle
import os
import logging
from typing import Optional, Callable, Any
from uuid import uuid4
from pathlib import Path
from celery import Celery
from celery.signals import after_setup_logger
from celery.apps.worker import Worker as CeleryWorker
from kombu import Queue as KombuQueue
from dataclasses import dataclass

from grow_worker.task_util import TaskUtil
from grow_worker.types import WorkFlowType, GROWProblem, get_problem_type
from rtctools_heat_network.workflows import run_end_scenario_sizing


class RabbitMQConfig:
    host: str = os.environ.get("RABBITMQ_HOST", "localhost")
    port: int = int(os.environ.get("RABBITMQ_PORT", "5672"))
    username: Optional[str] = os.environ.get("RABBITMQ_USERNAME")
    password: Optional[str] = os.environ.get("RABBITMQ_PASSWORD")
    virtualhost: str = os.environ.get("RABBITMQ_VIRTUALHOST", "omotes_celery")


class PostgreSQLConfig:
    host: str = os.environ.get("POSTGRESQL_HOST", "localhost")
    port: int = int(os.environ.get("POSTGRESQL_PORT", "5672"))
    database: str = os.environ.get("POSTGRESQL_DATABASE", "omotes_celery")
    username: Optional[str] = os.environ.get("POSTGRESQL_USERNAME")
    password: Optional[str] = os.environ.get("POSTGRESQL_PASSWORD")


class Config:
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    postgresql: PostgreSQLConfig = PostgreSQLConfig()
    workflow_type: WorkFlowType = WorkFlowType(os.environ.get("WORKER_WORKFLOW_TYPE"))
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")


config = Config()


logger = logging.getLogger()
logging_string = io.StringIO()


def output_root_logger_to_stdout():
    root_logger = logging.getLogger()
    sys_stream_handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(sys_stream_handler)
    root_logger.setLevel(config.log_level)


output_root_logger_to_stdout()

app = Celery(
    "omotes",
    broker=f"amqp://{config.rabbitmq.username}:{config.rabbitmq.password}@{config.rabbitmq.host}:{config.rabbitmq.port}/{config.rabbitmq.virtualhost}",
    backend=f"db+postgresql://{config.postgresql.username}:{config.postgresql.password}@{config.postgresql.host}:{config.postgresql.port}/{config.postgresql.database}",
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
)
app.conf.task_queues = (KombuQueue(config.workflow_type.value, routing_key=config.workflow_type.value),)  # Tell the worker to listen to a specific queue for 1 workflow type.
#app.conf.worker_send_task_events = True  # Tell the worker to send task events.

logger.info("Starting GROW worker as %s", config.workflow_type.value)
logger.info(
    "Connected to broker rabbitmq (%s:%s/%s) as %s",
    config.rabbitmq.host,
    config.rabbitmq.port,
    config.rabbitmq.virtualhost,
    config.rabbitmq.username,
)
logger.info(
    "Connected to backend postgresql (%s:%s/%s) as %s",
    config.postgresql.host,
    config.postgresql.port,
    config.postgresql.database,
    config.postgresql.username,
)


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    # formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    #
    # # add filehandler
    # stream_handler = logging.StreamHandler(logging_string)
    # stream_handler.setLevel(config.log_level)
    # stream_handler.setFormatter(formatter)
    # logger.addHandler(stream_handler)


@app.task(name=config.workflow_type.value, bind=True)
def grow_worker_task(self, job_id: uuid4, esdl_string: bytes):
    global logging_string
    logging_string = io.StringIO()
    logger.info("GROW worker started new task %s", job_id)
    return rtc_calculate(job_id, esdl_string, config.workflow_type, TaskUtil(self).update_progress)


@dataclass
class CalculationResult:
    job_id: uuid4
    exit_code: int
    logs: str
    input_esdl: str
    output_esdl: Optional[str]


def rtc_calculate(
    job_id: uuid4, encoded_esdl: bytes, workflow_type: WorkFlowType, update_progress: Callable[[float, str], None]
) -> Any:
    # try:
    esdl_string = encoded_esdl.decode()
    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOST" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOST", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    logger.info(f"Will write result profiles to influx: {write_result_db_profiles}. At {influxdb_host}:{influxdb_port}")

    solution: GROWProblem = run_end_scenario_sizing(
        get_problem_type(workflow_type),
        base_folder=base_folder,
        esdl_string=base64.encodebytes(esdl_string.encode("utf-8")),
        write_result_db_profiles=write_result_db_profiles,
        influxdb_host=influxdb_host,
        influxdb_port=influxdb_port,
        influxdb_username=os.environ.get("INFLUXDB_USERNAME"),
        influxdb_password=os.environ.get("INFLUXDB_PASSWORD"),
        influxdb_ssl=False,
        influxdb_verify_ssl=False,
        update_progress_function=update_progress,
    )

    update_progress(0.99, "Almost done.")

    result = CalculationResult(
        job_id=job_id,
        logs=logging_string.getvalue(),
        exit_code=0,
        input_esdl=esdl_string,
        output_esdl=solution.optimized_esdl_string,
    )
    update_progress(1.0, "Done.")
    return jsonpickle.encode(result)
    # except Exception as ex:
    #     if len(ex.args) == 1:
    #         exit_code = 1
    #     else:
    #         exit_code = ex.args[1]
    #     return jsonpickle.encode(
    #         {"error_message": ex.args[0], "exit_code": exit_code, "logs": logging_string.getvalue()}
    #     )


worker: CeleryWorker = app.Worker(hostname=f"worker-{config.workflow_type.value}@{socket.gethostname()}",
                                  log_level=logging.getLevelName(config.log_level),
                                  autoscale=(1, 1))

worker.start()
