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
from celery import Celery, Task as CeleryTask
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


logger = logging.getLogger()

WORKER: "Worker" = None


class WrappedTask(CeleryTask):
    def on_timeout(self, soft, timeout):
        super().on_timeout(soft, timeout)
        if not soft:
            logger.warning("A hard timeout was enforced for task %s", self.task.name)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super().on_failure(exc, task_id, args, kwargs, einfo)
        logger.error("Failure detected for celery task %s", task_id)
        # TODO Entrypoint to notify orchestrator & sdk of failure of task. At least in case where
        #  Celery itself or the task triggers an error. This is necessary as task is dropped but an
        #  error is published to logs. SDK wouldn't be notified otherwise.


class Worker:
    config = WorkerConfig()
    captured_logging_string = io.StringIO()

    celery_app: Celery
    celery_worker: CeleryWorker

    def _output_root_logger_to_stdout(self):
        root_logger = logging.getLogger()
        sys_stream_handler = logging.StreamHandler(sys.stdout)
        root_logger.addHandler(sys_stream_handler)
        root_logger.setLevel(self.config.log_level)

    def start(self):
        self._output_root_logger_to_stdout()

        config = self.config
        self.celery_app = Celery(
            "omotes",
            broker=f"amqp://{config.rabbitmq.username}:{config.rabbitmq.password}@{config.rabbitmq.host}:{config.rabbitmq.port}/{config.rabbitmq.virtual_host}",
            backend=f"db+postgresql://{config.postgresql.username}:{config.postgresql.password}@{config.postgresql.host}:{config.postgresql.port}/{config.postgresql.database}",
        )

        # Config of celery app
        self.celery_app.conf.task_queues = (
            KombuQueue(config.task_type.value, routing_key=config.task_type.value),
        )  # Tell the worker to listen to a specific queue for 1 workflow type.
        self.celery_app.conf.task_acks_late = True
        self.celery_app.conf.task_reject_on_worker_lost = True
        self.celery_app.conf.task_acks_on_failure_or_timeout = False
        self.celery_app.conf.worker_prefetch_multiplier = 1
        self.celery_app.conf.broker_connection_retry_on_startup = True
        # app.conf.worker_send_task_events = True  # Tell the worker to send task events.
        WrappedTask.worker = self
        self.celery_app.task(_grow_worker_task, base=WrappedTask, name=config.task_type.value, bind=True)

        logger.info("Starting GROW worker to work on task %s", config.task_type.value)
        logger.info(
            "Connected to broker rabbitmq (%s:%s/%s) as %s",
            config.rabbitmq.host,
            config.rabbitmq.port,
            config.rabbitmq.virtual_host,
            config.rabbitmq.username,
        )

        self.celery_worker = self.celery_app.Worker(
            hostname=f"worker-{config.task_type.value}@{socket.gethostname()}",
            log_level=logging.getLevelName(config.log_level),
            autoscale=(1, 1),
        )

        self.celery_worker.start()

        # logger.info(
        #     "Connected to backend postgresql (%s:%s/%s) as %s",
        #     config.postgresql.host,
        #     config.postgresql.port,
        #     config.postgresql.database,
        #     config.postgresql.username,
        # )


def _grow_worker_task(task: WrappedTask, job_id: uuid4, esdl_string: bytes) -> Any:
    """

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param task:
    :param job_id:
    :param esdl_string:
    :return: Pickled Calculation result
    """
    with BrokerInterface(config=WORKER.config.rabbitmq) as broker_if:
        # global logging_string
        # logging_string = io.StringIO()
        logger.info("GROW worker started new task %s", job_id)
        broker_if.send_message_to(
            WORKER.config.task_event_queue_name,
            pickle.dumps(
                StatusUpdateMessage(
                    omotes_job_id=job_id,
                    celery_task_id=task.request.id,
                    status=TaskStatus.STARTED,
                    task_type=WORKER.config.task_type.value,
                ).to_dict()
            ),
        )
        result = rtc_calculate(job_id, esdl_string, WORKER.config.task_type, TaskUtil(task).update_progress)
        broker_if.send_message_to(
            WORKER.config.task_event_queue_name,
            pickle.dumps(
                StatusUpdateMessage(
                    omotes_job_id=job_id,
                    celery_task_id=task.request.id,
                    status=TaskStatus.SUCCEEDED,
                    task_type=WORKER.config.task_type.value,
                ).to_dict()
            ),
        )
    return jsonpickle.encode(result)


def rtc_calculate(
    job_id: uuid4, encoded_esdl: bytes, task_type: TaskType, update_progress: Callable[[float, str], None]
) -> CalculationResult:
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
        logs="",  # TODO captured_logging_string.getvalue(),
        exit_code=0,
        input_esdl=esdl_string,
        output_esdl=solution.optimized_esdl_string,
    )
    update_progress(1.0, "Done.")
    return result
    # except Exception as ex:
    #     if len(ex.args) == 1:
    #         exit_code = 1
    #     else:
    #         exit_code = ex.args[1]
    #     return jsonpickle.encode(
    #         {"error_message": ex.args[0], "exit_code": exit_code, "logs": logging_string.getvalue()}
    #     )


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


if __name__ == "__main__":
    WORKER = Worker()
    WORKER.start()
