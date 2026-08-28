import asyncio
import shutil
from pathlib import Path

from omotes_sdk.prefect_util import deploy_flow

from omotes_optimizer_worker.env import EnvSettings
from omotes_optimizer_worker.prefect_flow import optimizer_flow

deployment_base_name = "omotes-optimizer"


async def _build_docker_image(command: list[str], cwd: Path | None = None) -> None:
    process = await asyncio.create_subprocess_exec(*command, cwd=cwd)
    return_code = await process.wait()
    if return_code != 0:
        raise RuntimeError(f"Docker build failed with exit code {return_code}")


prefect_use_local_code_and_image = EnvSettings.prefect_use_local_code_and_image()
optimizer_version = EnvSettings.optimizer_worker_version()
if prefect_use_local_code_and_image:
    optimizer_version = "local"
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
        "PREFECT_API_AUTH_STRING": EnvSettings.prefect_api_auth_string(),
        "PREFECT_API_URL": EnvSettings.prefect_api_url_for_worker(),
        "ESDL_OUTPUT_PROFILES_TYPE": EnvSettings.esdl_output_profiles_type(),
        "DB_HOSTNAME": EnvSettings.db_hostname(),
        "DB_PORT": EnvSettings.db_port(),
        "DB_USERNAME": EnvSettings.db_username(),
        "DB_PASSWORD": EnvSettings.db_password(),
        "MINIO_HOST": EnvSettings.minio_host(),
        "MINIO_PORT": EnvSettings.minio_port(),
        "MINIO_EXTERNAL_URL": EnvSettings.minio_external_url(),
        "MINIO_ACCESS_KEY": EnvSettings.minio_access_key(),
        "MINIO_SECRET": EnvSettings.minio_secret(),
        "PREFECT_FLOW_TIMEOUT_SECONDS": str(EnvSettings.prefect_flow_timeout_seconds()),
    },
    "networks": [EnvSettings.docker_worker_network()],  # for docker worker
    "auto_remove": True,  # for docker worker, uncomment for debugging
}


async def main() -> None:
    """Deploy training and prediction flows to Prefect.

    Raises:
        FileNotFoundError: If Docker is unavailable for a local image build.
    """
    if prefect_use_local_code_and_image:
        # create/update local docker image
        docker_executable = shutil.which("docker")
        if docker_executable is None:
            raise FileNotFoundError("Docker executable not found on PATH")

        if EnvSettings.prefect_use_local_sdk_and_mesido():
            repo_root = Path(__file__).resolve().parents[2]
            monorepo_root = repo_root.parent
            await _build_docker_image(
                [
                    docker_executable,
                    "build",
                    "-f",
                    "optimizer-worker/dev.Dockerfile",
                    "--provenance=false",
                    "-t",
                    optimizer_image,
                    ".",
                ],
                cwd=monorepo_root,
            )
        else:
            await _build_docker_image(
                [
                    docker_executable,
                    "build",
                    "--provenance=false",
                    "-t",
                    optimizer_image,
                    "..",
                ],
            )
    # When not using local code and image, a publised image is used with tag OPTIMIZER_WORKER_IMAGE_TAG.

    await deploy_flow(
        flow_function=optimizer_flow,
        deployment_name=f"{deployment_base_name}:{optimizer_version}",
        image_name=optimizer_image,
        job_variables=job_variables,
        prefect_work_pool_name=EnvSettings.prefect_work_pool_name(),
        max_concurrent_runs=EnvSettings.prefect_flow_max_concurrent_runs(),
    )

    print("Omotes optimizer deployment registered successfully")


if __name__ == "__main__":
    asyncio.run(main())
