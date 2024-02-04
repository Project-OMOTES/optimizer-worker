from enum import Enum
from typing import Type, Union

from rtctools_heat_network.workflows import EndScenarioSizingHIGHS, NetworkSimulatorHIGHSWeeklyTimeStep


class TaskType(Enum):
    GROW_OPTIMIZER = "grow_optimizer"
    GROW_SIMULATOR = "grow_simulator"


GROWProblem = Union[Type[EndScenarioSizingHIGHS], Type[NetworkSimulatorHIGHSWeeklyTimeStep]]


def get_problem_type(task_type: TaskType) -> GROWProblem:
    if task_type == TaskType.GROW_OPTIMIZER:
        return EndScenarioSizingHIGHS
    elif task_type == TaskType.GROW_SIMULATOR:
        return NetworkSimulatorHIGHSWeeklyTimeStep
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")
