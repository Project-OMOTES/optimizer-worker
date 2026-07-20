import asyncio
import os
import subprocess

from grow_worker.worker import optimizer_flow
from prefect_util import deploy_flow

deployment_base_name = "omotes-optimizer"

use_local_prefect_code_and_image = os.getenv("PREFECT_USE_LOCAL_CODE_AND_IMAGE", "false").lower() == "true"
optimizer_version = os.getenv("OPTIMIZER_WORKER_VERSION")
if use_local_prefect_code_and_image:
    optimizer_version = "local"
    optimizer_image = f"{deployment_base_name}:{optimizer_version}"
else:
    optimizer_image = f"ghcr.io/project-omotes/{deployment_base_name}:{optimizer_version}"

job_variables = {
    "imagePullPolicy": "Always",
    "env": {
        "PREFECT_LOGGING_EXTRA_LOGGERS": "root",
        "PREFECT_LOGGING_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PREFECT_LOGGING_ROOT_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PREFECT_LOGGING_LOGGERS_HTTPCORE_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PREFECT_LOGGING_LOGGERS_HTTPX_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PREFECT_LOGGING_LOGGERS_WEBSOCKETS_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PREFECT_LOGGING_LOGGERS_ASYNCIO_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "PREFECT_USER_NAME": os.getenv("PREFECT_USER_NAME"),
        "PREFECT_PASSWORD": os.getenv("PREFECT_PASSWORD"),
        "PREFECT_API_URL": os.getenv("PREFECT_SERVER_API_URL"),
        "ESDL_OUTPUT_PROFILES_TYPE": os.getenv("ESDL_OUTPUT_PROFILES_TYPE"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", None),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", None),
        "MINIO_HOST": os.getenv("MINIO_HOST"),
        "MINIO_EXTERNAL_HOST": os.getenv("MINIO_EXTERNAL_HOST"),
        "MINIO_ACCESS_KEY": os.getenv("MINIO_ACCESS_KEY"),
        "MINIO_SECRET": os.getenv("MINIO_SECRET"),
        "PREFECT_MINIO_HOST": os.getenv("PREFECT_MINIO_HOST") or os.getenv("MINIO_HOST"),
        "PREFECT_MINIO_EXTERNAL_HOST": os.getenv("PREFECT_MINIO_EXTERNAL_HOST") or os.getenv("MINIO_EXTERNAL_HOST"),
        "PREFECT_MINIO_ACCESS_KEY": os.getenv("PREFECT_MINIO_ACCESS_KEY") or os.getenv("MINIO_ACCESS_KEY"),
        "PREFECT_MINIO_SECRET": os.getenv("PREFECT_MINIO_SECRET") or os.getenv("MINIO_SECRET"),
        "PREFECT_MINIO_RESULTS_BUCKET": os.getenv("PREFECT_MINIO_RESULTS_BUCKET", "prefect-results"),
        "PREFECT_MINIO_RESULTS_PREFIX": os.getenv("PREFECT_MINIO_RESULTS_PREFIX", "flow-results"),
        "PREFECT_MINIO_RESULTS_BLOCK": os.getenv("PREFECT_MINIO_RESULTS_BLOCK", "minio-result-storage"),
    },
    "pod_watch_timeout_seconds": 24 * 3600,
    "networks": ["omotes"],  # for docker worker
    # "auto_remove": True,  # for docker worker, uncomment for debugging
}


async def main():
    """Deploy training and prediction flows to Prefect."""
    if use_local_prefect_code_and_image:
        # create/update local classification docker image
        cmd_build_classification_image = f"docker build --provenance=false -t {optimizer_image} .."
        subprocess.run(cmd_build_classification_image, shell=True, check=True)
    # When not using local code and image, a ci.tno.nl image is used (created on push to ci.tno.nl repo) with the tag
    #   specified as env var OPTIMIZER_WORKER_IMAGE_TAG.

    await deploy_flow(
        flow_function=optimizer_flow,
        deployment_name=f"{deployment_base_name}:{optimizer_version}",
        image_name=optimizer_image,
        job_variables=job_variables,
    )

    print("Omotes optimizer deployment registered successfully")


if __name__ == "__main__":
    asyncio.run(main())
