from pathlib import Path

from omotes_optimizer_worker.prefect_flow import OptimizerFlowResult, optimizer_flow

input_esdl_file = Path(__file__).parents[1] / "tests" / "data" / "esdl" / "Delft_T.esdl"
# input_esdl_file = Path(__file__).parents[1] / "tests" / "data" / "esdl" / "Delft_T_feedback.esdl"

workflow_type_name = "grow_optimizer_no_heat_losses"

with open(input_esdl_file) as open_file:
    input_esdl = open_file.read()

optimizer_flow_result = optimizer_flow.fn(
    input_esdl=input_esdl,
    workflow_config={},
    workflow_type_name=workflow_type_name,
)
if not isinstance(optimizer_flow_result, OptimizerFlowResult):
    raise RuntimeError(f"Optimizer flow did not return a result: {optimizer_flow_result}")
if optimizer_flow_result.output_esdl is None:
    raise RuntimeError("Optimizer flow did not produce output ESDL")

print("--------------ESDL messages:")
print(optimizer_flow_result.esdl_messages)
print("--------------Result")
print(f"Job is done (type: {workflow_type_name}). Output esdl length: {len(optimizer_flow_result.output_esdl)}, ")

# print("Output ESDL:", optimizer_flow_result.output_esdl)
