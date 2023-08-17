import uuid
from dataclasses import dataclass
import logging
import os
import subprocess
from typing import Optional

from dotenv import load_dotenv
from nwnsdk import NwnClient, JobStatus


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


class OptimizationWorker:
    nwn_client: NwnClient

    def __init__(self):
        self.nwn_client = NwnClient(host=..., user_loglevel=...)

    def work(self):
        while True:
            job_id = self.get_next_job_id()
            input_esdl_string = self.nwn_client.db_client.retrieve_input_esdl(job_id)
            self.nwn_client.db_client.set_job_running(job_id)
            calculation_result = self.run_optimizer_calculation(job_id, input_esdl_string)
            self.store_calculation_result(calculation_result)

    def get_next_job_id(self) -> uuid.uuid4:
        # Do RabbitMQ queue wait
        ...

    def store_calculation_result(self, calculation_result: CalculationResult) -> None:
        new_status = JobStatus.FINISHED if calculation_result.exit_code == 0 else JobStatus.ERROR

        self.nwn_client.db_client.store_job_result(job_id=calculation_result.job_id,
                                                   new_logs=calculation_result.logs,
                                                   new_status=new_status,
                                                   output_esdl=calculation_result.output_esdl)


    @staticmethod
    def run_optimizer_calculation(job_id: uuid.uuid4, esdl_string: str) -> CalculationResult:
        with open(f'/app/input_esdl_files/{job_id}.esdl') as open_esdl_input_file:
            open_esdl_input_file.write(esdl_string)

        with TempEnvVar('INPUT_ESDL_FILE_NAME', f'/app/input_esdl_files/{job_id}.esdl'):
            with TempEnvVar('OUTPUT_ESDL_FILE_NAME', f'/app/output_esdl_files/{job_id}.esdl'):
                process_result = subprocess.run(['python3', '-m', 'optimizer_worker.run_optimizer'],
                                                stderr=subprocess.STDOUT,
                                                text=True)

        if process_result.returncode == 0:
            with open(f'/app/output_esdl_files/{job_id}.esdl') as open_esdl_output_file:
                output_esdl = open_esdl_output_file.read()
        else:
            output_esdl = None

        return CalculationResult(job_id=job_id,
                                 logs=process_result.stdout,
                                 exit_code=process_result.returncode,
                                 input_esdl=esdl_string,
                                 output_esdl=output_esdl)


def main():
    OptimizationWorker().work()


if __name__ == "__main__":
    main()
