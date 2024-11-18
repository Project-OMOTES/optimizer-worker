import base64
import logging
import multiprocessing
import multiprocessing.pool
import signal
import time
from multiprocessing.process import current_process
import os
from pathlib import Path
from typing import cast, Dict, List, Tuple, Optional

from mesido.exceptions import MesidoAssetIssueError
from omotes_sdk.internal.orchestrator_worker_events.esdl_messages import (
    EsdlMessage,
    MessageSeverity,
)
from omotes_sdk.internal.worker.worker import initialize_worker, UpdateProgressHandler
from omotes_sdk.types import ProtobufDict
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


class EarlySystemExit(Exception):
    """Wrapper for `SystemExit` exception.

    To ensure that the worker process does not shutdown but rather handles the `SystemExit` as an
    error
    """

    ...


def run_mesido(input_esdl: str) -> Tuple[Optional[str], List[EsdlMessage]]:
    """Run mesido using the specific workflow.

    Note: This is run without a subprocess! Casadi does not yield the GIL and therefore
    causes starved thread issues.

    :param input_esdl: The input ESDL XML string.
    :return: GROW optimized or simulated ESDL
    """
    mesido_func = get_problem_function(GROW_TASK_TYPE)
    mesido_workflow = get_problem_type(GROW_TASK_TYPE)

    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOSTNAME" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOSTNAME", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    logger.info(
        "Will write result profiles to influx: %s. At %s:%s",
        write_result_db_profiles,
        influxdb_host,
        influxdb_port,
    )
    try:
        solution: GROWProblem = mesido_func(
            mesido_workflow,
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
            update_progress_function=None,
            profile_reader=InfluxDBProfileReader,
        )
        esdl_str = cast(str, solution.optimized_esdl_string)
        # TODO get esdl_messages from solution after mesido update.
        esdl_messages = []
    except MesidoAssetIssueError as mesido_issues_error:
        esdl_str = None
        esdl_messages = parse_mesido_esdl_messages(
            mesido_issues_error.general_issue, mesido_issues_error.message_per_asset_id
        )
    except SystemExit as e:
        raise EarlySystemExit(e)

    return esdl_str, esdl_messages


def parse_mesido_esdl_messages(
    general_message: str, object_messages: Dict[str, str]
) -> List[EsdlMessage]:
    """Convert mesido messages to a list of esdl messages in omotes format.

    :param general_message: general message (not related to a specific ESDL object).
    :param object_messages: esdl object messages per object id.
    :return: list of EsdlMessage protobuf objects.
    """
    # TODO get severity from esdl message and add list of general messages after mesido update.
    esdl_messages = []

    if general_message:
        esdl_messages.append(
            EsdlMessage(technical_message=general_message, severity=MessageSeverity.ERROR)
        )
    for object_id, message in object_messages.items():
        esdl_messages.append(
            EsdlMessage(
                technical_message=message,
                severity=MessageSeverity.ERROR,
                esdl_object_id=object_id,
            )
        )
    return esdl_messages


def kill_pool(pool: multiprocessing.pool.Pool) -> None:
    """Terminate all the process of a multiprocessing.Pool with SIGKILL.

    Found here: https://stackoverflow.com/a/47580796

    multiprocessing.Pool.terminate does not provide a way to give a different signal than SIGTERM
    so this function hooks into the internals to properly handle sending SIGKILL to all processes in
    the pool.

    :param pool: The multiprocessing to kill all processes in.
    """
    #
    # stop repopulating new child
    pool._state = multiprocessing.pool.TERMINATE  # type: ignore[attr-defined]
    pool._worker_handler._state = multiprocessing.pool.TERMINATE  # type: ignore[attr-defined]
    for p in pool._pool:  # type: ignore[attr-defined]
        if p.is_alive():
            logger.warning("Sending SIGKILL to pool process with pid %s", p.pid)
            os.kill(p.pid, signal.SIGKILL)
    # .is_alive() will reap dead process
    wait_till = time.time() + 5.0
    while (
        any(p.is_alive() for p in pool._pool)  # type: ignore[attr-defined]
        and time.time() < wait_till
    ):
        pass
    logger.warning("All processes in pool have been terminated.")
    pool.terminate()
    logger.warning("Forceful pool termination completed.")


def grow_worker_task(
    input_esdl: str, workflow_config: ProtobufDict, update_progress_handler: UpdateProgressHandler
) -> Tuple[Optional[str], List[EsdlMessage]]:
    """Run the grow worker task and run configured specific problem type for this worker instance.

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param input_esdl: The input ESDL XML string.
    :param workflow_config: Extra parameters to configure this run.
    :param update_progress_handler: Handler to notify of any progress changes.
    :return: GROW optimized or simulated ESDL
    """
    # TODO Very nasty hack. Celery unfortunately starts the worker subprocesses as 'daemons'
    #  which prevents this process from creating any other subprocesses. Therefore, we
    #  acknowledge this process is a daemon and turn of the protectioon that prevents new
    #  subprocesses from being created. This does introduce the issue that if this
    #  process is killed/cancelled/revoked, the subprocess will continue as a zombie process.
    #  See https://github.com/Project-OMOTES/optimizer-worker/issues/54
    current_process()._config["daemon"] = False  # type: ignore[attr-defined]

    with multiprocessing.Pool(1) as pool:
        try:
            output = pool.map(run_mesido, [input_esdl])[0]
        except SystemExit as e:
            logger.warning("During pool the worker was requested to quit: %s %s", type(e), e)
            kill_pool(pool)
            raise

    return output


if __name__ == "__main__":
    initialize_worker(GROW_TASK_TYPE.value, grow_worker_task)
