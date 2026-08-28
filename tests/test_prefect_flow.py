from os import environ
from pathlib import Path
from unittest.mock import patch

from prefect.states import State

from omotes_optimizer_worker.prefect_flow import OptimizerFlowResult, optimizer_flow

MINIO_TEST_ENV = {
    "MINIO_HOST": "minio",
    "MINIO_HOST_EXTERNAL": "localhost",
    "MINIO_PORT": "9000",
    "MINIO_ACCESS_KEY": "access",
    "MINIO_SECRET": "secret",
    "DB_HOSTNAME": "db",
    "DB_PORT": "5432",
    "DB_USERNAME": "user",
    "DB_PASSWORD": "password",
    "ESDL_OUTPUT_PROFILES_TYPE": "NO_DB_WRITE_FOR_TEST",
}


def test_optimizer_flow_runs_delft_esdl() -> None:
    """Run the optimizer flow with the same fixture as the local runner."""
    # Arrange
    fixture_path = Path(__file__).parent / "data" / "esdl" / "Delft_T.esdl"
    input_esdl = fixture_path.read_text()
    # Act
    with (
        patch.dict(environ, MINIO_TEST_ENV, clear=False),
        patch("omotes_optimizer_worker.prefect_flow.write_flow_return_artifact_to_minio"),
    ):
        result = optimizer_flow.fn(
            input_esdl=input_esdl,
            workflow_config={},
            workflow_type_name="grow_optimizer_no_heat_losses",
        )

    # Assert
    assert isinstance(result, OptimizerFlowResult)
    assert result.output_esdl is not None


def test_optimizer_flow_returns_delft_feedback_messages() -> None:
    """Return feedback messages when the Delft ESDL cannot be optimized."""
    # Arrange
    fixture_path = Path(__file__).parent / "data" / "esdl" / "Delft_T_feedback.esdl"
    input_esdl = fixture_path.read_text()

    # Act
    with (
        patch.dict(environ, MINIO_TEST_ENV, clear=False),
        patch("omotes_optimizer_worker.prefect_flow.write_flow_return_artifact_to_minio") as write_artifact,
    ):
        result = optimizer_flow.fn(
            input_esdl=input_esdl,
            workflow_config={},
            workflow_type_name="grow_optimizer_no_heat_losses",
        )

    # Assert
    assert isinstance(result, State)
    assert result.is_failed()
    feedback_result = write_artifact.call_args.args[0]
    assert write_artifact.call_args.args[5] == "localhost"
    assert isinstance(feedback_result, OptimizerFlowResult)
    assert feedback_result.output_esdl is None
    assert feedback_result.esdl_messages
    assert all(message["technical_message"] for message in feedback_result.esdl_messages)
    assert all(message["severity"] == "ERROR" for message in feedback_result.esdl_messages)
