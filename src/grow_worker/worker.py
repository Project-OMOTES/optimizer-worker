import base64
import logging
import os
from pathlib import Path
from typing import Any, cast

import esdl
from dotenv import load_dotenv
from mesido.esdl.esdl_mixin import DBAccessType, InfluxDBProfileReader
from mesido.esdl.esdl_parser import ESDLStringParser
from mesido.exceptions import MesidoAssetIssueError
from omotes_sdk.internal.worker.worker import UpdateProgressHandler, initialize_worker
from omotes_sdk.types import ProtobufDict
from pydantic import BaseModel, Field

from esdl_messages import (
    EsdlMessage,
    MessageSeverity,
)
from grow_worker.log_forwarding import StdCaptureToLogSession
from grow_worker.worker_types import (
    GROWProblem,
    GrowTaskType,
    get_problem_function,
    get_problem_type,
    get_solver_class,
)
from prefect_util import (
    Failed,
    State,
    create_flow_progress_updater,
    flow,
    load_gurobi_license,
    write_flow_return_artifact_to_minio,
)

load_dotenv()  # Load environment variables from .env file


# GROW_TASK_TYPES = [GrowTaskType(task_type) for task_type in os.environ["GROW_TASK_TYPE"].split(",")]


class EarlySystemExit(Exception):
    """Wrapper for `SystemExit` exception.

    To ensure that the worker process does not shut down but rather handles the `SystemExit` as an
    error
    """

    ...


class OptimizerFlowResult(BaseModel):
    output_esdl: str | None = Field(default=None, json_schema_extra={"file_extension": ".esdl"})
    esdl_messages: list[EsdlMessage] = Field(default_factory=list, json_schema_extra={"file_extension": ".json"})


@flow
def optimizer_flow(
    input_esdl: str,
    workflow_config: dict,
    workflow_type_name: str,
) -> OptimizerFlowResult | State[Any]:
    """Prefect flow function for the optimizer worker.

    :param input_esdl: The input ESDL XML string.
    :param workflow_config: Extra parameters to configure this run.
    :param workflow_type_name: Name of the workflow.
    :return: GROW optimized or simulated ESDL and a list of ESDL feedback messages.
    """
    logging.info("Starting optimizer flow with workflow type: %s", workflow_type_name)
    _update_flow_progress = create_flow_progress_updater(
        start_progress_fraction=0.0,
        start_description="Starting optimizer flow",
    )

    # Capture logging and print statemnents, and forward to logger.
    with StdCaptureToLogSession():
        try:
            _update_flow_progress(0.1, "Preparing workflow and solver")

            workflow_type = GrowTaskType(workflow_type_name)
            mesido_func = get_problem_function(workflow_type)
            mesido_workflow = get_problem_type(workflow_type)
            mesido_solver = get_solver_class(workflow_type)

            if "gurobi" in workflow_type_name.lower():
                load_gurobi_license()

            base_folder = Path(__file__).resolve().parent.parent

            output_esdl: str | None = None
            esdl_messages: list[EsdlMessage] = []

            _update_flow_progress(0.35, "Running mesido optimization")

            solution: GROWProblem = mesido_func(
                mesido_workflow,
                solver_class=mesido_solver,
                base_folder=base_folder,
                esdl_string=base64.encodebytes(input_esdl.encode("utf-8")),
                esdl_parser=ESDLStringParser,
                write_result_db_profiles=False,
                database_connections=[
                    {
                        "access_type": DBAccessType.READ_WRITE,
                        "influxdb_host": "omotes_influxdb",
                        "influxdb_port": 8096,
                        "influxdb_username": "root",
                        "influxdb_password": "9012",
                        "influxdb_ssl": False,
                        "influxdb_verify_ssl": False,
                    },
                ],
                update_progress_function=lambda *_args, **_kwargs: None,
                profile_reader=InfluxDBProfileReader,
            )
            output_esdl = cast(str, solution.optimized_esdl_string)

            _update_flow_progress(1.0, "Optimization completed")

            # TODO get esdl_messages from successful run after mesido update.
            success_result = OptimizerFlowResult(
                output_esdl=output_esdl,
                esdl_messages=esdl_messages,
            )
            write_flow_return_artifact_to_minio(success_result)
        except Exception as e:
            logging.exception("Exception during optimizer flow")

            esdl_messages: list[EsdlMessage] = []
            if isinstance(e, MesidoAssetIssueError):
                esdl_messages = parse_mesido_esdl_messages(e.general_issue, e.message_per_asset_id)
                logging.info(f"ESDL Messages: {esdl_messages}")

            failed_result = OptimizerFlowResult(output_esdl=None, esdl_messages=esdl_messages)
            write_flow_return_artifact_to_minio(failed_result)

            return Failed(message=f"Optimizer flow failed: {e}")


