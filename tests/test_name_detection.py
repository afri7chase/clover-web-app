import unittest

import pandas as pd

from backend.detection import infer_column_type, is_name_column_label
from utils.metrics import _find_matching_columns


NAME_COLUMN_VARIATIONS = [
    "First_name",
    "FIRST_NAME",
    "first_Name",
    "First_Name",
    "Last_name",
    "LAST_NAME",
    "last_Name",
    "Full_name",
    "FULL_NAME",
    "full_Name",
    "First Name",
    "FIRST NAME",
    "Last Name",
    "FULL NAME",
    "Firstname",
    "FIRSTNAME",
    "firstname",
    "Lastname",
    "LASTNAME",
    "lastname",
    "Given_name",
    "GIVEN_NAME",
    "given_Name",
    "Given_Name",
    "Given Name",
    "GIVEN NAME",
    "given name",
    "Surname",
    "SURNAME",
    "surname",
]

NON_NAME_COLUMNS = [
    "Last active",
    "Last login",
    "First seen",
]


class NameColumnDetectionTests(unittest.TestCase):
    def test_all_listed_name_variations_are_detected(self) -> None:
        for column_name in NAME_COLUMN_VARIATIONS:
            with self.subTest(column_name=column_name):
                self.assertTrue(is_name_column_label(column_name))

    def test_requested_non_name_columns_are_not_detected(self) -> None:
        for column_name in NON_NAME_COLUMNS:
            with self.subTest(column_name=column_name):
                self.assertFalse(is_name_column_label(column_name))

    def test_infer_column_type_marks_exact_name_labels_as_name(self) -> None:
        for column_name in NAME_COLUMN_VARIATIONS:
            with self.subTest(column_name=column_name):
                series = pd.Series(["Alice Smith", "Brian Lewis"], name=column_name)
                self.assertEqual(infer_column_type(series), "name")

    def test_infer_column_type_does_not_treat_last_active_like_name(self) -> None:
        for column_name in NON_NAME_COLUMNS:
            with self.subTest(column_name=column_name):
                series = pd.Series(["2023-11-24", "2024-03-01"], name=column_name)
                self.assertNotEqual(infer_column_type(series), "name")

    def test_metrics_name_matching_uses_exact_normalized_labels(self) -> None:
        dataset = pd.DataFrame(
            {
                "First Name": ["Alice"],
                "First_name": ["Brian"],
                "Firstname": ["Carla"],
                "Last Name": ["Smith"],
                "Last_name": ["Lewis"],
                "Lastname": ["Jones"],
                "Full Name": ["Alice Smith"],
                "Full_name": ["Brian Lewis"],
                "Given Name": ["Carla"],
                "Given_name": ["David"],
                "Surname": ["Clarke"],
                "Last active": ["2023-11-24"],
                "Last login": ["2023-11-25"],
                "First seen": ["2023-11-26"],
            }
        )

        matched_columns = _find_matching_columns(dataset, ["name"], rule_key="name")

        self.assertEqual(
            matched_columns,
            [
                "First Name",
                "First_name",
                "Firstname",
                "Last Name",
                "Last_name",
                "Lastname",
                "Full Name",
                "Full_name",
                "Given Name",
                "Given_name",
                "Surname",
            ],
        )


if __name__ == "__main__":
    unittest.main()
