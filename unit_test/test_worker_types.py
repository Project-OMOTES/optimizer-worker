import unittest
from grow_worker.worker_types import (
    get_problem_type,
    GrowTaskType,
    EndScenarioSizingDiscountedStagedHIGHS,
)


class TestModule(unittest.TestCase):
    def test__get_problem_type__is_correct_grow_optimizer(self) -> None:
        # Arrange
        task_type = GrowTaskType.GROW_OPTIMIZER_DEFAULT

        # Act
        result = get_problem_type(task_type)

        # Assert
        expected_result = EndScenarioSizingDiscountedStagedHIGHS
        self.assertEqual(expected_result, result)
