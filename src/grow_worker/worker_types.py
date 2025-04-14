from enum import Enum
from typing import Type, Union, Callable

from mesido.workflows import NetworkSimulatorHIGHSWeeklyTimeStep
from mesido.workflows.grow_workflow import (
    EndScenarioSizingHeadLossStaged,
    EndScenarioSizingStaged,
    SolverGurobi,
    SolverHIGHS,
)
from mesido.workflows import (
    run_end_scenario_sizing,
    run_end_scenario_sizing_no_heat_losses,
)


class GrowTaskType(Enum):
    """Grow task types."""

    GROW_OPTIMIZER_DEFAULT = "grow_optimizer_default"
    """Run the Grow Optimizer with HIGHS solver."""
    GROW_SIMULATOR = "grow_simulator"
    """Run the Grow Simulator with HIGHS solver."""
    GROW_OPTIMIZER_NO_HEAT_LOSSES = "grow_optimizer_no_heat_losses"
    """Run the Grow Optimizer without heat losses with HIGHS solver."""
    GROW_OPTIMIZER_WITH_PRESSURE = "grow_optimizer_with_pressure"
    """Run the Grow Optimizer with pump pressure with HIGHS solver."""

    GROW_OPTIMIZER_DEFAULT_GUROBI = "grow_optimizer_default_gurobi"
    """Run the Grow Optimizer with Gurobi solver."""
    GROW_SIMULATOR_GUROBI = "grow_simulator_gurobi"
    """Run the Grow Simulator with HIGHS solver."""
    GROW_OPTIMIZER_NO_HEAT_LOSSES_GUROBI = "grow_optimizer_no_heat_losses_gurobi"
    """Run the Grow Optimizer without heat losses with Gurobi solver."""
    GROW_OPTIMIZER_WITH_PRESSURE_GUROBI = "grow_optimizer_with_pressure_gurobi"
    """Run the Grow Optimizer with pump pressure with HIGHS solver."""


GROWProblem = Union[
    Type[EndScenarioSizingHeadLossStaged],
    Type[EndScenarioSizingStaged],
    Type[NetworkSimulatorHIGHSWeeklyTimeStep],
]


def get_problem_type(task_type: GrowTaskType) -> GROWProblem:
    """Convert the Grow task type to the Grow problem that should be run.

    :param task_type: Grow task type.
    :return: Grow problem class.
    """
    result: GROWProblem
    if task_type == GrowTaskType.GROW_OPTIMIZER_DEFAULT:
        result = EndScenarioSizingStaged
    elif task_type == GrowTaskType.GROW_SIMULATOR:
        result = NetworkSimulatorHIGHSWeeklyTimeStep
    elif task_type == GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES:
        result = EndScenarioSizingStaged
    elif task_type == GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE:
        result = EndScenarioSizingHeadLossStaged
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


def get_solver_class(task_type: GrowTaskType) -> Union[Type[SolverHIGHS], Type[SolverGurobi]]:
    """Convert the Grow task type to the Grow solver that should be run.

    :param task_type: Grow task type.
    :return: Grow solver class.
    """
    if task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT,
        GrowTaskType.GROW_SIMULATOR,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES,
    ]:
        result = SolverHIGHS
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT_GUROBI,
        GrowTaskType.GROW_SIMULATOR_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE_GUROBI,
    ]:
        result = SolverGurobi
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")
    return result
