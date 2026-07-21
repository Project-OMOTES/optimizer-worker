import unittest

from worker_types import (
    EndScenarioSizingStaged,
    GrowTaskType,
    get_problem_type,
)


class TestModule(unittest.TestCase):
    """Tests for worker type conversion helpers."""

    def test__get_problem_type__is_correct_grow_optimizer(self) -> None:
        """Verify optimizer default task maps to the staged sizing problem class."""
        # Arrange
        task_type = GrowTaskType.GROW_OPTIMIZER_DEFAULT

        # Act
        result = get_problem_type(task_type)

        # Assert
        expected_result = EndScenarioSizingStaged
        self.assertEqual(expected_result, result)
