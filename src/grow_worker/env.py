try:  # dotenv is not used/installed by all developers
    from dotenv import load_dotenv  # noqa

    load_dotenv()
except ImportError:
    pass

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
    def prefect_api_url() -> str:
        """Return Prefect API URL."""
        return require_env("PREFECT_API_URL")

    @staticmethod
    def prefect_user_name() -> str:
        """Return Prefect user name."""
        return require_env("PREFECT_USER_NAME")

    @staticmethod
    def prefect_password() -> str:
        """Return Prefect password."""
        return require_env("PREFECT_PASSWORD")

    @staticmethod
    def prefect_work_pool_name() -> str:
        """Return Prefect work pool name."""
        return require_env("PREFECT_WORK_POOL_NAME")

    @staticmethod
    def prefect_use_local_code_and_image() -> bool:
        """Return whether local code and image should be used for deployment."""
        return os.getenv("PREFECT_USE_LOCAL_CODE_AND_IMAGE", "false").lower() == "true"

    @staticmethod
    def prefect_classification_image_tag() -> str | None:
        """Return optional Prefect image tag override."""
        return os.getenv("PREFECT_CLASSIFICATION_IMAGE_TAG", None)

    @staticmethod
    def prefect_server_api_url() -> str:
        """Return Prefect server API URL."""
        return require_env("PREFECT_SERVER_API_URL")

    @staticmethod
    def minio_host() -> str:
        """Return MinIO host."""
        return require_env("MINIO_HOST")

    @staticmethod
    def minio_external_host() -> str | None:
        """Return optional external MinIO host."""
        return os.getenv("MINIO_EXTERNAL_HOST", None)

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
