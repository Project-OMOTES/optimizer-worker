import json
import logging
import os
import re
from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from grow_worker.env import EnvSettings

# !!! must be set before importing any prefect libs !!!
os.environ["PREFECT_API_URL"] = EnvSettings.prefect_api_url()
os.environ["PREFECT_API_AUTH_STRING"] = f"{EnvSettings.prefect_user_name()}:{EnvSettings.prefect_password()}"
os.environ["PREFECT_LOGGING_LEVEL"] = EnvSettings.log_level()

# !!! All prefect imports need to be done here to ensure PREFECT_API_URL has been set before !!!
# ruff: noqa: E402 Module level import not at top of file
from prefect import (
    flow,  # noqa: F401, used in flow definitions
)
from prefect.artifacts import (
    create_link_artifact,
    create_progress_artifact,
    update_progress_artifact,
)
from prefect.blocks.system import Secret
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    DeploymentFilter,
    DeploymentFilterName,
)
from prefect.client.schemas.sorting import DeploymentSort
from prefect.context import (
    FlowRunContext,  # noqa: F401, used in flow definitions
    get_run_context,
)
from prefect.filesystems import RemoteFileSystem
from prefect.runtime import flow_run
from prefect.states import (
    Failed,  # noqa: F401, used in flow definitions
    State,  # noqa: F401, used in flow definitions
    StateType,  # noqa: F401, used in flow definitions
)
from pydantic import BaseModel


def _build_minio_result_storage() -> RemoteFileSystem:
    """Create MinIO-backed Prefect result storage block when env vars are available.

    Returns:
        RemoteFileSystem: Configured Prefect result storage block.

    """
    minio_host = EnvSettings.minio_host()
    access_key = EnvSettings.minio_access_key()
    secret_key = EnvSettings.minio_secret()

    bucket = "prefect-results"
    prefix = "flow-results"
    endpoint_url = f"http://{minio_host}"

    return RemoteFileSystem(
        basepath=f"s3://{bucket}/{prefix}",
        settings={
            "key": access_key,
            "secret": secret_key,
            "client_kwargs": {"endpoint_url": endpoint_url},
        },
    )


minio_block = _build_minio_result_storage()

# Silence noisy third-party loggers that Prefect enables at DEBUG level internally
import logging as _logging

_log_level = getattr(_logging, EnvSettings.log_level(), _logging.WARNING)
for _noisy in (
    "httpcore",
    "httpx",
    "websockets",
    "asyncio",
    "hpack",
    "botocore",
    "aiobotocore",
    "s3fs",
    "fsspec",
    "urllib3",
):
    _logging.getLogger(_noisy).setLevel(_log_level)


def in_prefect_flow_context() -> bool:
    """Check whether execution is inside a Prefect flow context.

    Returns:
        bool: True when called in a Prefect flow context, otherwise False.

    """
    try:
        get_run_context()
        return True
    except Exception:
        return False


def get_flow_run_id_first_part() -> str:
    """Get first part of flow run id.

    For local runs a default value is returned.

    Returns:
        str: First 8 characters of the flow run id, or a default value for local runs.

    """
    return flow_run.id[:8] if flow_run and flow_run.id else "12345678"


def load_gurobi_license() -> None:
    """Load Gurobi license content from Prefect Secret and write it to disk."""
    target_dir = "/app/gurobi"
    target_file = os.path.join(target_dir, "gurobi.lic")
    os.makedirs(target_dir, exist_ok=True)

    # get license content from Prefect Secret block
    secret_block = cast(Secret[Any], Secret.load("gurobi-wls-secret"))
    license_content = secret_block.get()

    with open(target_file, "w") as f:
        f.write(license_content)

    logging.info(f"Successfully generated {target_file}")


def _sanitize_for_minio(value: str) -> str:
    """Sanitize a value for Prefect artifact keys.

    Returns:
        str: Lower-case alpha-numeric and dash-only string.

    """
    sanitized = re.sub(r"[^a-z0-9-]+", "-", value.lower().strip())
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    return sanitized or "field"


