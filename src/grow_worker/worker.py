import base64

import os
import logging
from pathlib import Path
from typing import Dict

from celery.signals import after_setup_logger

from omotes_sdk.internal.worker.worker import initialize_worker, UpdateProgressHandler
from rtctools_heat_network.workflows import run_end_scenario_sizing

from grow_worker.worker_types import GrowTaskType, GROWProblem, get_problem_type

logger = logging.getLogger("grow_worker")
GROW_TASK_TYPE = GrowTaskType(os.environ.get("GROW_TASK_TYPE"))


def grow_worker_task(
    input_esdl: str, workflow_config: Dict[str, str], update_progress_handler: UpdateProgressHandler
) -> str:
    """

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param input_esdl:
    :param workflow_config:
    :param update_progress_handler:
    :return: GROW optimized or simulated ESDL
    """
    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOSTNAME" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOSTNAME", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    logger.info(
        f"Will write result profiles to influx: {write_result_db_profiles}. " f"At {influxdb_host}:{influxdb_port}"
    )

    solution: GROWProblem = run_end_scenario_sizing(
        get_problem_type(GROW_TASK_TYPE),
        base_folder=base_folder,
        esdl_string=base64.encodebytes(input_esdl.encode("utf-8")),
        write_result_db_profiles=write_result_db_profiles,
        influxdb_host=influxdb_host,
        influxdb_port=influxdb_port,
        influxdb_username=os.environ.get("INFLUXDB_USERNAME"),
        influxdb_password=os.environ.get("INFLUXDB_PASSWORD"),
        influxdb_ssl=False,
        influxdb_verify_ssl=False,
        update_progress_function=update_progress_handler,
    )

    return solution.optimized_esdl_string


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
