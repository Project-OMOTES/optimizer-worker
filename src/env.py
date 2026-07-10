try:  # dotenv is not used/installed by all developers
    from dotenv import load_dotenv  # noqa

    load_dotenv()
except ImportError:
    pass

import os


def require_env(name: str) -> str:
    """Raise an error if the environment variable is not set."""
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: '{name}'")
    return value


class EnvSettings:
    """Helper class to access environment variables."""

    @staticmethod
    def log_level() -> str:
        return require_env("LOG_LEVEL").upper()

    @staticmethod
    def postgres_host() -> str:
        return require_env("POSTGRES_HOST")

    @staticmethod
    def postgres_port() -> str:
        return require_env("POSTGRES_PORT")

    @staticmethod
    def postgres_db() -> str:
        return require_env("POSTGRES_DB")

    @staticmethod
    def postgres_user() -> str:
        return require_env("POSTGRES_USER")

    @staticmethod
    def postgres_password() -> str:
        return require_env("POSTGRES_PASSWORD")

    @staticmethod
    def minio_host() -> str:
        return require_env("MINIO_HOST")

    @staticmethod
    def minio_external_host() -> str | None:
        return os.getenv("MINIO_EXTERNAL_HOST", None)

    @staticmethod
    def minio_access_key() -> str:
        return require_env("MINIO_ACCESS_KEY")

    @staticmethod
    def minio_secret() -> str:
        return require_env("MINIO_SECRET")

    @staticmethod
    def prefect_classification_image_tag() -> str | None:
        return os.getenv("PREFECT_CLASSIFICATION_IMAGE_TAG", None)

    @staticmethod
    def prefect_api_url() -> str:
        return require_env("PREFECT_API_URL")

    @staticmethod
    def prefect_user_name() -> str:
        return os.getenv("PREFECT_USER_NAME", "")

    @staticmethod
    def prefect_password() -> str:
        return os.getenv("PREFECT_PASSWORD", "")

    @staticmethod
    def prefect_work_pool_name() -> str:
        return require_env("PREFECT_WORK_POOL_NAME")

    @staticmethod
    def prefect_server_api_url() -> str:
        return require_env("PREFECT_SERVER_API_URL")

    @staticmethod
    def prefect_postgres_host() -> str:
        return require_env("PREFECT_POSTGRES_HOST")

    @staticmethod
    def prefect_postgres_port() -> str:
        return require_env("PREFECT_POSTGRES_PORT")

    @staticmethod
    def prefect_postgres_db() -> str:
        return require_env("PREFECT_POSTGRES_DB")

    @staticmethod
    def prefect_postgres_user() -> str:
        return require_env("PREFECT_POSTGRES_USER")

    @staticmethod
    def prefect_postgres_password() -> str:
        return require_env("PREFECT_POSTGRES_PASSWORD")

    @staticmethod
    def prefect_minio_host() -> str:
        return require_env("PREFECT_MINIO_HOST")

    @staticmethod
    def prefect_minio_external_host() -> str:
        return require_env("PREFECT_MINIO_EXTERNAL_HOST")

    @staticmethod
    def prefect_minio_access_key() -> str:
        return require_env("PREFECT_MINIO_ACCESS_KEY")

    @staticmethod
    def prefect_minio_secret() -> str:
        return require_env("PREFECT_MINIO_SECRET")

    @staticmethod
    def prefect_use_local_code_and_image() -> bool:
        return os.getenv("PREFECT_USE_LOCAL_CODE_AND_IMAGE", "false").lower() == "true"

    @staticmethod
    def output_sharepoint_path() -> str | None:
        return os.getenv("OUTPUT_SHAREPOINT_PATH")

    @staticmethod
    def eda_sharepoint_path() -> str | None:
        return os.getenv("EDA_SHAREPOINT_PATH")
