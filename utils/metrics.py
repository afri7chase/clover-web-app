import pandas as pd

from backend.detection import (
    is_name_column_label,
    is_phone_column_label,
    is_username_column_label,
    normalize_column_label,
)
from backend.validation import is_valid_calendar_date_value
from utils.validation_config import VALIDATION_BUCKETS as VALIDATION_RULES

SPECIAL_CHARACTER_PATTERN = r"[^A-Za-z0-9\s@\.\-\+\(\)/,'&]"
LOW_UNIQUENESS_THRESHOLD = 25.0


def _default_validation_result(label: str) -> dict:
    return {
        "label": label,
        "matched_columns": [],
        "valid_count": 0,
        "invalid_count": 0,
        "total_checked": 0,
        "valid_percentage": 0.0,
        "has_match": False,
    }


def _normalize_column_name(column_name: str) -> str:
    return normalize_column_label(column_name)


def _find_matching_columns(
    dataset: pd.DataFrame,
    keywords: list[str],
    rule_key: str | None = None,
) -> list[str]:
    matched_columns = []
    for column in dataset.columns:
        normalized = _normalize_column_name(column)
        if rule_key == "name":
            if is_name_column_label(column):
                matched_columns.append(column)
            continue
        if rule_key == "username":
            if is_username_column_label(column):
                matched_columns.append(column)
            continue
        if rule_key == "phone":
            if is_phone_column_label(column):
                matched_columns.append(column)
            continue
        if any(keyword in normalized for keyword in keywords):
            matched_columns.append(column)
    return matched_columns


def _get_non_empty_values(series: pd.Series) -> pd.Series:
    cleaned = series.dropna().astype(str).str.strip()
    return cleaned[cleaned != ""]


def _validate_email(series: pd.Series) -> pd.Series:
    return series.str.match(
        r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$",
        na=False,
    )


def _validate_name(series: pd.Series) -> pd.Series:
    return series.str.match(r"^[A-Za-z][A-Za-z\s\-'`.]{1,}$", na=False)


def _validate_dob(series: pd.Series) -> pd.Series:
    return series.apply(is_valid_calendar_date_value)


def _validate_phone(series: pd.Series) -> pd.Series:
    digits_only = series.str.replace(r"\D", "", regex=True)
    return digits_only.str.len().between(10, 15)


def _validate_username(series: pd.Series) -> pd.Series:
    return series.str.match(r"^(?![._-])(?!.*[._-]{2})[\w.-]*[A-Za-z0-9][\w.-]*?(?<![._-])$", na=False)


def _calculate_validation_results(dataset: pd.DataFrame) -> tuple[dict, dict]:
    validators = {
        "email": _validate_email,
        "name": _validate_name,
        "username": _validate_username,
        "dob": _validate_dob,
        "phone": _validate_phone,
    }

    validation_results = {}
    total_valid = 0
    total_invalid = 0
    total_checked = 0

    for key, config in VALIDATION_RULES.items():
        matched_columns = _find_matching_columns(dataset, config["keywords"], key)
        result = _default_validation_result(config["label"])
        result["matched_columns"] = matched_columns
        result["has_match"] = bool(matched_columns)

        for column in matched_columns:
            values = _get_non_empty_values(dataset[column])
            if values.empty:
                continue

            validity_mask = validators[key](values)
            valid_count = int(validity_mask.sum())
            checked_count = int(values.shape[0])
            invalid_count = checked_count - valid_count

            result["valid_count"] += valid_count
            result["invalid_count"] += invalid_count
            result["total_checked"] += checked_count

        if result["total_checked"] > 0:
            result["valid_percentage"] = round(
                (result["valid_count"] / result["total_checked"]) * 100,
                1,
            )

        total_valid += result["valid_count"]
        total_invalid += result["invalid_count"]
        total_checked += result["total_checked"]
        validation_results[key] = result

    validation_overview = {
        "valid_count": total_valid,
        "invalid_count": total_invalid,
        "total_checked": total_checked,
        "invalid_percentage": round((total_invalid / total_checked) * 100, 1)
        if total_checked
        else 0.0,
    }

    return validation_results, validation_overview


