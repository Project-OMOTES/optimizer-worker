from collections.abc import Mapping
from importlib import import_module, reload
from os import environ
from unittest import TestCase
from unittest.mock import patch


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
            "MINIO_EXTERNAL_URL": "localhost:9000",
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
