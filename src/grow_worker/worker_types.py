from enum import Enum
from typing import Type, Union, Callable

from mesido.workflows import NetworkSimulatorHIGHSWeeklyTimeStep
from mesido.workflows.grow_workflow import (
    EndScenarioSizingDiscountedStagedHIGHS,
    EndScenarioSizingHeadLossDiscountedStaged,
)
from mesido.workflows import (
    run_end_scenario_sizing,
    run_end_scenario_sizing_no_heat_losses,
)


class GrowTaskType(Enum):
    """Grow task types."""

    GROW_OPTIMIZER_DEFAULT = "grow_optimizer_default"
    """Run the Grow Optimizer."""
    GROW_SIMULATOR = "grow_simulator"
    """Run the Grow Simulator."""
    GROW_OPTIMIZER_NO_HEAT_LOSSES = "grow_optimizer_no_heat_losses"
    """Run the Grow Optimizer without heat losses."""
    GROW_OPTIMIZER_WITH_PRESSURE = "grow_optimizer_with_pressure"
    """Run the Grow Optimizer with pump pressure."""


GROWProblem = Union[
    Type[EndScenarioSizingHeadLossDiscountedStaged],
    Type[EndScenarioSizingDiscountedStagedHIGHS],
    Type[NetworkSimulatorHIGHSWeeklyTimeStep],
]


def get_problem_type(task_type: GrowTaskType) -> GROWProblem:
    """Convert the Grow task type to the Grow problem that should be run.

    :param task_type: Grow task type.
    :return: Grow problem class.
    """
    result: GROWProblem
    if task_type == GrowTaskType.GROW_OPTIMIZER_DEFAULT:
        result = EndScenarioSizingDiscountedStagedHIGHS
    elif task_type == GrowTaskType.GROW_SIMULATOR:
        result = NetworkSimulatorHIGHSWeeklyTimeStep
    elif task_type == GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES:
        result = EndScenarioSizingDiscountedStagedHIGHS
    elif task_type == GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE:
        result = EndScenarioSizingHeadLossDiscountedStaged
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")

    return result


def get_problem_function(
    task_type: GrowTaskType,
) -> Callable[..., GROWProblem]:
    """Convert the Grow task type to the Grow function that should be run.

    :param task_type: Grow task type.
    :return: Grow problem function.
    """
    result: GROWProblem
    if task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT,
        GrowTaskType.GROW_SIMULATOR,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE,
    ]:
        result = run_end_scenario_sizing
    elif task_type == GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES:
        result = run_end_scenario_sizing_no_heat_losses
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")

    return result
