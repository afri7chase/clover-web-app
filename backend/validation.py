import re
import unicodedata
from datetime import date, datetime

import pandas as pd

from backend.detection import infer_column_type


PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PREVIEW_LIMIT = 10
PREVIEW_COLUMNS = ["row_number", "column_name", "invalid_value", "reason"]
NAME_ALLOWED_SEPARATORS = {" ", "-", "'", "\u2019", "."}
USERNAME_ALLOWED_SEPARATORS = {"_", "-", "."}
SUPPORTED_DATE_FORMATS = (
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%m.%d.%Y",
    "%d.%m.%Y",
    "%Y.%m.%d",
)


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


def is_missing_validation_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return bool(pd.isna(value))


def get_non_missing_validation_values(series: pd.Series) -> pd.Series:
    return series[~series.apply(is_missing_validation_value)]


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


def parse_supported_calendar_date(value) -> pd.Timestamp | None:
    if is_missing_validation_value(value):
        return None

    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.normalize()

    if isinstance(value, datetime):
        return pd.Timestamp(value).normalize()

    if isinstance(value, date):
        return pd.Timestamp(value).normalize()

    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    for date_format in SUPPORTED_DATE_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(cleaned, date_format)).normalize()
        except ValueError:
            continue
    return None


def is_valid_calendar_date_value(value) -> bool:
    return parse_supported_calendar_date(value) is not None


def validate_date_values(values: pd.Series, reason: str) -> dict:
    valid_mask = values.apply(is_valid_calendar_date_value)
    return _build_validation_result(values, valid_mask, reason)


def _is_valid_username(value: str) -> bool:
    cleaned = str(value).strip()
    if not cleaned:
        return False

    lowered = cleaned.casefold()
    if "@" in cleaned or "http://" in lowered or "https://" in lowered or "www." in lowered:
        return False

    if cleaned[0] in USERNAME_ALLOWED_SEPARATORS or cleaned[-1] in USERNAME_ALLOWED_SEPARATORS:
        return False

    has_alphanumeric = False
    previous_was_separator = False
    for char in cleaned:
        if unicodedata.category(char)[0] == "C":
            return False
        if char.isalpha() or char.isdigit():
            has_alphanumeric = True
            previous_was_separator = False
            continue
        if char in USERNAME_ALLOWED_SEPARATORS:
            if previous_was_separator:
                return False
            previous_was_separator = True
            continue
        return False

    return has_alphanumeric


def validate_username_values(values: pd.Series, reason: str) -> dict:
    valid_mask = values.apply(_is_valid_username)
    return _build_validation_result(values, valid_mask, reason)


def validate_fields(df: pd.DataFrame):
    email_quality = {}
    field_quality = {}
    validation_previews = {
        "email": _empty_preview_df(),
        "name": _empty_preview_df(),
        "username": _empty_preview_df(),
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
            date_values = get_non_missing_validation_values(series)
            result = validate_date_values(
                date_values,
                "Not a valid calendar date",
            )
            result.update({"type": col_type, "missing": int(total - len(date_values)), "total": total})
            field_quality[col] = result
            validation_previews["date_of_birth"] = _append_preview(
                validation_previews["date_of_birth"],
                result["invalid_preview"],
            )

        elif col_type == "date":
            date_values = get_non_missing_validation_values(series)
            result = validate_date_values(
                date_values,
                "Not a valid calendar date",
            )
            result.update({"type": col_type, "missing": int(total - len(date_values)), "total": total})
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

        elif col_type == "username":
            result = validate_username_values(
                values,
                "Expected a valid username using letters, numbers, periods, underscores, or hyphens with no spaces, edge separators, or repeated separators.",
            )
            result.update({"type": "username", "missing": missing, "total": total})
            field_quality[col] = result
            validation_previews["username"] = _append_preview(
                validation_previews["username"],
                result["invalid_preview"],
            )

    return email_quality, field_quality, validation_previews
