import base64
import os
from pathlib import Path

from rtctools.util import run_optimization_problem
from warmingup_mpc.run_scenario_sizing_v2 import HeatProblemCBC


def run_calculation(input_esdl: str) -> str:
    base_folder = Path(__file__).resolve().parent.parent
    solution: HeatProblemCBC = run_optimization_problem(HeatProblemCBC, base_folder=base_folder, esdl_string=input_esdl)
    return solution.optimized_esdl_string


if __name__ == "__main__":
    print("Starting")

    input_esdl_file_path = os.environ.get("INPUT_ESDL_FILE_NAME")
    output_esdl_file_path = os.environ.get("OUTPUT_ESDL_FILE_NAME")
    with open(input_esdl_file_path) as open_input_esdl_file:
        input_esdl_string = open_input_esdl_file.read()

    print("Received input esdl file:")
    print(input_esdl_string)

    output_esdl = run_calculation(input_esdl_string)
    print("Done with calculation")
    print("Output esdl: ", output_esdl)
    encoded_output = base64.b64encode(output_esdl.encode("utf-8"))
    print("Writing to output file: ", output_esdl)

    with open(output_esdl_file_path, "w+") as open_output_esdl_file:
        open_output_esdl_file.write(output_esdl)
    print("Done")
