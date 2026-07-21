from collections.abc import Callable
from enum import Enum
from typing import Any

from mesido.workflows import (
    NetworkSimulatorHIGHSWeeklyTimeStep,
    run_end_scenario_sizing,
    run_end_scenario_sizing_no_heat_losses,
)
from mesido.workflows.grow_workflow import (
    EndScenarioSizingDiscountedStaged,
    EndScenarioSizingHeadLossStaged,
    EndScenarioSizingStaged,
    SolverGurobi,
    SolverHIGHS,
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
    GROW_OPTIMIZER_EAC = "grow_optimizer_eac"
    """Run the Grow Optimizer with minimum equivalent annual cost goal with HIGHS solver."""

    GROW_OPTIMIZER_DEFAULT_GUROBI = "grow_optimizer_default_gurobi"
    """Run the Grow Optimizer with Gurobi solver."""
    GROW_SIMULATOR_GUROBI = "grow_simulator_gurobi"
    """Run the Grow Simulator with Gurobi solver."""
    GROW_OPTIMIZER_NO_HEAT_LOSSES_GUROBI = "grow_optimizer_no_heat_losses_gurobi"
    """Run the Grow Optimizer without heat losses with Gurobi solver."""
    GROW_OPTIMIZER_WITH_PRESSURE_GUROBI = "grow_optimizer_with_pressure_gurobi"
    """Run the Grow Optimizer with pump pressure with Gurobi solver."""
    GROW_OPTIMIZER_EAC_GUROBI = "grow_optimizer_eac_gurobi"
    """Run the Grow Optimizer with minimum equivalent annual cost goal with Gurobi solver."""


GROWProblem = (
    type[EndScenarioSizingHeadLossStaged]
    | type[EndScenarioSizingStaged]
    | type[EndScenarioSizingDiscountedStaged]
    | type[NetworkSimulatorHIGHSWeeklyTimeStep]
)

GROWProblemFunction = Callable[..., Any]


def get_problem_type(task_type: GrowTaskType) -> GROWProblem:
    """Convert the Grow task type to the Grow problem that should be run.

    Args:
        task_type: Grow task type.

    Returns:
        GROWProblem: Grow problem class.

    Raises:
        RuntimeError: If the task type is unknown.

    """
    result: GROWProblem
    if task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT,
        GrowTaskType.GROW_OPTIMIZER_DEFAULT_GUROBI,
    ]:
        result = EndScenarioSizingStaged
    elif task_type in [
        GrowTaskType.GROW_SIMULATOR,
        GrowTaskType.GROW_SIMULATOR_GUROBI,
    ]:
        result = NetworkSimulatorHIGHSWeeklyTimeStep
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES_GUROBI,
    ]:
        result = EndScenarioSizingStaged
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE_GUROBI,
    ]:
        result = EndScenarioSizingHeadLossStaged
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_EAC,
        GrowTaskType.GROW_OPTIMIZER_EAC_GUROBI,
    ]:
        result = EndScenarioSizingDiscountedStaged
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")

    return result


def get_problem_function(
    task_type: GrowTaskType,
) -> GROWProblemFunction:
    """Convert the Grow task type to the Grow function that should be run.

    Args:
        task_type: Grow task type.

    Returns:
        GROWProblemFunction: Grow problem function.

    Raises:
        RuntimeError: If the task type is unknown.

    """
    result: GROWProblemFunction
    if task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT,
        GrowTaskType.GROW_SIMULATOR,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE,
        GrowTaskType.GROW_OPTIMIZER_DEFAULT_GUROBI,
        GrowTaskType.GROW_SIMULATOR_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_EAC,
        GrowTaskType.GROW_OPTIMIZER_EAC_GUROBI,
    ]:
        result = run_end_scenario_sizing
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES_GUROBI,
    ]:
        result = run_end_scenario_sizing_no_heat_losses
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")

    return result


def get_solver_class(task_type: GrowTaskType) -> type[SolverHIGHS] | type[SolverGurobi]:
    """Convert the Grow task type to the Grow solver that should be run.

    Args:
        task_type: Grow task type.

    Returns:
        type[SolverHIGHS] | type[SolverGurobi]: Grow solver class.

    Raises:
        RuntimeError: If the task type is unknown.

    """
    result: type[SolverHIGHS] | type[SolverGurobi]
    if task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT,
        GrowTaskType.GROW_SIMULATOR,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES,
        GrowTaskType.GROW_OPTIMIZER_EAC,
    ]:
        result = SolverHIGHS
    elif task_type in [
        GrowTaskType.GROW_OPTIMIZER_DEFAULT_GUROBI,
        GrowTaskType.GROW_SIMULATOR_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_NO_HEAT_LOSSES_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_WITH_PRESSURE_GUROBI,
        GrowTaskType.GROW_OPTIMIZER_EAC_GUROBI,
    ]:
        result = SolverGurobi
    else:
        raise RuntimeError(f"Unknown workflow type, please implement {task_type}")
    return result
