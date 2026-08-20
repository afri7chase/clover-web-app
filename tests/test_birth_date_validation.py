import unittest
from datetime import datetime

import pandas as pd

from backend.validation import (
    get_non_missing_validation_values,
    validate_date_values,
    validate_fields,
    validate_phone_values,
    validate_username_values,
)
from utils.metrics import calculate_dataset_metrics


VALID_BIRTH_DATES = [
    "12/25/1994",
    "25/12/1994",
    "1994/12/25",
    "12-25-1994",
    "25-12-1994",
    "1994-12-25",
    "12.25.1994",
    "25.12.1994",
    "1994.12.25",
    "2024-02-29",
]

INVALID_BIRTH_DATES = [
    "1994-65-80",
    "1994/13/40",
    "32/12/1994",
    "02/30/2024",
    "2023-02-29",
    "random text that cannot be interpreted as a date",
]


class BirthDateValidationTests(unittest.TestCase):
    def test_supported_birth_date_formats_are_accepted(self) -> None:
        values = pd.Series(VALID_BIRTH_DATES, name="Birth Date")
        result = validate_date_values(values, "Not a valid calendar date")

        self.assertEqual(result["valid"], len(VALID_BIRTH_DATES))
        self.assertEqual(result["invalid"], 0)

    def test_ambiguous_but_possible_dates_are_accepted(self) -> None:
        values = pd.Series(["01/02/2020", "02-01-2020", "03.04.2020"], name="Birth Date")
        result = validate_date_values(values, "Not a valid calendar date")

        self.assertEqual(result["valid"], 3)
        self.assertEqual(result["invalid"], 0)

    def test_valid_and_invalid_leap_dates_are_handled_strictly(self) -> None:
        values = pd.Series(["2024-02-29", "2023-02-29"], name="Birth Date")
        result = validate_date_values(values, "Not a valid calendar date")

        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(result["invalid_preview"].iloc[0]["invalid_value"], "2023-02-29")

    def test_impossible_birth_dates_are_rejected(self) -> None:
        values = pd.Series(INVALID_BIRTH_DATES, name="Birth Date")
        result = validate_date_values(values, "Not a valid calendar date")

        self.assertEqual(result["valid"], 0)
        self.assertEqual(result["invalid"], len(INVALID_BIRTH_DATES))

    def test_missing_birth_dates_are_excluded_from_invalid_preview(self) -> None:
        series = pd.Series(
            ["1994-12-25", None, pd.NA, "", "   ", "1994-65-80"],
            name="Birth Date",
        )
        present_values = get_non_missing_validation_values(series)
        result = validate_date_values(present_values, "Not a valid calendar date")

        self.assertEqual(present_values.tolist(), ["1994-12-25", "1994-65-80"])
        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(result["invalid_preview"]["invalid_value"].tolist(), ["1994-65-80"])

    def test_original_birth_date_formatting_is_preserved_in_previews(self) -> None:
        dataset = pd.DataFrame(
            {
                "Date of Birth": ["25.12.1994", "1994-65-80", "  ", "02/30/2024"],
            }
        )
        original_values = dataset["Date of Birth"].copy(deep=True)

        _, field_quality, validation_previews = validate_fields(dataset)

        self.assertTrue(dataset["Date of Birth"].equals(original_values))
        self.assertEqual(field_quality["Date of Birth"]["valid"], 1)
        self.assertEqual(field_quality["Date of Birth"]["invalid"], 2)
        self.assertEqual(field_quality["Date of Birth"]["missing"], 1)
        self.assertEqual(
            validation_previews["date_of_birth"]["invalid_value"].tolist(),
            ["1994-65-80", "02/30/2024"],
        )
        self.assertEqual(
            validation_previews["date_of_birth"]["reason"].tolist(),
            ["Not a valid calendar date", "Not a valid calendar date"],
        )

    def test_datetime_objects_are_accepted(self) -> None:
        values = pd.Series([pd.Timestamp("1994-12-25"), datetime(2024, 2, 29)], name="Birth Date")
        result = validate_date_values(values, "Not a valid calendar date")

        self.assertEqual(result["valid"], 2)
        self.assertEqual(result["invalid"], 0)

    def test_metrics_birth_date_summary_uses_same_calendar_logic(self) -> None:
        dataset = pd.DataFrame(
            {
                "Date of Birth": ["12/25/1994", "25/12/1994", "2023-02-29", "", "1994-65-80"],
            }
        )
        metrics = calculate_dataset_metrics(dataset)
        dob_result = metrics["validation_results"]["dob"]

        self.assertEqual(dob_result["valid_count"], 2)
        self.assertEqual(dob_result["invalid_count"], 2)
        self.assertEqual(dob_result["total_checked"], 4)
        self.assertEqual(dob_result["valid_percentage"], 50.0)

    def test_other_validation_categories_are_unchanged(self) -> None:
        username_result = validate_username_values(
            pd.Series(["Nyy_30", "user__name"], name="Username"),
            "Expected a valid username using letters, numbers, periods, underscores, or hyphens with no spaces, edge separators, or repeated separators.",
        )
        phone_result = validate_phone_values(
            pd.Series(["246-425-8359", "12"], name="Phone"),
            "Expected 7 to 15 digits after removing separators.",
        )

        self.assertEqual(username_result["valid"], 1)
        self.assertEqual(username_result["invalid"], 1)
        self.assertEqual(phone_result["valid"], 1)
        self.assertEqual(phone_result["invalid"], 1)


if __name__ == "__main__":
    unittest.main()
