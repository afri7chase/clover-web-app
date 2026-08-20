import unittest

import pandas as pd

from utils.pdf_report import build_quality_report_pdf_bytes


class PdfReportTests(unittest.TestCase):
    def test_pdf_generation_returns_non_empty_pdf_bytes(self) -> None:
        dataset_info = {
            "file_name": "sample_dataset.csv",
            "last_analyzed": "2026-07-23 10:00 AM",
        }
        metrics = {
            "validation_overview": {
                "valid_count": 10,
                "invalid_count": 2,
                "total_checked": 12,
                "invalid_percentage": 16.7,
            },
            "validation_results": {
                "email": {"label": "Email Validation", "valid_count": 3, "invalid_count": 1, "valid_percentage": 75.0},
                "name": {"label": "Name Validation", "valid_count": 2, "invalid_count": 0, "valid_percentage": 100.0},
                "username": {"label": "Username Validation", "valid_count": 2, "invalid_count": 0, "valid_percentage": 100.0},
                "dob": {"label": "Date of Birth Validation", "valid_count": 1, "invalid_count": 1, "valid_percentage": 50.0},
                "phone": {"label": "Phone Validation", "valid_count": 2, "invalid_count": 0, "valid_percentage": 100.0},
            },
            "duplicate_summary": {
                "exact_duplicates_count": 1,
                "exact_duplicates_pct": 10.0,
                "email_duplicates_count": 0,
                "email_duplicates_pct": 0.0,
            },
            "special_character_columns": pd.DataFrame(
                [
                    {
                        "column": "notes",
                        "column_type": "generic",
                        "affected_rows": 1,
                        "special_char_count": 2,
                        "emoji_count": 0,
                    }
                ]
            ),
            "missing_by_column": pd.DataFrame(
                [
                    {"column": "phone", "missing_values": 1},
                    {"column": "notes", "missing_values": 0},
                ]
            ),
            "low_uniqueness_columns": pd.DataFrame(columns=["column"]),
            "special_character_total": 1,
            "duplicate_rows": 1,
            "missing_values": 1,
            "total_rows": 10,
            "total_columns": 5,
            "valid_records": 8,
            "quality_status_raw": "WARN",
        }
        top_issues = [
            {
                "title": "Validation failures found",
                "message": "2 invalid values across tracked checks.",
            }
        ]
        column_risk_ranking = pd.DataFrame(
            [
                {
                    "rank": 1,
                    "column": "date_of_birth",
                    "risk_level": "High",
                    "primary_issue": "Invalid Dates",
                    "risk_score": 92,
                }
            ]
        )

        pdf_bytes = build_quality_report_pdf_bytes(
            dataset_info,
            metrics,
            84.2,
            top_issues,
            column_risk_ranking,
        )

        self.assertTrue(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 100)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
