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
    def prefect_api_url_for_worker() -> str:
        """Return Prefect API URL to be used inside worker."""
        return require_env("PREFECT_API_URL_FOR_WORKER")

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
    def prefect_flow_timeout_seconds() -> int:
        """Return Prefect flow timeout in seconds."""
        timeout_seconds = os.getenv(
            "PREFECT_FLOW_TIMEOUT_SECONDS",
            str(24 * 3600 * 2),  # default to 2 days
        )
        return int(timeout_seconds)

    @staticmethod
    def minio_host() -> str:
        """Return MinIO host."""
        return require_env("MINIO_HOST")

    @staticmethod
    def minio_port() -> str:
        """Return MinIO port."""
        return require_env("MINIO_PORT")

    @staticmethod
    def minio_external_url() -> str:
        """Return external MinIO host."""
        return require_env("MINIO_EXTERNAL_URL")

    @staticmethod
    def minio_access_key() -> str:
        """Return MinIO access key."""
        return require_env("MINIO_ACCESS_KEY")

    @staticmethod
    def minio_secret() -> str:
        """Return MinIO secret key."""
        return require_env("MINIO_SECRET")

    @staticmethod
    def optimizer_worker_version() -> str | None:
        """Return optional optimizer worker version."""
        return os.getenv("OPTIMIZER_WORKER_VERSION", None)

    @staticmethod
    def docker_worker_network() -> str:
        """Return the Docker network the docker-type worker attaches flow-run containers to."""
        return os.getenv("PREFECT_DOCKER_WORKER_NETWORK", "omotes")
