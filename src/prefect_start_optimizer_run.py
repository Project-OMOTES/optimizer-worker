import asyncio
import os
from pathlib import Path

from prefect_util import trigger_flow_run

# create input:
esdl_input_file = "../local_test/Delft_T.esdl"
# esdl_input_file = "../local_test/optimizer_poc_tutorial_feedback_error.esdl"
esdl_input_string = Path(esdl_input_file).read_text(encoding="utf-8")


wf_parameters = dict(
    input_esdl=esdl_input_string,
    workflow_config={"key": "value"},
    workflow_type_name="grow_optimizer_default",
)

# Defining the arguments passed to the prefect run
asyncio.run(
    trigger_flow_run(
        run_name="run 6",
        deployment_base_name="omotes-optimizer",
        deployment_version="local",
        parameters=wf_parameters,
        memory_limit=os.getenv("PREFECT_RUN_MEMORY_LIMIT"),
        type=wf_parameters["workflow_type_name"],
        username="mark",
    )
)
