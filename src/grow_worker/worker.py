import base64
import io
import pickle
import sys
import socket

import jsonpickle
import os
import logging
from typing import Optional, Callable, Any
from uuid import uuid4
from pathlib import Path
from celery import Celery
from celery.signals import after_setup_logger, worker_shutting_down
from celery.apps.worker import Worker as CeleryWorker
from kombu import Queue as KombuQueue
from dataclasses import dataclass

from omotes_job_tools.messages import StatusUpdateMessage, TaskStatus, CalculationResult
from rtctools_heat_network.workflows import run_end_scenario_sizing
from omotes_job_tools.broker_interface import BrokerInterface
from omotes_job_tools.config import RabbitMQConfig as EmptyRabbitMQConfig

from grow_worker.task_util import TaskUtil
from grow_worker.worker_types import TaskType, GROWProblem, get_problem_type


class RabbitMQConfig(EmptyRabbitMQConfig):
    def __init__(self):
        super().__init__(
            host=os.environ.get("RABBITMQ_HOST", "localhost"),
            port=int(os.environ.get("RABBITMQ_PORT", "5672")),
            username=os.environ.get("RABBITMQ_USERNAME"),
            password=os.environ.get("RABBITMQ_PASSWORD"),
            virtual_host=os.environ.get("RABBITMQ_VIRTUALHOST", "omotes_celery"),
        )


class PostgreSQLConfig:
    host: str = os.environ.get("POSTGRESQL_HOST", "localhost")
    port: int = int(os.environ.get("POSTGRESQL_PORT", "5672"))
    database: str = os.environ.get("POSTGRESQL_DATABASE", "omotes_celery")
    username: Optional[str] = os.environ.get("POSTGRESQL_USERNAME")
    password: Optional[str] = os.environ.get("POSTGRESQL_PASSWORD")


class WorkerConfig:
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    postgresql: PostgreSQLConfig = PostgreSQLConfig()
    task_event_queue_name: str = os.environ.get("TASK_EVENT_QUEUE_NAME", "omotes_task_events")
    task_type: TaskType = TaskType(os.environ.get("WORKER_TASK_TYPE"))
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")


config = WorkerConfig()


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
    broker=f"amqp://{config.rabbitmq.username}:{config.rabbitmq.password}@{config.rabbitmq.host}:{config.rabbitmq.port}/{config.rabbitmq.virtual_host}",
    backend=f"db+postgresql://{config.postgresql.username}:{config.postgresql.password}@{config.postgresql.host}:{config.postgresql.port}/{config.postgresql.database}",
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
)
app.conf.task_queues = (
    KombuQueue(config.task_type.value, routing_key=config.task_type.value),
)  # Tell the worker to listen to a specific queue for 1 workflow type.
# app.conf.worker_send_task_events = True  # Tell the worker to send task events.


logger.info("Starting GROW worker to work on task %s", config.task_type.value)
logger.info(
    "Connected to broker rabbitmq (%s:%s/%s) as %s",
    config.rabbitmq.host,
    config.rabbitmq.port,
    config.rabbitmq.virtual_host,
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
    pass
    # formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    #
    # # add filehandler
    # stream_handler = logging.StreamHandler(logging_string)
    # stream_handler.setLevel(config.log_level)
    # stream_handler.setFormatter(formatter)
    # logger.addHandler(stream_handler)


# @worker_shutting_down.connect
# def shutdown(*args, **kwargs):
#     print(args, kwargs)
#     broker_if.stop()


@app.task(name=config.task_type.value, bind=True)
def grow_worker_task(self, job_id: uuid4, esdl_string: bytes):
    print(self, type(self))
    with BrokerInterface(config=config.rabbitmq) as broker_if:
        # global logging_string
        # logging_string = io.StringIO()
        logger.info("GROW worker started new task %s", job_id)
        broker_if.send_message_to(
            config.task_event_queue_name,
            pickle.dumps(
                StatusUpdateMessage(
                    omotes_job_id=job_id,
                    celery_task_id=self.request.id,
                    status=TaskStatus.STARTED,
                    task_type=config.task_type.value,
                ).to_dict()
            ),
        )
        result = rtc_calculate(job_id, esdl_string, config.task_type, TaskUtil(self).update_progress)
        broker_if.send_message_to(
            config.task_event_queue_name,
            pickle.dumps(
                StatusUpdateMessage(
                    omotes_job_id=job_id,
                    celery_task_id=self.request.id,
                    status=TaskStatus.SUCCEEDED,
                    task_type=config.task_type.value,
                ).to_dict()
            ),
        )
    return result


def rtc_calculate(
    job_id: uuid4, encoded_esdl: bytes, task_type: TaskType, update_progress: Callable[[float, str], None]
) -> Any:
    # try:
    esdl_string = encoded_esdl.decode()
    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOST" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOST", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    logger.info(f"Will write result profiles to influx: {write_result_db_profiles}. At {influxdb_host}:{influxdb_port}")

    solution: GROWProblem = run_end_scenario_sizing(
        get_problem_type(task_type),
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


worker: CeleryWorker = app.Worker(
    hostname=f"worker-{config.task_type.value}@{socket.gethostname()}",
    log_level=logging.getLevelName(config.log_level),
    autoscale=(1, 1),
)

worker.start()
