import re

import pandas as pd

from backend.detection import infer_column_type


NAME_REGEX = re.compile(r"^[A-Za-z ,.\'-]+$")
FULL_NAME_REGEX = re.compile(r"^[A-Za-z]+(?: [A-Za-z]+)+$")
DATE_OF_BIRTH_REGEX = re.compile(r"^(0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])[/-]\d{4}$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PREVIEW_LIMIT = 10
PREVIEW_COLUMNS = ["row_number", "column_name", "invalid_value", "reason"]
NAME_ALLOWED_SEPARATORS = {" ", "-", "'", "\u2019", "."}


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


def _build_validation_result(
    original_values: pd.Series,
    valid_mask: pd.Series,
    reason: str,
) -> dict:
    invalid_mask = ~valid_mask
    return {
        "valid": int(valid_mask.sum()),
        "invalid": int(invalid_mask.sum()),
        "invalid_examples": original_values[invalid_mask].head(5).tolist(),
        "invalid_preview": _build_invalid_preview(original_values, invalid_mask, reason),
    }


def validate_pattern(values: pd.Series, regex, reason: str) -> dict:
    valid_mask = values.str.match(regex, na=False)
    return _build_validation_result(values, valid_mask, reason)


def _normalize_phone_values(values: pd.Series) -> pd.Series:
    normalized = values.astype(str).str.strip()
    normalized = normalized.str.replace(r"\.0$", "", regex=True)
    normalized = normalized.str.replace(r"[^\d]", "", regex=True)
    return normalized


def validate_phone_values(values: pd.Series, reason: str) -> dict:
    normalized = _normalize_phone_values(values)
    valid_mask = normalized.str.match(r"^\d{7,15}$", na=False)
    return _build_validation_result(values, valid_mask, reason)


def _is_valid_name(value: str) -> bool:
    cleaned = str(value).strip()
    if not cleaned:
        return False

    lowered = cleaned.casefold()
    if "@" in cleaned or "http://" in lowered or "https://" in lowered or "www." in lowered:
        return False
    if any(char.isdigit() for char in cleaned):
        return False

    alpha_count = 0
    previous_separator = False
    for index, char in enumerate(cleaned):
        if char.isalpha():
            alpha_count += 1
            previous_separator = False
            continue

        if char in NAME_ALLOWED_SEPARATORS:
            if index == 0 or index == len(cleaned) - 1:
                return False
            if previous_separator and char != " ":
                return False
            previous_separator = char != " "
            continue

        return False

    return alpha_count > 0


def validate_name_values(values: pd.Series, reason: str) -> dict:
    valid_mask = values.apply(_is_valid_name)
    return _build_validation_result(values, valid_mask, reason)


def validate_date_of_birth_values(values: pd.Series, reason: str) -> dict:
    format_mask = values.str.match(DATE_OF_BIRTH_REGEX, na=False)
    normalized = values.str.replace("/", "-", regex=False)
    parsed_dates = pd.to_datetime(normalized, format="%m-%d-%Y", errors="coerce")
    today = pd.Timestamp.today().normalize()
    valid_mask = format_mask & parsed_dates.notna() & parsed_dates.le(today)
    return _build_validation_result(values, valid_mask, reason)


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
            result = validate_phone_values(
                values,
                "Expected 7 to 15 digits after removing separators.",
            )
            result.update({"type": "phone", "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["phone"] = _append_preview(
                validation_previews["phone"],
                result["invalid_preview"],
            )

        elif col_type == "date_of_birth":
            result = validate_date_of_birth_values(
                values,
                "Expected format MM/DD/YYYY or MM-DD-YYYY and a valid non-future date.",
            )
            result.update({"type": col_type, "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["date_of_birth"] = _append_preview(
                validation_previews["date_of_birth"],
                result["invalid_preview"],
            )

        elif col_type == "date":
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
            result = validate_name_values(
                values,
                "Expected a valid personal name using letters, spaces, apostrophes, hyphens, or periods.",
            )
            result.update({"type": "name", "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["name"] = _append_preview(
                validation_previews["name"],
                result["invalid_preview"],
            )

    return email_quality, field_quality, validation_previews
