import asyncio
import json
import logging
import os
import re
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast
from uuid import UUID

import numpy as np

from env import EnvSettings

# !!! must be set before importing any prefect libs !!!
os.environ["PREFECT_API_URL"] = EnvSettings.prefect_api_url()
os.environ["PREFECT_API_AUTH_STRING"] = "admin:password"
os.environ["PREFECT_LOGGING_LEVEL"] = EnvSettings.log_level()
# os.environ["PREFECT_LOGGING_ROOT_LEVEL"] = EnvSettings.log_level()

# !!! All prefect imports need to be done here to ensure PREFECT_API_URL has been set before !!!
# ruff: noqa: E402 Module level import not at top of file
from prefect import (
    State,  # needed to avoid a pydantic error - very strange...
    flow,  # noqa: F401, used in flow definitions
    task,
)
from prefect.artifacts import (
    create_link_artifact,
    create_markdown_artifact,
    create_progress_artifact,
    create_table_artifact,
    update_progress_artifact,
)
from prefect.blocks.system import Secret
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    DeploymentFilter,
    DeploymentFilterName,
    FlowRunFilter,
    FlowRunFilterTags,
)
from prefect.client.schemas.objects import Artifact
from prefect.client.schemas.sorting import DeploymentSort, FlowRunSort
from prefect.context import get_run_context
from prefect.filesystems import RemoteFileSystem
from prefect.runtime import flow_run
from prefect.states import (
    Failed,  # noqa: F401, used in flow definitions
    StateType,  # noqa: F401, used in flow definitions
)
from pydantic import BaseModel


def _build_minio_result_storage() -> RemoteFileSystem | None:
    """Create MinIO-backed Prefect result storage block when env vars are available."""
    minio_host = os.getenv("PREFECT_MINIO_HOST") or os.getenv("MINIO_HOST")
    access_key = os.getenv("PREFECT_MINIO_ACCESS_KEY") or os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("PREFECT_MINIO_SECRET") or os.getenv("MINIO_SECRET")
    if not minio_host or not access_key or not secret_key:
        return None

    bucket = os.getenv("PREFECT_MINIO_RESULTS_BUCKET", "prefect-results")
    prefix = os.getenv("PREFECT_MINIO_RESULTS_PREFIX", "flow-results")
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
    """Return True if running inside a Prefect flow context, False otherwise."""
    try:
        get_run_context()
        return True
    except Exception:
        return False


class LocalFuture:
    """Wrapper around either a Prefect Future or a raw value."""

    def __init__(self, inner: Any, in_flow: bool):
        self._inner = inner
        self._in_flow = in_flow

    def results(self, **kwargs) -> Any:
        """Return the underlying result.

        Supports Prefect's Future.result(**kwargs) options like:
          - timeout
          - raise_on_failure
        """
        if self._in_flow:
            return self._inner.result(**kwargs)
        else:
            # Outside flow → synchronous value
            if kwargs:
                # Optional: raise if user tries unsupported args
                raise ValueError(f"LocalFuture outside Prefect flow does not support kwargs: {kwargs}")
            return self._inner


