import jsonpickle
import os
import logging
from typing import Optional
from uuid import uuid4
from pathlib import Path
from celery import Celery
from dataclasses import dataclass
import subprocess
from nwnsdk import WorkFlowType

LOGGER = logging.getLogger("optimizer_worker")

app = Celery(
    "omotes",
    broker="amqp://user:bitnami@rabbitmq",
    backend="rpc://user:bitnami@rabbitmq",
    broker_connection_retry_on_startup=True,
)


@app.task(name="optimizer-task", bind=True)
def optimize(self, job_id: uuid4, esdl_string: str):
    LOGGER.info("optimizer worker started")
    return jsonpickle.encode(
        run_rtc_calculation(
            job_id,
            esdl_string,
            WorkFlowType.GROW_OPTIMIZER,
        )
    )


@app.task(name="simulator-task", bind=True)
def simulate(self, job_id: uuid4, esdl_string: str):
    LOGGER.info("simulation worker started")
    return jsonpickle.encode(
        run_rtc_calculation(
            job_id,
            esdl_string,
            WorkFlowType.GROW_SIMULATOR,
        )
    )


@dataclass
class TempEnvVar:
    name: str
    value: str

    def __enter__(self):
        self.old_value = os.environ.get(self.name)
        os.environ[self.name] = self.value

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_value is not None:
            os.environ[self.name] = self.old_value


@dataclass
class CalculationResult:
    job_id: uuid4
    exit_code: int
    logs: str
    input_esdl: str
    output_esdl: Optional[str]


def run_rtc_calculation(job_id: uuid4, esdl_string: str, workflow_type: WorkFlowType) -> CalculationResult:
    input_file = Path(os.environ["INPUT_FILES_DIR"]) / f"{job_id}.esdl"
    output_file = Path(os.environ["OUTPUT_FILES_DIR"]) / f"{job_id}.esdl"

    with open(input_file, "w+") as open_esdl_input_file:
        open_esdl_input_file.write(esdl_string)

    with TempEnvVar("INPUT_ESDL_FILE_NAME", str(input_file)), TempEnvVar(
        "OUTPUT_ESDL_FILE_NAME", str(output_file)
    ), TempEnvVar("WORKFLOW_TYPE", workflow_type.value):
        LOGGER.info("Starting optimization for %s  in subprocess", job_id)
        process_result = subprocess.run(
            ["python3", "-m", "optimization_runner.run_optimizer"],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            text=True,
        )

    if process_result.returncode == 0:
        with open(output_file) as open_esdl_output_file:
            output_esdl = open_esdl_output_file.read()
    else:
        output_esdl = None

    LOGGER.info("Completed job %s with exit_code %s", job_id, process_result.returncode)

    return CalculationResult(
        job_id=job_id,
        logs=process_result.stdout,
        exit_code=process_result.returncode,
        input_esdl=esdl_string,
        output_esdl=output_esdl,
    )
