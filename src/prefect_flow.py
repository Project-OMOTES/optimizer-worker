import base64
import logging
import os
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from esdl import EnergySystem
from esdl.esdl_handler import EnergySystemHandler
from mesido.esdl.esdl_mixin import DBAccessType, ESDLOutputProfilesType
from mesido.esdl.esdl_parser import ESDLStringParser
from mesido.esdl.profile_parser import ESDLProfileReader
from mesido.exceptions import MesidoAssetIssueError
from pydantic import BaseModel, Field

from grow_worker.esdl_messages import (
    EsdlMessage,
    MessageSeverity,
)
from grow_worker.log_forwarding import StdCaptureToLogSession
from grow_worker.prefect_util import (
    Failed,
    State,
    create_flow_progress_updater,
    flow,
    flow_run,
    in_prefect_flow_context,
    load_gurobi_license,
    write_flow_return_artifact_to_minio,
)
from worker_types import (
    GrowTaskType,
    get_problem_function,
    get_problem_type,
    get_solver_class,
)

load_dotenv()  # Load environment variables from .env file


class OptimizerFlowResult(BaseModel):
    """Flow result payload written as artifact output."""

    output_esdl: str | None = Field(default=None, json_schema_extra={"file_extension": ".esdl"})
    esdl_messages: list[dict[str, Any]] = Field(default_factory=list, json_schema_extra={"file_extension": ".json"})


@flow
def optimizer_flow(
    input_esdl: str,
    workflow_config: dict,
    workflow_type_name: str,
) -> OptimizerFlowResult | State[Any] | None:
    """Prefect flow function for the optimizer worker.

    Args:
        input_esdl: The input ESDL XML string.
        workflow_config: Extra parameters to configure this run.
        workflow_type_name: Name of the workflow.

    Returns:
        OptimizerFlowResult | State[Any] | None: Failed state when execution fails; otherwise no value is
        returned from this flow function.

    """
    logging.info("Starting optimizer flow with workflow type: %s", workflow_type_name)
    _update_flow_progress = create_flow_progress_updater(
        start_progress_fraction=0.0,
        start_description="Starting optimizer flow",
    )

    # Capture and forward solver output only during orchestrated Prefect flow runs.
    capture_session = StdCaptureToLogSession() if in_prefect_flow_context() else nullcontext()
    with capture_session:
        try:
            workflow_type = GrowTaskType(workflow_type_name)
            mesido_func = get_problem_function(workflow_type)
            mesido_workflow = get_problem_type(workflow_type)
            mesido_solver = get_solver_class(workflow_type)

            if "gurobi" in workflow_type_name.lower():
                load_gurobi_license()

            base_folder = Path(__file__).resolve().parent.parent
            esdl_output_profiles_type_str = os.environ.get("ESDL_OUTPUT_PROFILES_TYPE", "POSTGRESQL").upper()
            esdl_output_profiles_type = getattr(ESDLOutputProfilesType, esdl_output_profiles_type_str, None)
            if esdl_output_profiles_type is None:
                logging.warning(
                    "Unknown ESDL_OUTPUT_PROFILES_TYPE '%s', defaulting to POSTGRESQL",
                    esdl_output_profiles_type_str,
                )
                esdl_output_profiles_type = ESDLOutputProfilesType.POSTGRESQL

            db_host = os.environ.get("DB_HOSTNAME")
            db_port = int(os.environ.get("DB_PORT", "5432"))
            db_username = os.environ.get("DB_USERNAME", "")
            db_password = os.environ.get("DB_PASSWORD", "")

            logging.info(
                "Will write result profiles to '%s' database at %s:%s",
                esdl_output_profiles_type_str,
                db_host,
                db_port,
            )

            database_connection = []

            database_connection.append({
                "access_type": DBAccessType.READ_WRITE,
                "host": db_host,
                "port": db_port,
                "username": db_username,
                "password": db_password,
                "ssl": False,
                "verify_ssl": False,
            })

            esdl_messages: list[EsdlMessage] = []

            solution: Any = mesido_func(
                mesido_workflow,
                solver_class=mesido_solver,
                base_folder=base_folder,
                esdl_string=base64.encodebytes(input_esdl.encode("utf-8")),
                esdl_parser=ESDLStringParser,
                esdl_output_profiles_type=esdl_output_profiles_type,
                database_connections=database_connection,
                update_progress_function=_update_flow_progress,
                profile_reader=ESDLProfileReader,
            )
            output_esdl = cast(str, solution.optimized_esdl_string)

            # update name of output ESDL
            input_esh = EnergySystemHandler()
            input_esh.load_from_string(input_esdl)

            new_name = input_esh.energy_system.name + "_"
            new_name += flow_run.name if flow_run and flow_run.name else workflow_type_name

            output_esh = EnergySystemHandler()
            output_esh.load_from_string(output_esdl)
            output_energy_system: EnergySystem = output_esh.energy_system
            output_energy_system.name = new_name

            # TODO get esdl_messages from successful run after mesido update.
            esdl_messages_as_dicts = [message.model_dump(mode="json") for message in esdl_messages]
            success_result = OptimizerFlowResult(
                output_esdl=output_esh.to_string(),
                esdl_messages=esdl_messages_as_dicts,
            )
            write_flow_return_artifact_to_minio(success_result)

            # return only for local runs and testing, not persisted for containerized runs: artifacts are used
            return success_result
        except Exception as e:
            logging.exception("Exception during optimizer flow")

            esdl_messages: list[EsdlMessage] = []
            if isinstance(e, MesidoAssetIssueError):
                esdl_messages = parse_mesido_esdl_messages(e.general_issue, e.message_per_asset_id)
                logging.info(f"ESDL Messages: {esdl_messages}")

            failed_result = OptimizerFlowResult(
                output_esdl=None,
                esdl_messages=[message.model_dump(mode="json") for message in esdl_messages],
            )
            write_flow_return_artifact_to_minio(failed_result)

            return Failed(message=f"Optimizer flow failed: {e}")


def parse_mesido_esdl_messages(general_message: str, object_messages: dict[str, str]) -> list[EsdlMessage]:
    """Convert mesido messages to a list of esdl messages in omotes format.

    Args:
        general_message: General message (not related to a specific ESDL object).
        object_messages: ESDL object messages per object id.

    Returns:
        list[EsdlMessage]: List of EsdlMessage dataclass objects.

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
