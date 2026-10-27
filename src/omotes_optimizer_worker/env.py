import os


def require_env(name: str) -> str:
    """Return a required environment variable.

    Returns:
        str: The configured environment variable value.

    Raises:
        RuntimeError: If the environment variable is missing.

    """
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: '{name}'")
    return value


class EnvSettings:
    """Helper class to access environment variables."""

    @staticmethod
    def log_level() -> str:
        """Return configured log level in upper-case."""
        return require_env("LOG_LEVEL").upper()

    @staticmethod
    def esdl_output_profiles_type() -> str:
        """Return ESDL output profiles type."""
        return require_env("ESDL_OUTPUT_PROFILES_TYPE")

    @staticmethod
    def db_hostname() -> str:
        """Return database host name."""
        return require_env("DB_HOSTNAME")

    @staticmethod
    def db_port() -> str:
        """Return database port."""
        return require_env("DB_PORT")

    @staticmethod
    def db_username() -> str:
        """Return database user name."""
        return require_env("DB_USERNAME")

    @staticmethod
    def db_password() -> str:
        """Return database password."""
        return require_env("DB_PASSWORD")

    @staticmethod
    def pg_db_timeseries() -> str:
        """Return PostgreSQL timeseries database name."""
        return os.getenv("PG_DB_TIMESERIES", "omotes_timeseries")

    @staticmethod
    def prefect_api_url_for_worker() -> str:
        """Return Prefect API URL to be used inside worker."""
        return require_env("PREFECT_API_URL_FOR_WORKER")

    @staticmethod
    def orchestrator_api_url() -> str:
        """Return the optional orchestrator API URL used inside workers."""
        return os.getenv("ORCHESTRATOR_API_URL", "")

    @staticmethod
    def prefect_work_pool_name() -> str:
        """Return Prefect work pool name."""
        return require_env("PREFECT_WORK_POOL_NAME")

    @staticmethod
    def prefect_use_local_code_and_image() -> bool:
        """Return whether local code and image should be used for deployment."""
        return os.getenv("PREFECT_USE_LOCAL_CODE_AND_IMAGE", "false").lower() == "true"

    @staticmethod
    def prefect_use_local_sdk_and_mesido() -> bool:
        """Return whether local code for sdk and mesido should be used for deployment."""
        return os.getenv("PREFECT_USE_LOCAL_SDK_AND_MESIDO", "false").lower() == "true"

    @staticmethod
    def prefect_api_auth_string() -> str:
        """Return Prefect auth string."""
        return require_env("PREFECT_API_AUTH_STRING")

    @staticmethod
    def prefect_flow_max_concurrent_runs() -> int:
        """Return the maximum number of concurrent Prefect flow runs."""
        return int(require_env("PREFECT_FLOW_MAX_CONCURRENT_RUNS"))

    @staticmethod
    def prefect_gurobi_max_concurrent_runs() -> int:
        """Return the maximum number of concurrent Gurobi flow runs (number of Gurobi licenses)."""
        return int(os.getenv("PREFECT_GUROBI_MAX_CONCURRENT_RUNS", "1"))

    @staticmethod
    def prefect_flow_timeout_seconds() -> int:
        """Return Prefect flow timeout in seconds."""
        timeout_seconds = os.getenv(
            "PREFECT_FLOW_TIMEOUT_SECONDS",
            str(24 * 3600 * 2),  # default to 2 days
        )
        return int(timeout_seconds)

    @staticmethod
    def s3_host() -> str:
        """Return S3 host."""
        return require_env("S3_HOST")

    @staticmethod
    def s3_port() -> str:
        """Return S3 port."""
        return require_env("S3_PORT")

    @staticmethod
    def s3_external_url() -> str:
        """Return external S3 URL."""
        return require_env("S3_EXTERNAL_URL")

    @staticmethod
    def s3_access_key() -> str:
        """Return S3 admin user (access key)."""
        return require_env("S3_ACCESS_KEY")

    @staticmethod
    def s3_secret_key() -> str:
        """Return S3 admin password (secret key)."""
        return require_env("S3_SECRET_KEY")

    @staticmethod
    def optimizer_worker_version() -> str | None:
        """Return optional optimizer worker version."""
        return os.getenv("OPTIMIZER_WORKER_VERSION", None)

    @staticmethod
    def docker_worker_networks() -> list[str]:
        """Return Docker networks the docker-type worker attaches flow-run containers to."""
        networks = os.getenv(
            "PREFECT_DOCKER_WORKER_NETWORKS",
            os.getenv("PREFECT_DOCKER_WORKER_NETWORK", "omotes"),
        )
        return [network.strip() for network in networks.split(",") if network.strip()]
