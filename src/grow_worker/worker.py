import io
import jsonpickle
import os
import logging
from typing import Optional, Callable, Any
from uuid import uuid4
from pathlib import Path
from celery import Celery
from celery.signals import after_setup_logger
from dataclasses import dataclass

from grow_worker.task_util import TaskUtil
from grow_worker.types import WorkFlowType, GROWProblem, get_problem_type
from rtctools_heat_network.workflows import run_end_scenario_sizing

app = Celery(
    "omotes",
    broker="amqp://user:bitnami@rabbitmq",
    backend="rpc://user:bitnami@rabbitmq",
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

logger = logging.getLogger(__name__)
logging_string = io.StringIO()


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # add filehandler
    global logging_string
    logging_string = io.StringIO()
    stream_handler = logging.StreamHandler(logging_string)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


@app.task(name="optimizer-task", bind=True)
def optimize(self, job_id: uuid4, esdl_string: str):
    logger.info("optimizer worker started")
    return rtc_calculate(job_id, esdl_string, WorkFlowType.GROW_OPTIMIZER, TaskUtil(self).update_progress)


@app.task(name="simulator-task", bind=True)
def simulate(self, job_id: uuid4, esdl_string: str):
    logger.info("simulation worker started")
    return rtc_calculate(job_id, esdl_string, WorkFlowType.GROW_SIMULATOR, TaskUtil(self).update_progress)


@dataclass
class CalculationResult:
    job_id: uuid4
    exit_code: int
    logs: str
    input_esdl: str
    output_esdl: Optional[str]


def rtc_calculate(
    job_id: uuid4, esdl_string: str, workflow_type: WorkFlowType, update_progress: Callable[[float, str], None]
) -> Any:
    try:
        base_folder = Path(__file__).resolve().parent.parent
        write_result_db_profiles = "INFLUXDB_HOST" in os.environ
        influxdb_host = os.environ.get("INFLUXDB_HOST", "localhost")
        influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

        print(f"Will write result profiles to influx: {write_result_db_profiles}. At {influxdb_host}:{influxdb_port}")

        raise Exception("final crash", 200)

        solution: GROWProblem = run_end_scenario_sizing(
            get_problem_type(workflow_type),
            base_folder=base_folder,
            esdl_string=esdl_string,
            write_result_db_profiles=write_result_db_profiles,
            influxdb_host=influxdb_host,
            influxdb_port=influxdb_port,
            influxdb_username=os.environ.get("INFLUXDB_USERNAME"),
            influxdb_password=os.environ.get("INFLUXDB_PASSWORD"),
            influxdb_ssl=False,
            influxdb_verify_ssl=False,
            update_progress_function=update_progress,
        )

        # update_progress(0.99, "almost done")

        result = CalculationResult(
            job_id=job_id,
            logs=logging_string.getvalue(),
            exit_code=0,
            input_esdl=esdl_string,
            output_esdl=solution.optimized_esdl_string,
        )
        return jsonpickle.encode(result)
    except Exception as ex:
        if len(ex.args) == 1:
            exit_code = 1
        else:
            exit_code = ex.args[1]
        return jsonpickle.encode(
            {"error_message": ex.args[0], "exit_code": exit_code, "logs": logging_string.getvalue()}
        )
