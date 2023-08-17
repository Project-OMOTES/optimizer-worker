import os
from pathlib import Path

from rtctools.util import run_optimization_problem

from warmingup_mpc.run_scenario_sizing_v2 import HeatProblemCBC

if __name__ == "__main__":
    print('Hello, Docker!')
    base_folder = Path(__file__).resolve().parent.parent
    input_esdl_file_path = os.environ.get('INPUT_ESDL_FILE_NAME')
    output_esdl_file_path = os.environ.get('OUTPUT_ESDL_FILE_NAME')
    solution = run_optimization_problem(HeatProblemCBC, base_folder=base_folder, esdl_string=esdl_string)
    esh = solution.get_optimized_esh()
    print('Bye, Docker!')
