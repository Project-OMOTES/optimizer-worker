import os
from pathlib import Path

from rtctools.util import run_optimization_problem
from warmingup_mpc.run_scenario_sizing_v2 import HeatProblemCBC

if __name__ == "__main__":
    print("Hello, Docker!")
    base_folder = Path(__file__).resolve().parent.parent
    input_esdl_file_path = os.environ.get("INPUT_ESDL_FILE_NAME")
    output_esdl_file_path = os.environ.get("OUTPUT_ESDL_FILE_NAME")
    with open(input_esdl_file_path) as open_input_esdl_file:
        input_esdl_string = open_input_esdl_file.read()

    print("I AM DOING OPTIMIZATION MAGIC RIGHT NOW (not really, just printing this message for testing purposes.")
    print("Received input esdl file:")
    print(input_esdl_string)
    import time

    time.sleep(5)
    # solution = run_optimization_problem(HeatProblemCBC, base_folder=base_folder, esdl_string=input_esdl_string)
    # esh = solution.get_optimized_esh()

    with open(output_esdl_file_path, "w+") as open_output_esdl_file:
        open_output_esdl_file.write("TEST OUTPUT!!")
    print("Bye, Docker!")
