import base64
import os
from pathlib import Path

from rtctools.util import run_optimization_problem
from rtctools_heat_network.workflows.grow_workflow import EndScenarioSizingCBC


def run_calculation(input_esdl: str) -> str:
    base_folder = Path(__file__).resolve().parent.parent
    solution: EndScenarioSizingCBC = run_optimization_problem(
        EndScenarioSizingCBC, base_folder=base_folder, esdl_string=input_esdl
    )
    return solution.optimized_esdl_string


if __name__ == "__main__":
    print("Starting")

    input_esdl_file_path = os.environ.get("INPUT_ESDL_FILE_NAME")
    output_esdl_file_path = os.environ.get("OUTPUT_ESDL_FILE_NAME")
    with open(input_esdl_file_path) as open_input_esdl_file:
        input_esdl_string = open_input_esdl_file.read()

    output_esdl = run_calculation(input_esdl_string)
    print("Done with calculation. Writing output")
    encoded_output = base64.b64encode(output_esdl.encode("utf-8"))

    with open(output_esdl_file_path, "w+") as open_output_esdl_file:
        open_output_esdl_file.write(output_esdl)
    print("Done. Shutting down...")
