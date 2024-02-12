from enum import Enum
from typing import Type, Union

from rtctools_heat_network.workflows import EndScenarioSizingHIGHS, NetworkSimulatorHIGHSWeeklyTimeStep


class WorkFlowType(Enum):
    GROW_OPTIMIZER = "grow_optimizer"
    GROW_SIMULATOR = "grow_simulator"


GROWProblem = Union[Type[EndScenarioSizingHIGHS], Type[NetworkSimulatorHIGHSWeeklyTimeStep]]


def get_problem_type(workflow_type: WorkFlowType) -> GROWProblem:
    if workflow_type == WorkFlowType.GROW_OPTIMIZER:
        return EndScenarioSizingHIGHS
    elif workflow_type == WorkFlowType.GROW_SIMULATOR:
        return NetworkSimulatorHIGHSWeeklyTimeStep
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {workflow_type}")
