from os import environ
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from esdl.esdl_handler import EnergySystemHandler
from mesido.esdl.esdl_mixin import ESDLOutputProfilesType
from prefect.states import State

from omotes_optimizer_worker.prefect_flow import (
    OptimizerFlowResult,
    optimizer_flow,
    publish_optimizer_timeseries_cleanup_resource,
)

MINIO_TEST_ENV = {
    "MINIO_HOST": "minio",
    "MINIO_EXTERNAL_URL": "http://localhost:9000",
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
    assert write_artifact.call_args.args[5] == "http://localhost:9000"
    assert isinstance(feedback_result, OptimizerFlowResult)
    assert feedback_result.output_esdl is None
    assert feedback_result.esdl_messages
    assert all(message["technical_message"] for message in feedback_result.esdl_messages)
    assert all(message["severity"] == "ERROR" for message in feedback_result.esdl_messages)


def test_optimizer_flow_configures_influxdb_output() -> None:
    """Pass InfluxDB output settings to Mesido and publish its generated database."""
    fixture_path = Path(__file__).parent / "data" / "esdl" / "Delft_T.esdl"
    input_esdl = fixture_path.read_text()
    output_esh = EnergySystemHandler()
    output_esh.load_from_string(input_esdl)
    mesido_arguments: dict = {}

    def run_mesido(*args: object, **kwargs: object) -> SimpleNamespace:
        mesido_arguments.update(kwargs)
        return SimpleNamespace(optimized_esdl_string=input_esdl)

    influx_env = MINIO_TEST_ENV | {
        "ESDL_OUTPUT_PROFILES_TYPE": "INFLUXDB",
        "DB_HOSTNAME": "omotes_influxdb",
        "DB_PORT": "8096",
    }
    with (
        patch.dict(environ, influx_env, clear=False),
        patch("omotes_optimizer_worker.prefect_flow.get_problem_function", return_value=run_mesido),
        patch("omotes_optimizer_worker.prefect_flow.get_problem_type"),
        patch("omotes_optimizer_worker.prefect_flow.get_solver_class"),
        patch("omotes_optimizer_worker.prefect_flow.write_flow_return_artifact_to_minio"),
        patch("omotes_optimizer_worker.prefect_flow.publish_optimizer_timeseries_cleanup_resource") as publish_resource,
    ):
        result = optimizer_flow.fn(
            input_esdl=input_esdl,
            workflow_config={},
            workflow_type_name="grow_optimizer_no_heat_losses",
        )

    assert isinstance(result, OptimizerFlowResult)
    assert mesido_arguments["esdl_output_profiles_type"] == ESDLOutputProfilesType.INFLUXDB
    assert mesido_arguments["database_connections"] == [
        {
            "access_type": "read_write",
            "host": "omotes_influxdb",
            "port": 8096,
            "username": "user",
            "password": "password",
            "ssl": False,
            "verify_ssl": False,
        }
    ]
    publish_resource.assert_called_once_with(
        db_host="omotes_influxdb",
        db_port=8096,
        output_energy_system_id=output_esh.energy_system.id,
        output_profiles_type=ESDLOutputProfilesType.INFLUXDB,
        pg_database=None,
    )


def test_publish_optimizer_database_cleanup_resource_for_postgresql() -> None:
    """Publish deletable PostgreSQL resource coordinates without credentials."""
    with (
        patch("omotes_optimizer_worker.prefect_flow.publish_job_cleanup_resource") as publish_resource,
    ):
        publish_optimizer_timeseries_cleanup_resource(
            db_host="postgres",
            db_port=5432,
            output_energy_system_id="output-esdl-id",
            output_profiles_type=ESDLOutputProfilesType.POSTGRESQL,
            pg_database="omotes_timeseries",
        )

    assert publish_resource.call_args.args[0].model_dump(mode="json", by_alias=True) == {
        "type": "postgresql",
        "host": "postgres",
        "port": 5432,
        "database": "omotes_timeseries",
        "schema": "output-esdl-id",
    }
    assert "username" not in str(publish_resource.call_args)
    assert "password" not in str(publish_resource.call_args)


def test_publish_optimizer_database_cleanup_resource_for_influxdb() -> None:
    """Use the output ESDL ID as the Mesido-created InfluxDB database name."""
    with (
        patch("omotes_optimizer_worker.prefect_flow.publish_job_cleanup_resource") as publish_resource,
    ):
        publish_optimizer_timeseries_cleanup_resource(
            db_host="influxdb",
            db_port=8086,
            output_energy_system_id="output-esdl-id",
            output_profiles_type=ESDLOutputProfilesType.INFLUXDB,
        )

    assert publish_resource.call_args.args[0].model_dump(mode="json", by_alias=True) == {
        "type": "influxdb",
        "host": "influxdb",
        "port": 8086,
        "database": "output-esdl-id",
        "schema": None,
    }
