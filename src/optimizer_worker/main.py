import signal
import threading
from dataclasses import dataclass
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional
import uuid

import pika as pika
from dotenv import load_dotenv
from nwnsdk import NwnClient, JobStatus, PostgresConfig, RabbitmqConfig, Queue


LOGGER = logging.getLogger("optimizer_worker")

load_dotenv()  # take environment variables from .env


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
    job_id: uuid.uuid4
    exit_code: int
    logs: str
    input_esdl: str
    output_esdl: Optional[str]


class PerformCalculation(threading.Thread):
    nwn_client: NwnClient
    input_files_dir: Path
    output_files_dir: Path
    job_id: uuid.UUID
    channel: pika.adapters.blocking_connection.BlockingChannel
    method: pika.spec.Basic.Deliver

    def __init__(
        self,
        nwn_client: NwnClient,
        input_files_dir: Path,
        output_files_dir: Path,
        job_id: uuid.UUID,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
    ):
        super().__init__()

        self.nwn_client = nwn_client
        self.input_files_dir = input_files_dir
        self.output_files_dir = output_files_dir
        self.job_id = job_id
        self.channel = channel
        self.method = method

    def run(self) -> None:
        LOGGER.info("Starting calculation for job %s", self.job_id)
        input_esdl_string = self.nwn_client.get_job_input_esdl(self.job_id)
        self.nwn_client.set_job_running(self.job_id)
        calculation_result = self.run_optimizer_calculation(
            self.input_files_dir, self.output_files_dir, self.job_id, input_esdl_string
        )
        self.store_calculation_result(calculation_result)
        if self.channel.is_open:
            self.channel.connection.add_callback_threadsafe(lambda: self.channel.basic_ack(self.method.delivery_tag))
        else:
            LOGGER.warning("Rabbitmq channel was closed so could not ack that job %s was performed.", self.job_id)

    def store_calculation_result(self, calculation_result: CalculationResult) -> None:
        new_status = JobStatus.FINISHED if calculation_result.exit_code == 0 else JobStatus.ERROR

        self.nwn_client.store_job_result(
            job_id=calculation_result.job_id,
            new_logs=calculation_result.logs,
            new_status=new_status,
            output_esdl=calculation_result.output_esdl,
        )

    @staticmethod
    def run_optimizer_calculation(
        input_files_dir: Path, output_files_dir: Path, job_id: uuid.uuid4, esdl_string: str
    ) -> CalculationResult:
        input_file = input_files_dir / f"{job_id}.esdl"
        output_file = output_files_dir / f"{job_id}.esdl"

        with open(input_file, "w+") as open_esdl_input_file:
            open_esdl_input_file.write(esdl_string)

        with TempEnvVar("INPUT_ESDL_FILE_NAME", str(input_file)):
            with TempEnvVar("OUTPUT_ESDL_FILE_NAME", str(output_file)):
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


class OptimizationWorker:
    nwn_client: NwnClient
    input_files_dir: Path
    output_files_dir: Path
    running_calculation: Optional[PerformCalculation]

    def __init__(self, input_files_dir: Path, output_files_dir: Path):
        self.input_files_dir = input_files_dir
        self.output_files_dir = output_files_dir
        postgres_config = PostgresConfig(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "6432"),
            database_name=os.environ["POSTGRES_DATABASE_NAME"],
            user_name=os.environ["POSTGRES_ROOT_USER"],
            password=os.environ["POSTGRES_ROOT_PASSWORD"],
        )
        rabbitmq_config = RabbitmqConfig(
            host=os.environ["RABBITMQ_HOST"],
            port=int(os.environ["RABBITMQ_PORT"]),
            exchange_name=os.environ["RABBITMQ_EXCHANGE"],
            user_name=os.environ["RABBITMQ_ROOT_USER"],
            password=os.environ["RABBITMQ_ROOT_PASSWORD"],
            hipe_compile=os.environ.get("RABBITMQ_HIPE_COMPILE", "1"),
        )

        self.nwn_client = NwnClient(postgres_config=postgres_config, rabbitmq_config=rabbitmq_config)
        self.running_calculation = None

    def on_start_workflow_message(
        self,
        ch: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ):
        message = json.loads(body.decode("utf-8"))
        job_id = uuid.UUID(message.get("job_id"))

        if job_id is None:
            LOGGER.error("Received a message which did not contain a job id. Message: %s", message)
            ch.connection.add_callback_threadsafe(lambda: ch.basic_ack(method.delivery_tag))
        else:
            LOGGER.info("Received message to work on job %s", job_id)
            self.running_calculation = PerformCalculation(
                self.nwn_client, self.input_files_dir, self.output_files_dir, job_id, ch, method
            )
            self.running_calculation.start()

    def work(self):
        signal.signal(signal.SIGQUIT, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.nwn_client.connect()
        self.nwn_client.set_callbacks({Queue.StartWorkflowOptimizer: self.on_start_workflow_message})
        self.nwn_client.join()

    def signal_handler(self, signal, frame):
        LOGGER.info("Received signal %s. Stopping..", signal)
        self.stop()

    def stop(self):
        self.nwn_client.stop()


def main():
    OptimizationWorker(Path(os.environ["INPUT_FILES_DIR"]), Path(os.environ["OUTPUT_FILES_DIR"])).work()


if __name__ == "__main__":
    main()