class LocalTask:
    """Wrap a function to behave like a Prefect Task inside a flow, but execute as a normal function outside of a
    Prefect flow context.

    :param fn: The original function to wrap.
    :param task_kwargs: Keyword arguments to pass to Prefect's @task decorator.
    """

    def __init__(self, fn: Callable[..., Any], task_kwargs: dict[str, Any] = None):
        """Initialize the LocalTask.

        :param fn: The function to wrap.
        :param task_kwargs: Additional keyword arguments for Prefect's task decorator.
        """
        self._fn: Callable[..., Any] = fn
        self.task_kwargs: dict[str, Any] = task_kwargs or {}
        self._prefect_task = None
        wraps(fn)(self)

    def _get_prefect_task(self):
        """Return a Prefect Task instance."""
        if self._prefect_task is None:
            self._prefect_task = task(**self.task_kwargs)(self._fn)
        return self._prefect_task

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the wrapped function. If inside a Prefect flow, dynamically wrap it as a Prefect Task. Otherwise,
        execute normally.

        :param args: Positional arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        :return: The result of calling the underlying function or Prefect Task.
        """
        if in_prefect_flow_context():
            t = self._get_prefect_task()
            return t(*args, **kwargs)
        else:
            return self._fn(*args, **kwargs)

    def submit(self, *args: Any, **kwargs: Any) -> LocalFuture:
        if in_prefect_flow_context():
            fut = self._get_prefect_task().submit(*args, **kwargs)
            return LocalFuture(fut, in_flow=True)
        else:
            value = self._fn(*args, **kwargs)
            return LocalFuture(value, in_flow=False)

    @property
    def fn(self) -> Callable[..., Any]:
        """Expose the underlying function for testing or direct calls.

        :return: The wrapped function.
        """
        return self._fn

    @fn.setter
    def fn(self, value: Callable[..., Any]):
        """Set the underlying function.

        :param value: The function to set as the underlying function.
        """
        self._fn = value


def prefect_task(cache_results: bool = False, **task_kwargs: Any) -> Callable[[Callable[..., Any]], LocalTask]:
    """Decorator to make a function behave as a Prefect Task when called inside a flow, but as a regular function
    outside a flow.

    :param cache_results: If True, enable result persistence with MinIO.
    :param task_kwargs: Additional keyword arguments for Prefect's @task decorator.
    :return: A decorator that wraps the target function in a LocalTask.
    """
    kwargs: dict[str, Any] = task_kwargs.copy()

    if cache_results:
        kwargs.update(
            persist_result=True,
            cache_expiration=timedelta(days=10),
        )

    def decorator(fn: Callable[..., Any]) -> LocalTask:
        """Wrap the function in a LocalTask.

        :param fn: The function to wrap.
        :return: A LocalTask instance wrapping the function.
        """
        if "name" not in kwargs:
            kwargs["name"] = fn.__name__.removesuffix("_task")
        return LocalTask(fn, kwargs)

    return decorator


def load_gurobi_license() -> None:
    target_dir = "/app/gurobi"
    target_file = os.path.join(target_dir, "gurobi.lic")
    os.makedirs(target_dir, exist_ok=True)

    # get license content from Prefect Secret block
    secret_block = Secret.load("gurobi-wls-secret")
    license_content = secret_block.get()

    with open(target_file, "w") as f:
        f.write(license_content)

    logging.info(f"Successfully generated {target_file}")


def handle_flow_state_update(flow_object, flow_run_object, state: State):
    """Unified handler for flow start and state changes.

    Args:
        flow_object: The flow object (filled by flow hook function)
        flow_run_object: The FlowRun object (filled by flow hook function)
        state: State of the run (filled by flow hook function)
        flow_type: type of the flow

    """
    pass
    if not in_prefect_flow_context() or not flow_run.parameters.get("write_results_to_postgres"):
        return

    # postgres_interface = PostgresInterface()
    # postgres_interface.update_job_status(flow_type, str(flow_run_object.id), state.type.value)


# def update_job_progress(
#     flow_type: FlowType,
#     flow_run_id: str,
#     progress_fraction: float,
#     progress_message: str,
# ):
#     """Update the progress of a job (training or prediction) in postgres.

#     :param flow_type: job type.
#     :param flow_run_id: run id of the prefect run.
#     :param progress_fraction: progress fraction (0.0-1.0).
#     :param progress_message: progress message.
#     """
#     if not in_prefect_flow_context() or not flow_run.parameters.get("write_results_to_postgres"):
#         return

#     postgres_interface = PostgresInterface()
#     postgres_interface.update_job_status(flow_type, flow_run_id, StateType.RUNNING.value)
#     postgres_interface.update_job_progress_fraction_message(
#         flow_type, flow_run_id, progress_fraction, progress_message
#     )


def get_run_unique_run_name():
    """Returns the run name, hyphen and the first 8 chars of the run id."""
    return f"{flow_run.get_name()}-{flow_run.id[:8]}"


