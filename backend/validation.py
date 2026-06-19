import re

import pandas as pd

from backend.detection import infer_column_type


NAME_REGEX = re.compile(r"^[A-Za-z ,.'-]+$")
FULL_NAME_REGEX = re.compile(r"^[A-Za-z]+(?: [A-Za-z]+)+$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PREVIEW_LIMIT = 10
PREVIEW_COLUMNS = ["row_number", "column_name", "invalid_value", "reason"]


def _empty_preview_df() -> pd.DataFrame:
    return pd.DataFrame(columns=PREVIEW_COLUMNS)


def _append_preview(existing: pd.DataFrame, preview: pd.DataFrame) -> pd.DataFrame:
    if preview.empty:
        return existing
    if existing.empty:
        return preview.head(PREVIEW_LIMIT).reset_index(drop=True)
    combined = pd.concat([existing, preview], ignore_index=True)
    return combined.head(PREVIEW_LIMIT).reset_index(drop=True)


def _build_invalid_preview(values: pd.Series, invalid_mask: pd.Series, reason: str) -> pd.DataFrame:
    invalid_values = values[invalid_mask]
    if invalid_values.empty:
        return _empty_preview_df()

    preview = pd.DataFrame(
        {
            "row_number": [int(index) + 1 for index in invalid_values.index],
            "column_name": [str(values.name)] * len(invalid_values),
            "invalid_value": invalid_values.astype(str).tolist(),
            "reason": [reason] * len(invalid_values),
        }
    )
    return preview.head(PREVIEW_LIMIT).reset_index(drop=True)


def validate_pattern(values: pd.Series, regex, reason: str) -> dict:
    valid_mask = values.str.match(regex, na=False)

    return {
        "valid": int(valid_mask.sum()),
        "invalid": int((~valid_mask).sum()),
        "invalid_examples": values[~valid_mask].head(5).tolist(),
        "invalid_preview": _build_invalid_preview(values, ~valid_mask, reason),
    }


def validate_fields(df: pd.DataFrame):
    email_quality = {}
    field_quality = {}
    validation_previews = {
        "email": _empty_preview_df(),
        "name": _empty_preview_df(),
        "date_of_birth": _empty_preview_df(),
        "phone": _empty_preview_df(),
    }

    for col in df.columns:
        series = df[col]
        values = series.dropna().astype(str).str.strip()

        total = len(series)
        missing = int(series.isna().sum())
        col_type = infer_column_type(series)

        if col_type == "email":
            result = validate_pattern(
                values,
                EMAIL_REGEX,
                "Expected a valid email address.",
            )
            result.update({"missing": missing, "total": total})
            email_quality[col] = result
            validation_previews["email"] = _append_preview(
                validation_previews["email"],
                result["invalid_preview"],
            )

        elif col_type == "phone":
            result = validate_pattern(
                values,
                PHONE_REGEX,
                "Expected a phone number with 7 to 15 digits.",
            )
            result.update({"type": "phone", "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["phone"] = _append_preview(
                validation_previews["phone"],
                result["invalid_preview"],
            )

        elif col_type in {"date_of_birth", "date"}:
            result = validate_pattern(
                values,
                DATE_REGEX,
                "Expected a date format such as YYYY-MM-DD.",
            )
            result.update({"type": col_type, "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["date_of_birth"] = _append_preview(
                validation_previews["date_of_birth"],
                result["invalid_preview"],
            )

        elif col_type == "name":
            regex = FULL_NAME_REGEX if " " in values.head(1).to_string() else NAME_REGEX
            result = validate_pattern(
                values,
                regex,
                "Expected alphabetic name characters only.",
            )
            result.update({"type": "name", "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["name"] = _append_preview(
                validation_previews["name"],
                result["invalid_preview"],
            )

    return email_quality, field_quality, validation_previews
