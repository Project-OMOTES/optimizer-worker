import base64

import os
import logging
from typing import Any
from uuid import uuid4
from pathlib import Path
from celery.signals import after_setup_logger, worker_shutting_down

from omotes_sdk.internal.orchestrator_worker_events.messages import CalculationResult
from omotes_sdk.internal.worker.worker import WorkerTask, initialize_worker, UpdateProgressHandler
from rtctools_heat_network.workflows import run_end_scenario_sizing

from grow_worker.worker_types import GrowTaskType, GROWProblem, get_problem_type


logger = logging.getLogger("grow_worker")
GROW_TASK_TYPE = GrowTaskType(os.environ.get("GROW_WORKER_TASK_TYPE"))


def grow_worker_task(
    task: WorkerTask, job_id: uuid4, esdl_string: bytes, update_progress_handler: UpdateProgressHandler
) -> Any:
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
    result = rtc_calculate(job_id, esdl_string, update_progress_handler)
    return result


def rtc_calculate(job_id: uuid4, encoded_esdl: bytes, update_progress: UpdateProgressHandler) -> CalculationResult:
    # try:
    esdl_string = encoded_esdl.decode()
    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOST" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOST", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    logger.info(f"Will write result profiles to influx: {write_result_db_profiles}. At {influxdb_host}:{influxdb_port}")

    solution: GROWProblem = run_end_scenario_sizing(
        get_problem_type(GROW_TASK_TYPE),
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
    initialize_worker(GROW_TASK_TYPE.value, grow_worker_task)