def _sanitize_for_minio(value: str) -> str:
    """Sanitize a value for Prefect artifact keys: lowercase letters, numbers, dashes."""
    sanitized = re.sub(r"[^a-z0-9-]+", "-", value.lower().strip())
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    return sanitized or "field"


def _create_minio_presigned_url(object_path: str, expires_seconds: int = 7 * 24 * 60 * 60) -> str | None:
    """Create a presigned GET URL for an object written via minio_block."""
    try:
        resolved_path = minio_block._resolve_path(object_path)
        return cast(str, minio_block.filesystem.sign(resolved_path, expiration=expires_seconds))
    except Exception:
        logging.exception("Failed to create presigned URL for MinIO object")
        return None


def _extract_minio_object_path(description: str | None) -> str | None:
    """Extract a MinIO object path from an artifact description."""
    if not description:
        return None

    match = re.search(r"MinIO object:\\s*(.+)", description)
    return match.group(1).strip() if match else None


def _get_required_file_extension(result: BaseModel, field_name: str) -> str:
    """Return the configured file extension for a BaseModel field."""
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
    """Persist flow return fields to MinIO and publish Prefect links to those objects."""
    if not in_prefect_flow_context():
        return None

    run_folder_path = _sanitize_for_minio(f"{flow_run.get_name()}-{flow_run.id[:8]}")

    for field_name, field_value in flow_result:
        if field_value is None:
            continue

        artifact_key = _sanitize_for_minio(f"{field_name}-{flow_run.id[:8]}")
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
            link_text=f"Open {field_name} in MinIO",
            key=artifact_key,
            description=f"MinIO object: {field_object_path}",
        )

    return run_folder_path


PREFECT_ARTIFACT_BUCKET = "prefect-artifacts"

P = ParamSpec("P")  # Captures the parameters of the original function
R = TypeVar("R")  # Captures the return type of the original function