def _create_minio_presigned_url(object_path: str, expires_seconds: int = 7 * 24 * 60 * 60) -> str | None:
    """Create a presigned GET URL for an object written via minio_block.

    Returns:
        str | None: The generated URL or None when URL generation fails.

    """
    try:
        resolved_path = minio_block._resolve_path(object_path)
        return cast(str, minio_block.filesystem.sign(resolved_path, expiration=expires_seconds))
    except Exception:
        logging.exception("Failed to create presigned URL for MinIO object")
        return None


def _get_required_file_extension(result: BaseModel, field_name: str) -> str:
    """Return the configured file extension for a BaseModel field.

    Returns:
        str: Lower-cased file extension for the field.

    Raises:
        ValueError: If the field has no valid file_extension entry.

    """
    field_info = type(result).model_fields.get(field_name)
    extension = None
    if field_info is not None and isinstance(field_info.json_schema_extra, dict):
        extension = field_info.json_schema_extra.get("file_extension")

    if not isinstance(extension, str) or not extension.startswith("."):
        raise ValueError(
            f"Field '{field_name}' in model '{type(result).__name__}' must define "
            "json_schema_extra={'file_extension': '.ext'}"
        )

    return extension.lower()


def write_flow_return_artifact_to_minio(
    flow_result: BaseModel,
) -> str | None:
    """Persist flow return fields to MinIO and publish Prefect links to those objects.

    Returns:
        str | None: Run folder path in MinIO, or None if not in flow context.

    """
    if not in_prefect_flow_context():
        return None

    run_folder_path = _sanitize_for_minio(f"{flow_run.get_name()}-{get_flow_run_id_first_part()}")

    for field_name, field_value in flow_result:
        if field_value is None:
            continue

        artifact_key = _sanitize_for_minio(f"{field_name}-{get_flow_run_id_first_part()}")
        field_extension = _get_required_file_extension(flow_result, field_name)
        field_object_path = f"{run_folder_path}/{artifact_key}{field_extension}"

        field_bytes = (
            field_value.encode("utf-8")
            if isinstance(field_value, str)
            else json.dumps(field_value, indent=2, default=str).encode("utf-8")
        )

        try:
            minio_block.write_path(path=field_object_path, content=field_bytes)
        except Exception:
            logging.exception("Failed to persist flow return field '%s' to MinIO", field_name)
            continue

        presigned_url = _create_minio_presigned_url(field_object_path)
        if presigned_url is None:
            continue

        create_link_artifact(
            link=presigned_url,
            link_text=f"Download '{field_name}' from MinIO",
            key=artifact_key,
            description=f"MinIO object: {field_object_path}",
        )

    return run_folder_path


def create_flow_progress_artifact(
    key: str,
    start_progress: float = 0.0,
    start_description: str | None = None,
) -> UUID | None:
    """Create a flow progress artifact and return its id.

    Returns:
        UUID | None: Created artifact id, or None if unavailable.

    """
    if not in_prefect_flow_context():
        return None

    try:
        return cast(
            UUID,
            create_progress_artifact(
                key=key,
                progress=start_progress,
                description=start_description,
            ),
        )
    except Exception:
        return None


def create_flow_progress_updater(
    start_progress_fraction: float = 0.0,
    start_description: str | None = None,
) -> Callable[[float, str | None], None]:
    """Create a progress artifact and return a safe updater function.

    Returns:
        Callable[[float, str | None], None]: Function that updates progress artifacts.

    """
    progress_key = f"progress-{get_flow_run_id_first_part()}"
    artifact_id = create_flow_progress_artifact(
        key=progress_key,
        start_progress=start_progress_fraction * 100.0,
        start_description=start_description,
    )

    def _update(progress_fraction: float, description: str | None = None) -> None:
        if artifact_id is None:
            logging.error(f"Error logging progress update for run '{flow_run.get_name()}': artifact creation failed")
        else:
            update_progress_artifact(
                artifact_id=artifact_id, progress=progress_fraction * 100.0, description=description
            )

    return _update


