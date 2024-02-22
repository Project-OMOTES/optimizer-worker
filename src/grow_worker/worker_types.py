from enum import Enum
from typing import Type, Union

from rtctools_heat_network.workflows import (
    EndScenarioSizingHIGHS,
    NetworkSimulatorHIGHSWeeklyTimeStep,
)


class GrowTaskType(Enum):
    """Grow task types."""

    GROW_OPTIMIZER = "grow_optimizer"
    """Run the Grow Optimizer."""
    GROW_SIMULATOR = "grow_simulator"
    """Run the Grow simulator."""


GROWProblem = Union[Type[EndScenarioSizingHIGHS], Type[NetworkSimulatorHIGHSWeeklyTimeStep]]


def get_problem_type(task_type: GrowTaskType) -> GROWProblem:
    """Convert the Grow task type to the Grow problem that should be run.

    :param task_type: Grow task type.
    :return: Grow problem class.
    """
    result: GROWProblem
    if task_type == GrowTaskType.GROW_OPTIMIZER:
        result = EndScenarioSizingHIGHS
    elif task_type == GrowTaskType.GROW_SIMULATOR:
        result = NetworkSimulatorHIGHSWeeklyTimeStep
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")

    return result
