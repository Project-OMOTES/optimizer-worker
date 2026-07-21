import asyncio
import subprocess

from grow_worker.env import EnvSettings
from grow_worker.prefect_util import deploy_flow
from prefect_flow import optimizer_flow

deployment_base_name = "omotes-optimizer"

use_local_prefect_code_and_image = EnvSettings.prefect_use_local_code_and_image()
optimizer_version = EnvSettings.optimizer_worker_version()
if use_local_prefect_code_and_image:
    optimizer_version = "local2"
    optimizer_image = f"{deployment_base_name}:{optimizer_version}"
else:
    optimizer_image = f"ghcr.io/project-omotes/{deployment_base_name}:{optimizer_version}"

job_variables = {
    "imagePullPolicy": "Always",
    "env": {
        "PREFECT_LOGGING_EXTRA_LOGGERS": "root",
        "PREFECT_LOGGING_LEVEL": EnvSettings.log_level(),
        "PREFECT_LOGGING_ROOT_LEVEL": EnvSettings.log_level(),
        "LOG_LEVEL": EnvSettings.log_level(),
        "PREFECT_USER_NAME": EnvSettings.prefect_user_name(),
        "PREFECT_PASSWORD": EnvSettings.prefect_password(),
        "PREFECT_API_URL": EnvSettings.prefect_server_api_url(),
        "ESDL_OUTPUT_PROFILES_TYPE": EnvSettings.esdl_output_profiles_type(),
        "DB_HOSTNAME": EnvSettings.db_hostname(),
        "DB_PORT": EnvSettings.db_port(),
        "DB_USERNAME": EnvSettings.db_username(),
        "DB_PASSWORD": EnvSettings.db_password(),
        "MINIO_HOST": EnvSettings.minio_host(),
        "MINIO_EXTERNAL_HOST": EnvSettings.minio_external_host(),
        "MINIO_ACCESS_KEY": EnvSettings.minio_access_key(),
        "MINIO_SECRET": EnvSettings.minio_secret(),
        "PREFECT_MINIO_HOST": EnvSettings.minio_host(),
        "PREFECT_MINIO_EXTERNAL_HOST": EnvSettings.minio_external_host(),
        "PREFECT_MINIO_ACCESS_KEY": EnvSettings.minio_access_key(),
        "PREFECT_MINIO_SECRET": EnvSettings.minio_secret(),
    },
    "pod_watch_timeout_seconds": 24 * 3600,
    "networks": ["omotes"],  # for docker worker
    "auto_remove": True,  # for docker worker, uncomment for debugging
}


async def main() -> None:
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
