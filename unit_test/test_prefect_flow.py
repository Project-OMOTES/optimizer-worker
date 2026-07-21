from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prefect.states import State

from prefect_flow import OptimizerFlowResult, optimizer_flow
from worker_types import GrowTaskType


class TestPrefectFlow(TestCase):
    """Tests for the Prefect optimizer flow wrapper."""

    @patch("prefect_flow.write_flow_return_artifact_to_minio")
    @patch("prefect_flow.create_flow_progress_updater")
    @patch("prefect_flow.StdCaptureToLogSession")
    @patch("prefect_flow.EnergySystemHandler")
    @patch("prefect_flow.get_solver_class")
    @patch("prefect_flow.get_problem_type")
    @patch("prefect_flow.get_problem_function")
    def test_optimizer_flow_success_writes_result_artifact(
        self,
        mock_get_problem_function: MagicMock,
        mock_get_problem_type: MagicMock,
        mock_get_solver_class: MagicMock,
        mock_energy_system_handler: MagicMock,
        mock_capture_to_log_session: MagicMock,
        mock_create_flow_progress_updater: MagicMock,
        mock_write_artifact: MagicMock,
    ) -> None:
        """Verify successful optimizer execution writes a result artifact."""
        expected_output_esdl = "<EnergySystem />"
        mesido_function = MagicMock(return_value=SimpleNamespace(optimized_esdl_string=expected_output_esdl))

        mock_get_problem_function.return_value = mesido_function
        mock_get_problem_type.return_value = object()
        mock_get_solver_class.return_value = object()
        mock_create_flow_progress_updater.return_value = MagicMock()
        mock_capture_to_log_session.return_value.__enter__.return_value = None
        mock_capture_to_log_session.return_value.__exit__.return_value = False
        input_esh = MagicMock()
        input_esh.energy_system = SimpleNamespace(name="input-esdl")
        output_esh = MagicMock()
        output_esh.energy_system = SimpleNamespace(name="output-esdl")
        output_esh.to_string.return_value = expected_output_esdl
        mock_energy_system_handler.side_effect = [input_esh, output_esh]

        result = optimizer_flow.fn(
            input_esdl="<esdl />",
            workflow_config={},
            workflow_type_name=GrowTaskType.GROW_OPTIMIZER_DEFAULT.value,
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, OptimizerFlowResult)
        if not isinstance(result, OptimizerFlowResult):
            self.fail("Expected OptimizerFlowResult on success path")
        self.assertEqual(expected_output_esdl, result.output_esdl)
        mock_write_artifact.assert_called_once()

        written_result = mock_write_artifact.call_args.args[0]
        self.assertEqual(expected_output_esdl, written_result.output_esdl)
        self.assertEqual([], written_result.esdl_messages)

        self.assertTrue(mesido_function.called)
        mesido_call_kwargs = mesido_function.call_args.kwargs
        self.assertIn("database_connections", mesido_call_kwargs)
        self.assertEqual(1, len(mesido_call_kwargs["database_connections"]))

    @patch("prefect_flow.write_flow_return_artifact_to_minio")
    @patch("prefect_flow.create_flow_progress_updater")
    @patch("prefect_flow.StdCaptureToLogSession")
    @patch("prefect_flow.get_solver_class")
    @patch("prefect_flow.get_problem_type")
    @patch("prefect_flow.get_problem_function")
    def test_optimizer_flow_failure_returns_failed_state_and_writes_failed_artifact(
        self,
        mock_get_problem_function: MagicMock,
        mock_get_problem_type: MagicMock,
        mock_get_solver_class: MagicMock,
        mock_capture_to_log_session: MagicMock,
        mock_create_flow_progress_updater: MagicMock,
        mock_write_artifact: MagicMock,
    ) -> None:
        """Verify unexpected exceptions return Failed state and write failed artifact."""
        mesido_function = MagicMock(side_effect=RuntimeError("boom"))

        mock_get_problem_function.return_value = mesido_function
        mock_get_problem_type.return_value = object()
        mock_get_solver_class.return_value = object()
        mock_create_flow_progress_updater.return_value = MagicMock()
        mock_capture_to_log_session.return_value.__enter__.return_value = None
        mock_capture_to_log_session.return_value.__exit__.return_value = False

        result = optimizer_flow.fn(
            input_esdl="<esdl />",
            workflow_config={},
            workflow_type_name=GrowTaskType.GROW_OPTIMIZER_DEFAULT.value,
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, State)
        if not isinstance(result, State):
            self.fail("Expected Prefect State on failure path")
        self.assertTrue(result.is_failed())
        self.assertIn("Optimizer flow failed", str(result.message))

        mock_write_artifact.assert_called_once()
        written_result = mock_write_artifact.call_args.args[0]
        self.assertIsNone(written_result.output_esdl)
        self.assertEqual([], written_result.esdl_messages)

    @patch("prefect_flow.write_flow_return_artifact_to_minio")
    @patch("prefect_flow.load_gurobi_license")
    @patch("prefect_flow.create_flow_progress_updater")
    @patch("prefect_flow.StdCaptureToLogSession")
    @patch("prefect_flow.EnergySystemHandler")
    @patch("prefect_flow.get_solver_class")
    @patch("prefect_flow.get_problem_type")
    @patch("prefect_flow.get_problem_function")
    def test_optimizer_flow_gurobi_workflow_loads_license(
        self,
        mock_get_problem_function: MagicMock,
        mock_get_problem_type: MagicMock,
        mock_get_solver_class: MagicMock,
        mock_energy_system_handler: MagicMock,
        mock_capture_to_log_session: MagicMock,
        mock_create_flow_progress_updater: MagicMock,
        mock_load_gurobi_license: MagicMock,
        mock_write_artifact: MagicMock,
    ) -> None:
        """Verify workflows with gurobi in the name trigger license loading."""
        expected_output_esdl = "<EnergySystem />"
        mesido_function = MagicMock(return_value=SimpleNamespace(optimized_esdl_string=expected_output_esdl))

        mock_get_problem_function.return_value = mesido_function
        mock_get_problem_type.return_value = object()
        mock_get_solver_class.return_value = object()
        mock_create_flow_progress_updater.return_value = MagicMock()
        mock_capture_to_log_session.return_value.__enter__.return_value = None
        mock_capture_to_log_session.return_value.__exit__.return_value = False
        input_esh = MagicMock()
        input_esh.energy_system = SimpleNamespace(name="input-esdl")
        output_esh = MagicMock()
        output_esh.energy_system = SimpleNamespace(name="output-esdl")
        output_esh.to_string.return_value = expected_output_esdl
        mock_energy_system_handler.side_effect = [input_esh, output_esh]

        result = optimizer_flow.fn(
            input_esdl="<esdl />",
            workflow_config={},
            workflow_type_name=GrowTaskType.GROW_OPTIMIZER_DEFAULT_GUROBI.value,
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, OptimizerFlowResult)
        if not isinstance(result, OptimizerFlowResult):
            self.fail("Expected OptimizerFlowResult on success path")
        self.assertEqual(expected_output_esdl, result.output_esdl)
        mock_load_gurobi_license.assert_called_once()
        mock_write_artifact.assert_called_once()
