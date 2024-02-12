import unittest
from grow_worker.worker_types import TaskType


class MyTest(unittest.TestCase):
    def test__testable_function__is_correct(self) -> None:
        # Arrange
        values = [True, True, False]

        # Act
        result = any(values)

        # Assert
        expected_result = True
        self.assertEqual(expected_result, result)
