import base64
import os
from pathlib import Path
from typing import Union, Type

from rtctools.util import run_optimization_problem
from rtctools_heat_network.workflows.grow_workflow import EndScenarioSizingHIGHS
from rtctools_heat_network.workflows.simulator_workflow import NetworkSimulatorHIGHSWeeklyTimeStep
from nwnsdk import WorkFlowType

GROWProblem = Union[Type[EndScenarioSizingHIGHS], Type[NetworkSimulatorHIGHSWeeklyTimeStep]]


def get_problem_type(
    workflow_type: WorkFlowType,
) -> GROWProblem:
    if workflow_type == WorkFlowType.GROW_OPTIMIZER:
        return EndScenarioSizingHIGHS
    elif workflow_type == WorkFlowType.GROW_SIMULATOR:
        return NetworkSimulatorHIGHSWeeklyTimeStep
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {workflow_type}")


def run_calculation(input_esdl: str, grow_problem: GROWProblem) -> str:
    base_folder = Path(__file__).resolve().parent.parent
    write_result_db_profiles = "INFLUXDB_HOST" in os.environ
    influxdb_host = os.environ.get("INFLUXDB_HOST", "localhost")
    influxdb_port = int(os.environ.get("INFLUXDB_PORT", "8086"))

    print(f"Will write result profiles to influx: {write_result_db_profiles}. At {influxdb_host}:{influxdb_port}")

    solution: GROWProblem = run_optimization_problem(
        grow_problem,
        base_folder=base_folder,
        esdl_string=input_esdl,
        write_result_db_profiles=write_result_db_profiles,
        influxdb_host=influxdb_host,
        influxdb_port=influxdb_port,
        influxdb_username=os.environ.get("INFLUXDB_USERNAME"),
        influxdb_password=os.environ.get("INFLUXDB_PASSWORD"),
        influxdb_ssl=False,
        influxdb_verify_ssl=False,
    )
    return solution.optimized_esdl_string


if __name__ == "__main__":
    print("Starting")

    input_esdl_file_path = os.environ.get("INPUT_ESDL_FILE_NAME")
    output_esdl_file_path = os.environ.get("OUTPUT_ESDL_FILE_NAME")
    workflow_type = os.environ.get("WORKFLOW_TYPE")
    with open(input_esdl_file_path) as open_input_esdl_file:
        input_esdl_string = open_input_esdl_file.read()

    output_esdl = run_calculation(input_esdl_string, get_problem_type(WorkFlowType(workflow_type)))
    print("Done with calculation. Writing output")
    encoded_output = base64.b64encode(output_esdl.encode("utf-8"))

    with open(output_esdl_file_path, "w+") as open_output_esdl_file:
        open_output_esdl_file.write(output_esdl)
    print("Done. Shutting down...")