def _memory_quantity_to_bytes(memory_limit: str) -> int:
    """Convert a Kubernetes-style memory quantity into bytes for Docker.

    Returns:
        int: Memory quantity in bytes.

    Raises:
        ValueError: If the input memory quantity has an unsupported format.

    """
    normalized = memory_limit.strip()
    match = re.fullmatch(r"(?i)(\d+(?:\.\d+)?)([kmgtpe]i?|)", normalized)
    if not match:
        raise ValueError(f"Unsupported memory quantity: {memory_limit!r}")

    value = float(match.group(1))
    suffix = match.group(2).lower()
    binary_factors = {
        "": 1,
        "k": 10**3,
        "m": 10**6,
        "g": 10**9,
        "t": 10**12,
        "p": 10**15,
        "e": 10**18,
        "ki": 1024,
        "mi": 1024**2,
        "gi": 1024**3,
        "ti": 1024**4,
        "pi": 1024**5,
        "ei": 1024**6,
    }
    return int(value * binary_factors[suffix])


def build_universal_job_vars(memory_limit: str | None = None, base_vars: dict | None = None) -> dict | None:
    """Build a job_variables payload for Kubernetes-style memory input.

    Kubernetes workers use memory_request and memory_limit directly.
    Docker workers use mem_limit, so we convert the Kubernetes quantity to bytes in Python.

    Returns:
        dict | None: Job variables suitable for worker deployment or None if unchanged.

    """
    job_vars = dict(base_vars or {})

    if memory_limit:
        job_vars["memory_limit"] = memory_limit
        job_vars["memory_request"] = memory_limit
        job_vars["mem_limit"] = _memory_quantity_to_bytes(memory_limit)

    return job_vars or None


async def deploy_flow(
    flow_function: object,
    deployment_name: str,
    image_name: str,
    job_variables: dict,
) -> None:
    """Deploy prefect flow with variables.

    Will raise an error when trying to overwrite an existing semantic version (x.x.x).
    Note: the 'flow' object cannot be annotated properly since @flow is dynamically typed.

    Args:
        flow_function: Flow object exposing a deploy method.
        deployment_name: Name of the deployment.
        image_name: Name of the Docker image.
        job_variables: Job variables.

    Raises:
        RuntimeError: If a semantic-versioned deployment already exists.

    """
    version_name = image_name.rsplit(":", 1)[-1]

    async with get_client() as client:
        deployments = await client.read_deployments(
            deployment_filter=DeploymentFilter(name=DeploymentFilterName(any_=[deployment_name])),
            sort=DeploymentSort.CREATED_DESC,
        )
        if deployments and is_semantic_version(version_name):
            raise RuntimeError(f"Prefect flow cannot be overwritten for semantic version '{deployment_name}'")

    deployable_flow = cast(Any, flow_function)
    await deployable_flow.deploy(
        name=deployment_name,
        work_pool_name=EnvSettings.prefect_work_pool_name(),
        image=image_name,
        build=False,
        job_variables=job_variables,
    )


# Support full semantic versions like 1.2.3-beta+exp.sha.5114f85
SEMVER_REGEX = re.compile(
    r"""
    ^
    (0|[1-9]\d*)\.                # major
    (0|[1-9]\d*)\.                # minor
    (0|[1-9]\d*)                  # patch
    (?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?  # prerelease (optional)
    (?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))? # build metadata (optional)
    $
    """,
    re.VERBOSE,
)


def is_semantic_version(version_name: str) -> bool:
    """Return whether a version string follows Semantic Versioning.

    Returns:
        bool: True for semantic version strings, otherwise False.

    """
    return bool(SEMVER_REGEX.match(version_name))
