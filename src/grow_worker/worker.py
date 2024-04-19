import base64

import os
import logging
from pathlib import Path
from typing import cast

from omotes_sdk.internal.worker.worker import initialize_worker, UpdateProgressHandler
from omotes_sdk.types import ParamsDict
from mesido.esdl.esdl_parser import ESDLStringParser
from mesido.esdl.profile_parser import InfluxDBProfileReader

from grow_worker.worker_types import (
    GrowTaskType,
    GROWProblem,
    get_problem_type,
    get_problem_function,
)

logger = logging.getLogger("grow_worker")
GROW_TASK_TYPE = GrowTaskType(os.environ.get("GROW_TASK_TYPE"))


def grow_worker_task(
    input_esdl: str, params_dict: ParamsDict, update_progress_handler: UpdateProgressHandler
) -> str:
    """Run the grow worker task and run configured specific problem type for this worker instance.

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param input_esdl: The input ESDL XML string.
    :param params_dict: Extra parameters to configure this run.
    :param update_progress_handler: Handler to notify of any progress changes.
    :return: GROW optimized or simulated ESDL
    """
    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOSTNAME" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOSTNAME", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    logger.info(
        f"Will write result profiles to influx: {write_result_db_profiles}. "
        f"At {influxdb_host}:{influxdb_port}"
    )

    solution: GROWProblem = get_problem_function(GROW_TASK_TYPE)(
        get_problem_type(GROW_TASK_TYPE),
        base_folder=base_folder,
        esdl_string=base64.encodebytes(input_esdl.encode("utf-8")),
        esdl_parser=ESDLStringParser,
        write_result_db_profiles=write_result_db_profiles,
        influxdb_host=influxdb_host,
        influxdb_port=influxdb_port,
        influxdb_username=os.environ.get("INFLUXDB_USERNAME"),
        influxdb_password=os.environ.get("INFLUXDB_PASSWORD"),
        influxdb_ssl=False,
        influxdb_verify_ssl=False,
        update_progress_function=update_progress_handler,
        profile_reader=InfluxDBProfileReader,
    )

    return cast(str, solution.optimized_esdl_string)


if __name__ == "__main__":
    initialize_worker(GROW_TASK_TYPE.value, grow_worker_task)