def _calculate_uniqueness(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    total_rows = max(int(dataset.shape[0]), 1)
    uniqueness_rows = []

    for column in dataset.columns:
        unique_count = int(dataset[column].nunique(dropna=False))
        uniqueness_percentage = round((unique_count / total_rows) * 100, 1)
        uniqueness_rows.append(
            {
                "column": str(column),
                "unique_values": unique_count,
                "uniqueness_percentage": uniqueness_percentage,
            }
        )

    uniqueness_by_column = pd.DataFrame(uniqueness_rows).sort_values(
        by="uniqueness_percentage",
        ascending=True,
    )

    low_uniqueness_columns = uniqueness_by_column[
        uniqueness_by_column["uniqueness_percentage"] < LOW_UNIQUENESS_THRESHOLD
    ].reset_index(drop=True)

    return uniqueness_by_column.reset_index(drop=True), low_uniqueness_columns


def _calculate_special_character_columns(dataset: pd.DataFrame) -> pd.DataFrame:
    flagged_rows = []
    text_columns = dataset.select_dtypes(include=["object", "string"]).columns

    for column in text_columns:
        values = _get_non_empty_values(dataset[column])
        if values.empty:
            continue

        mask = values.str.contains(SPECIAL_CHARACTER_PATTERN, regex=True)
        affected_rows = int(mask.sum())
        if affected_rows == 0:
            continue

        flagged_rows.append(
            {
                "column": str(column),
                "affected_rows": affected_rows,
                "affected_percentage": round((affected_rows / len(values)) * 100, 1),
            }
        )

    if not flagged_rows:
        return pd.DataFrame(columns=["column", "affected_rows", "affected_percentage"])

    return pd.DataFrame(flagged_rows).sort_values(
        by="affected_rows",
        ascending=False,
    ).reset_index(drop=True)


def calculate_dataset_metrics(dataset: pd.DataFrame | None) -> dict:
    """Calculate core dataset quality metrics."""
    if dataset is None:
        empty_missing = pd.DataFrame({"column": ["No data loaded"], "missing_values": [0]})
        empty_uniqueness = pd.DataFrame(
            {
                "column": ["No data loaded"],
                "unique_values": [0],
                "uniqueness_percentage": [0.0],
            }
        )
        empty_special = pd.DataFrame(
            columns=["column", "affected_rows", "affected_percentage"]
        )
        empty_validation = {
            key: _default_validation_result(config["label"])
            for key, config in VALIDATION_RULES.items()
        }

        return {
            "total_rows": 0,
            "total_columns": 0,
            "missing_values": 0,
            "duplicate_rows": 0,
            "missing_by_column": empty_missing,
            "uniqueness_by_column": empty_uniqueness,
            "low_uniqueness_columns": empty_uniqueness.iloc[0:0].copy(),
            "special_character_columns": empty_special,
            "special_character_total": 0,
            "validation_results": empty_validation,
            "validation_overview": {
                "valid_count": 0,
                "invalid_count": 0,
                "total_checked": 0,
                "invalid_percentage": 0.0,
            },
        }

    missing_by_column = (
        dataset.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "column", 0: "missing_values"})
        .sort_values(by="missing_values", ascending=False)
        .reset_index(drop=True)
    )

    validation_results, validation_overview = _calculate_validation_results(dataset)
    uniqueness_by_column, low_uniqueness_columns = _calculate_uniqueness(dataset)
    special_character_columns = _calculate_special_character_columns(dataset)

    return {
        "total_rows": int(dataset.shape[0]),
        "total_columns": int(dataset.shape[1]),
        "missing_values": int(dataset.isna().sum().sum()),
        "duplicate_rows": int(dataset.duplicated().sum()),
        "missing_by_column": missing_by_column,
        "uniqueness_by_column": uniqueness_by_column,
        "low_uniqueness_columns": low_uniqueness_columns,
        "special_character_columns": special_character_columns,
        "special_character_total": int(special_character_columns["affected_rows"].sum())
        if not special_character_columns.empty
        else 0,
        "validation_results": validation_results,
        "validation_overview": validation_overview,
    }