def grow_worker_task(
    input_esdl: str,
    workflow_config: ProtobufDict,
    update_progress_handler: UpdateProgressHandler,
    workflow_type_name: str,
) -> tuple[str | None, list[EsdlMessage]]:
    """Run the grow worker task and run configured specific problem type for this worker instance.

    Note: Be careful! This spawns within a subprocess and gains a copy of memory from parent
    process. You cannot open sockets and other resources in the main process and expect
    it to be copied to subprocess. Any resources e.g. connections/sockets need to be opened
    in this task by the subprocess.

    :param input_esdl: The input ESDL XML string.
    :param workflow_config: Extra parameters to configure this run.
    :param update_progress_handler: Handler to notify of any progress changes.
    :param workflow_type_name: Name of the workflow.
    :return: GROW optimized or simulated ESDL and a list of ESDL feedback messages.
    """
    workflow_type = GrowTaskType(workflow_type_name)
    mesido_func = get_problem_function(workflow_type)
    mesido_workflow = get_problem_type(workflow_type)
    mesido_solver = get_solver_class(workflow_type)

    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOSTNAME" in os.environ or "POSTGRES_HOSTNAME" in os.environ
    db_type_output_profiles_name = os.environ.get("DB_TYPE_OUTPUT_PROFILES", "POSTGRESQL").upper()
    db_type_output_profiles = getattr(esdl.DatabaseTypeEnum, db_type_output_profiles_name, None)
    if db_type_output_profiles is None:
        logging.warning(
            "Unknown DB_TYPE_OUTPUT_PROFILES '%s', defaulting to POSTGRESQL",
            db_type_output_profiles_name,
        )
        db_type_output_profiles = esdl.DatabaseTypeEnum.POSTGRESQL
    influxdb_host = os.environ.get("INFLUXDB_HOSTNAME")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))
    postgres_host = os.environ.get("POSTGRES_HOSTNAME")
    postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))

    logging.info(
        "Will write result profiles to influx: %s. At %s:%s",
        write_result_db_profiles,
        influxdb_host,
        influxdb_port,
    )

    database_connection = []
    if influxdb_host:
        database_connection.append({
            "access_type": (
                DBAccessType.READ_WRITE
                if db_type_output_profiles == esdl.DatabaseTypeEnum.INFLUXDB
                else DBAccessType.READ
            ),
            "host": influxdb_host,
            "port": influxdb_port,
            "username": os.environ.get("INFLUXDB_USERNAME"),
            "password": os.environ.get("INFLUXDB_PASSWORD"),
            "ssl": False,
            "verify_ssl": False,
        })
    if postgres_host:
        database_connection.append({
            "access_type": (
                DBAccessType.READ_WRITE
                if db_type_output_profiles == esdl.DatabaseTypeEnum.POSTGRESQL
                else DBAccessType.READ
            ),
            "host": postgres_host,
            "port": postgres_port,
            "username": os.environ.get("POSTGRES_USERNAME"),
            "password": os.environ.get("POSTGRES_PASSWORD"),
        })

    esdl_str = None
    esdl_messages = []
    try:
        solution: GROWProblem = mesido_func(
            mesido_workflow,
            solver_class=mesido_solver,
            base_folder=base_folder,
            esdl_string=base64.encodebytes(input_esdl.encode("utf-8")),
            esdl_parser=ESDLStringParser,
            write_result_db_profiles=write_result_db_profiles,
            db_type_output_profiles=db_type_output_profiles,
            database_connections=database_connection,
            update_progress_function=update_progress_handler,
            profile_reader=ESDLProfileReader,
        )
        esdl_str = cast(str, solution.optimized_esdl_string)
        # TODO get esdl_messages from successful run after mesido update.
    except MesidoAssetIssueError as mesido_issues_error:
        esdl_messages = parse_mesido_esdl_messages(
            mesido_issues_error.general_issue, mesido_issues_error.message_per_asset_id
        )
    except SystemExit as e:
        raise EarlySystemExit(e)
    except Exception:
        # in case of general mesido error, make sure to return esdl_str and esdl_messages
        pass

    return esdl_str, esdl_messages


def parse_mesido_esdl_messages(general_message: str, object_messages: dict[str, str]) -> list[EsdlMessage]:
    """Convert mesido messages to a list of esdl messages in omotes format.

    :param general_message: general message (not related to a specific ESDL object).
    :param object_messages: esdl object messages per object id.
    :return: list of EsdlMessage dataclass objects.
    """
    # TODO get severity from esdl message and add list of general messages after mesido update.
    esdl_messages = []

    if general_message:
        esdl_messages.append(EsdlMessage(technical_message=general_message, severity=MessageSeverity.ERROR))
    for object_id, message in object_messages.items():
        esdl_messages.append(
            EsdlMessage(
                technical_message=message,
                severity=MessageSeverity.ERROR,
                esdl_object_id=object_id,
            )
        )
    return esdl_messages


if __name__ == "__main__":
    initialize_worker([task_type.value for task_type in GROW_TASK_TYPES], cast(Any, grow_worker_task))
