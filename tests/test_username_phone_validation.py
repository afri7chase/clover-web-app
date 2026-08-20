import unittest

import pandas as pd

from backend.detection import (
    infer_column_type,
    is_phone_column_label,
    is_username_column_label,
)
from backend.validation import validate_fields, validate_username_values
from utils.metrics import _find_matching_columns
from utils.validation_config import VALIDATION_BUCKETS, VALIDATION_ORDER


USERNAME_COLUMN_VARIATIONS = [
    "Username",
    "USERNAME",
    "username",
    "User_name",
    "USER_NAME",
    "user_Name",
    "User Name",
    "USER NAME",
    "user name",
    "User-name",
    "USER-NAME",
    "Login name",
    "Login_name",
    "Login-name",
]

PHONE_COLUMN_VARIATIONS = [
    "Phone",
    "Phone Number",
    "Phone_number",
    "Mobile",
    "Mobile Number",
    "Telephone",
    "Contact Number",
]

NON_USERNAME_COLUMNS = [
    "User ID",
    "User status",
    "User type",
    "Last active",
    "Last login",
    "Account created",
]


class UsernameAndPhoneValidationTests(unittest.TestCase):
    def test_username_column_variations_are_detected(self) -> None:
        for column_name in USERNAME_COLUMN_VARIATIONS:
            with self.subTest(column_name=column_name):
                self.assertTrue(is_username_column_label(column_name))
                series = pd.Series(["Nyy_30", "johnsmith"], name=column_name)
                self.assertEqual(infer_column_type(series), "username")

    def test_username_is_not_treated_as_name(self) -> None:
        series = pd.Series(["Nyy_30", "JohnSmith25"], name="Username")
        self.assertEqual(infer_column_type(series), "username")
        self.assertNotEqual(infer_column_type(series), "name")

    def test_user_id_is_not_treated_as_username(self) -> None:
        self.assertFalse(is_username_column_label("User ID"))
        series = pd.Series(["12345", "67890"], name="User ID")
        self.assertNotEqual(infer_column_type(series), "username")

    def test_last_active_is_not_name_username_or_phone(self) -> None:
        series = pd.Series(["2023-11-24", "2024-02-01"], name="Last active")
        inferred = infer_column_type(series)
        self.assertNotIn(inferred, {"name", "username", "phone"})

    def test_genuine_phone_columns_are_detected(self) -> None:
        for column_name in PHONE_COLUMN_VARIATIONS:
            with self.subTest(column_name=column_name):
                self.assertTrue(is_phone_column_label(column_name))
                series = pd.Series(["246-425-8359", "0539502"], name=column_name)
                self.assertEqual(infer_column_type(series), "phone")

    def test_username_validation_accepts_nyy_30(self) -> None:
        series = pd.Series(["Nyy_30"], name="Username")
        result = validate_username_values(
            series,
            "Expected a valid username using letters, numbers, periods, underscores, or hyphens with no spaces, edge separators, or repeated separators.",
        )
        self.assertEqual(result["valid"], 1)
        self.assertEqual(result["invalid"], 0)

    def test_username_validation_rejects_invalid_patterns(self) -> None:
        values = pd.Series(
            [
                "user name",
                "@username",
                "user!",
                "_username",
                "username_",
                "user__name",
                "...",
                ".*",
                "*-",
            ],
            name="Username",
        )
        result = validate_username_values(
            values,
            "Expected a valid username using letters, numbers, periods, underscores, or hyphens with no spaces, edge separators, or repeated separators.",
        )
        self.assertEqual(result["valid"], 0)
        self.assertEqual(result["invalid"], len(values))

    def test_backend_validation_returns_username_separately(self) -> None:
        dataset = pd.DataFrame(
            {
                "Username": ["Nyy_30", "user__name"],
                "Full Name": ["Alice Smith", "Brian Lewis"],
                "Last active": ["2023-11-24", "2023-11-25"],
            }
        )

        email_quality, field_quality, validation_previews = validate_fields(dataset)

        self.assertEqual(email_quality, {})
        self.assertIn("Username", field_quality)
        self.assertEqual(field_quality["Username"]["type"], "username")
        self.assertEqual(field_quality["Username"]["valid"], 1)
        self.assertEqual(field_quality["Username"]["invalid"], 1)
        self.assertFalse(validation_previews["username"].empty)
        self.assertEqual(validation_previews["username"].iloc[0]["invalid_value"], "user__name")
        self.assertTrue(validation_previews["name"].empty)

    def test_metrics_username_matching_is_exact(self) -> None:
        dataset = pd.DataFrame(
            {
                "Username": ["Nyy_30"],
                "User Name": ["johnsmith"],
                "Login name": ["user.name"],
                "User ID": ["12345"],
                "Last login": ["2023-11-24"],
            }
        )

        matched_columns = _find_matching_columns(
            dataset,
            VALIDATION_BUCKETS["username"]["keywords"],
            rule_key="username",
        )

        self.assertEqual(matched_columns, ["Username", "User Name", "Login name"])

    def test_dashboard_config_includes_separate_username_bucket(self) -> None:
        self.assertIn("username", VALIDATION_BUCKETS)
        self.assertEqual(VALIDATION_BUCKETS["username"]["label"], "Username Validation")
        self.assertIn("username", VALIDATION_ORDER)
        self.assertNotEqual(VALIDATION_ORDER.index("username"), VALIDATION_ORDER.index("name"))


if __name__ == "__main__":
    unittest.main()
