import asyncio
from collections.abc import Mapping
from importlib import import_module, reload
from os import environ
from unittest import TestCase
from unittest.mock import AsyncMock, patch


class TestDeployFlowJobVariables(TestCase):
    """Tests for the job_variables structure built at module level."""

    def _get_job_variables(self) -> Mapping[str, object]:
        required_env = {
            "LOG_LEVEL": "INFO",
            "ESDL_OUTPUT_PROFILES_TYPE": "POSTGRESQL",
            "DB_HOSTNAME": "db",
            "DB_PORT": "5432",
            "DB_USERNAME": "user",
            "DB_PASSWORD": "pass",
            "PREFECT_API_AUTH_STRING": "token",
            "PREFECT_API_URL_FOR_WORKER": "http://prefect:4200/api",
            "MINIO_HOST": "minio",
            "MINIO_EXTERNAL_URL": "http://localhost:9000",
            "MINIO_PORT": "9000",
            "MINIO_ACCESS_KEY": "access",
            "MINIO_SECRET": "secret",
            "PREFECT_WORK_POOL_NAME": "default",
            "PREFECT_FLOW_MAX_CONCURRENT_RUNS": "1",
        }
        with patch.dict(environ, required_env, clear=False):
            m = import_module("omotes_optimizer_worker.prefect_deploy_flow")
            m = reload(m)

        return m.job_variables

    def test_job_variables_auto_remove_is_set(self) -> None:
        """auto_remove should be True, not left over missing from testing."""
        self.assertTrue(self._get_job_variables()["auto_remove"])


class TestDeployFlowMain(TestCase):
    """Tests for the deployments registered by main()."""

    def test_main_deploys_each_deployment_on_its_limited_work_queue(self) -> None:
        """Both deployments are registered on their own work queue with the configured concurrency limit."""
        env = {
            "LOG_LEVEL": "INFO",
            "ESDL_OUTPUT_PROFILES_TYPE": "POSTGRESQL",
            "DB_HOSTNAME": "db",
            "DB_PORT": "5432",
            "DB_USERNAME": "user",
            "DB_PASSWORD": "pass",
            "PREFECT_API_AUTH_STRING": "token",
            "PREFECT_API_URL_FOR_WORKER": "http://prefect:4200/api",
            "MINIO_HOST": "minio",
            "MINIO_EXTERNAL_URL": "http://localhost:9000",
            "MINIO_PORT": "9000",
            "MINIO_ACCESS_KEY": "access",
            "MINIO_SECRET": "secret",
            "PREFECT_WORK_POOL_NAME": "pool",
            "PREFECT_FLOW_MAX_CONCURRENT_RUNS": "4",
            "PREFECT_GUROBI_MAX_CONCURRENT_RUNS": "1",
            "PREFECT_USE_LOCAL_CODE_AND_IMAGE": "false",
            "OPTIMIZER_WORKER_VERSION": "1.2.3",
        }
        with patch.dict(environ, env, clear=False):
            m = reload(import_module("omotes_optimizer_worker.prefect_deploy_flow"))
            with patch.object(m, "deploy_flow", new=AsyncMock()) as deploy_mock:
                asyncio.run(m.main())

        self.assertEqual(
            [
                (c.kwargs["deployment_name"], c.kwargs["work_queue_name"], c.kwargs["max_concurrent_runs"])
                for c in deploy_mock.await_args_list
            ],
            [
                ("omotes-optimizer:1.2.3", "omotes-optimizer", 4),
                ("omotes-optimizer-gurobi:1.2.3", "omotes-optimizer-gurobi", 1),
            ],
        )