def summarize_top_issues(metrics: dict) -> list[dict]:
    """Build a prioritized list of top quality issues for the dashboard."""
    total_rows = metrics["total_rows"]
    total_columns = metrics["total_columns"]

    if total_rows == 0 or total_columns == 0:
        return [
            {
                "severity": "info",
                "icon": "&#9432;",
                "title": "No dataset loaded",
                "message": "Upload a CSV file to generate issue summaries, validations, and uniqueness analysis.",
            }
        ]

    issues = []
    total_cells = total_rows * total_columns
    missing_ratio = (metrics["missing_values"] / total_cells) * 100 if total_cells else 0.0
    duplicate_ratio = (metrics["duplicate_rows"] / total_rows) * 100 if total_rows else 0.0
    invalid_ratio = metrics["validation_overview"]["invalid_percentage"]

    if metrics["duplicate_rows"] > 0:
        severity = "error" if duplicate_ratio >= 10 else "warning"
        issues.append(
            {
                "severity": severity,
                "icon": "&#10006;" if severity == "error" else "&#9888;",
                "title": "Duplicate rows detected",
                "message": (
                    f"{metrics['duplicate_rows']:,} duplicate rows found "
                    f"({duplicate_ratio:.1f}% of the dataset)."
                ),
            }
        )

    if metrics["missing_values"] > 0:
        top_columns = metrics["missing_by_column"]
        top_columns = top_columns[top_columns["missing_values"] > 0]["column"].head(3).tolist()
        severity = "error" if missing_ratio >= 10 else "warning"
        issues.append(
            {
                "severity": severity,
                "icon": "&#10006;" if severity == "error" else "&#9888;",
                "title": "Missing values require review",
                "message": (
                    f"{metrics['missing_values']:,} missing values detected "
                    f"({missing_ratio:.1f}% of all cells). "
                    f"Most affected columns: {', '.join(top_columns) or 'n/a'}."
                ),
            }
        )

    if metrics["validation_overview"]["invalid_count"] > 0:
        failing_checks = [
            result["label"].replace(" Validation", "")
            for result in metrics["validation_results"].values()
            if result["invalid_count"] > 0
        ]
        severity = "error" if invalid_ratio >= 15 else "warning"
        issues.append(
            {
                "severity": severity,
                "icon": "&#10006;" if severity == "error" else "&#9888;",
                "title": "Validation failures found",
                "message": (
                    f"{metrics['validation_overview']['invalid_count']:,} invalid values "
                    f"across {', '.join(failing_checks)} checks."
                ),
            }
        )

    if metrics["special_character_total"] > 0:
        top_special_columns = metrics["special_character_columns"]["column"].head(3).tolist()
        issues.append(
            {
                "severity": "info",
                "icon": "&#9432;",
                "title": "Special characters detected",
                "message": (
                    f"{metrics['special_character_total']:,} values include uncommon symbols. "
                    f"Review columns: {', '.join(top_special_columns)}."
                ),
            }
        )

    if not metrics["low_uniqueness_columns"].empty:
        low_unique_columns = metrics["low_uniqueness_columns"]["column"].head(4).tolist()
        severity = "warning" if len(low_unique_columns) >= 2 else "info"
        issues.append(
            {
                "severity": severity,
                "icon": "&#9888;" if severity == "warning" else "&#9432;",
                "title": "Low uniqueness columns identified",
                "message": (
                    f"{len(metrics['low_uniqueness_columns'])} columns have uniqueness below "
                    f"{LOW_UNIQUENESS_THRESHOLD:.0f}%. "
                    f"Examples: {', '.join(low_unique_columns)}."
                ),
            }
        )

    if not issues:
        issues.append(
            {
                "severity": "info",
                "icon": "&#9432;",
                "title": "No major issues detected",
                "message": "The current dataset has no duplicate, missing, or validation issues in the tracked checks.",
            }
        )

    severity_order = {"error": 0, "warning": 1, "info": 2}
    return sorted(issues, key=lambda issue: severity_order[issue["severity"]])
