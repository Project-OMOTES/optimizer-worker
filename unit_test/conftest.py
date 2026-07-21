import os

_TEST_ENV_DEFAULTS = {
    "LOG_LEVEL": "INFO",
    "ESDL_OUTPUT_PROFILES_TYPE": "POSTGRESQL",
    "DB_HOSTNAME": "localhost",
    "DB_PORT": "5432",
    "DB_USERNAME": "test-user",
    "DB_PASSWORD": "test-password",
    "PREFECT_API_URL": "http://localhost:4200/api",
    "PREFECT_USER_NAME": "test-user",
    "PREFECT_PASSWORD": "test-password",
    "PREFECT_WORK_POOL_NAME": "test-pool",
    "PREFECT_SERVER_API_URL": "http://localhost:4200/api",
    "MINIO_HOST": "localhost:9000",
    "MINIO_ACCESS_KEY": "test-access-key",
    "MINIO_SECRET": "test-secret-key",
}

for key, value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(key, value)