def run_sync(async_func: Callable[P, R]) -> Callable[P, R]:
    """Decorator to run an async function in a synchronous context.

    Usage:

    @run_sync
    async def async_func(x: int) -> str:
        ...

    result: str = async_func(42)
    """

    @wraps(async_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(async_func(*args, **kwargs))
        except RuntimeError:
            return asyncio.run(async_func(*args, **kwargs))

    return wrapper


@run_sync
async def create_prefect_metadata_artifact_if_in_flow_context(key: str, data: dict, description: str | None = None):
    if not in_prefect_flow_context():
        return

    async with get_client() as client:
        artifact = Artifact(
            key=key,
            type="metadata",
            data=data,
            flow_run_id=flow_run.id,
            description=description,
        )
        await client.create_artifact(artifact)


def create_prefect_artifact_if_in_flow_context(
    key: str,
    description: str = "",
    table_data: list | None = None,
    markdown: str | None = None,
    dict_data: dict | None = None,
    # figure: plt.Figure | None = None,
):
    """Create a Prefect artifact, if running in Prefect context.

    Create a table, markdown or file Prefect artifact. If not running in Prefect context, nothing happens.

    :param key: Name of the artifact, must only contain lowercase letters, numbers, and dashes
    :param description: Description of the artifact.
    :param table_data: table data consisting of a list of dicts.
    :param markdown: markdown.
    :param dict_data: dictionary which will be converted to markdown.
    :param figure: matplotlib figure.
    """
    if not in_prefect_flow_context():
        return

    def np_encoder(obj):
        if isinstance(obj, np.generic):
            return obj.item()
        return None

    if table_data:
        create_table_artifact(
            key=key,
            table=table_data,
            description=description,
        )
    elif markdown or dict_data:
        if dict_data:
            markdown = "```json\n" + json.dumps(dict_data, indent=2, default=np_encoder) + "\n```"
        create_markdown_artifact(
            key=key,
            markdown=markdown,
            description=description,
        )
    # elif figure:
    #     image_url = save_image_to_minio(
    #         object_path=f"{get_run_unique_run_name()}/{key}",
    #         figure=figure,
    #         bucket_name=PREFECT_ARTIFACT_BUCKET,
    #     )
    #     create_image_artifact(
    #         key=key,
    #         image_url=image_url,
    #         description=description,
    #     )


def create_flow_progress_artifact(
    key: str,
    start_progress: float = 0.0,
    start_description: str | None = None,
) -> UUID | None:
    """Create a flow progress artifact and return its id, or None when unavailable."""
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
    """Create a progress artifact and return a safe updater function."""
    progress_key = f"progress-{flow_run.id[:8]}"
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
    """Convert a Kubernetes-style memory quantity into bytes for Docker."""
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
    """
    job_vars = dict(base_vars or {})

    if memory_limit:
        job_vars["memory_limit"] = memory_limit
        job_vars["memory_request"] = memory_limit
        job_vars["mem_limit"] = _memory_quantity_to_bytes(memory_limit)

    return job_vars or None


async def trigger_flow_run(
    run_name: str,
    deployment_base_name: str,
    deployment_version: str,
    parameters: dict | None = None,
    memory_limit: str | None = None,
    job_variables: dict | None = None,
    type: str | None = None,
    username: str | None = None,
    company: str | None = None,
):
    deployment_name = f"{deployment_base_name}:{deployment_version}"
    async with get_client() as client:
        # Fetch deployments with the given name
        deployments = await client.read_deployments(
            deployment_filter=DeploymentFilter(name=DeploymentFilterName(any_=[deployment_name])),
            sort=DeploymentSort.CREATED_DESC,
        )

        if not deployments:
            print(f"❌ Deployment '{deployment_name}' not found for run '{run_name}'.")
            return

        run_tags: list[str] = []
        run_tags.append(f"version:{deployment_version}")
        if type:
            run_tags.append(f"type:{type}")
        if username:
            run_tags.append(f"user:{username}")
        if company:
            run_tags.append(f"company:{company}")

        deployment_id = deployments[0].id
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id=deployment_id,
            parameters=parameters or {},
            name=run_name,
            tags=run_tags or None,
            job_variables=build_universal_job_vars(memory_limit=memory_limit, base_vars=job_variables),
        )
        print(f"✅ Created flow run '{run_name}' from '{deployment_name}' → Run ID: {flow_run.id}; tags={run_tags}")


async def list_flow_runs_by_tags(
    username: str | None = None,
    company: str | None = None,
    limit: int = 20,
):
    """List recent flow runs filtered by run tags.

    Tags follow the trigger_run_by_name convention:
      - user:<username>
      - company:<company>
    """
    required_tags: list[str] = []
    if username:
        required_tags.append(f"user:{username}")
    if company:
        required_tags.append(f"company:{company}")

    async with get_client() as client:
        flow_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(tags=FlowRunFilterTags(all_=required_tags) if required_tags else None),
            sort=FlowRunSort.START_TIME_DESC,
            limit=limit,
        )

    for run in flow_runs:
        print(
            f"{run.id} | name={run.name} | state={run.state_name} | "
            f"start={run.start_time} | tags={list(run.tags or [])}"
        )

    return flow_runs


async def deploy_flow(flow_function: Any, deployment_name: str, image_name: str, job_variables: dict):
    """Deploy prefect flow with variables.
    Will raise an error when trying to overwrite an existing semantic version (x.x.x).
    Note: the 'flow' object cannot be annotated properly since @flow is dynamically typed.

    :param flow_function: Flow object.
    :param deployment_name: Name of the deployment.
    :param image_name: Name of the Docker image.
    :param job_variables: Job variables.
    """
    version_name = image_name.rsplit(":", 1)[-1]

    async with get_client() as client:
        deployments = await client.read_deployments(
            deployment_filter=DeploymentFilter(name=DeploymentFilterName(any_=[deployment_name])),
            sort=DeploymentSort.CREATED_DESC,
        )
        if deployments and is_semantic_version(version_name):
            raise RuntimeError(f"Prefect flow cannot be overwritten for semantic version '{deployment_name}'")

    await flow_function.deploy(
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
    """Return True if the version string follows Semantic Versioning '1.2.3'."""
    return bool(SEMVER_REGEX.match(version_name))
