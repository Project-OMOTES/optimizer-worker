from enum import Enum
from typing import Type, Union, Callable

from rtctools_heat_network.workflows import (
    EndScenarioSizingHIGHS,
    NetworkSimulatorHIGHSWeeklyTimeStep,
    EndScenarioSizingStagedHIGHS,
    EndScenarioSizingDiscountedHIGHS,
)
from rtctools_heat_network.workflows import (
    run_end_scenario_sizing,
    run_end_scenario_sizing_no_heat_losses,
)


class GrowTaskType(Enum):
    """Grow task types."""

    GROW_OPTIMIZER = "grow_optimizer"
    """Run the Grow Optimizer."""
    GROW_SIMULATOR = "grow_simulator"
    """Run the Grow Simulator."""
    GROW_OPTIMIZER_NO_HEAT_LOSSES = "grow_optimizer_no_heat_losses"
    """Run the Grow Optimizer without heat losses."""
    GROW_OPTIMIZER_NO_HEAT_LOSSES_DISCOUNTED_CAPEX = (
        "grow_optimizer_no_heat_losses_discounted_capex"
    )
    """Run the Grow Optimizer without heat losses and a discounted CAPEX."""


GROWProblem = Union[
    Type[EndScenarioSizingHIGHS],
    Type[NetworkSimulatorHIGHSWeeklyTimeStep],
    Type[EndScenarioSizingStagedHIGHS],
    Type[EndScenarioSizingDiscountedHIGHS],
]


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
    elif task_type == GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES:
        result = EndScenarioSizingStagedHIGHS
    elif task_type == GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES_DISCOUNTED_CAPEX:
        result = EndScenarioSizingDiscountedHIGHS
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
    if task_type in [GrowTaskType.GROW_OPTIMIZER, GrowTaskType.GROW_SIMULATOR]:
        result = run_end_scenario_sizing
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES_DISCOUNTED_CAPEX,
    ]:
        result = run_end_scenario_sizing_no_heat_losses
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")

    return result
