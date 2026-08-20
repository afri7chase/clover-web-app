import re

import pandas as pd


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALT_DATE_REGEX = re.compile(r"^\d{2}[/\-]\d{2}[/\-]\d{4}$")

EMAIL_FIELD_NAMES = {"email_address", "e_mail", "user_email", "mail_address"}
USERNAME_FIELD_NAMES = {"username", "user_name", "login_name"}
PHONE_FIELD_NAMES = {
    "phone",
    "phone_number",
    "mobile",
    "mobile_number",
    "telephone",
    "contact_number",
}
DATE_OF_BIRTH_FIELD_NAMES = {"date_of_birth"}
NAME_FIELD_NAMES = {
    "name",
    "first_name",
    "firstname",
    "last_name",
    "lastname",
    "full_name",
    "fullname",
    "given_name",
    "givenname",
    "surname",
}

EMAIL_TOKENS = {"email", "mail"}
DATE_OF_BIRTH_TOKENS = {"dob", "birth"}
GENERIC_DATE_TOKENS = {"date", "created", "updated", "joined", "timestamp", "signup"}
LOCATION_TOKENS = {"street", "road", "avenue", "ave", "city", "country", "parish", "branch", "address"}


def normalize_column_label(column_name: str) -> str:
    lowered = str(column_name).strip().lower()
    normalized = re.sub(r"[\s_-]+", "_", lowered)
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return normalized.strip("_")


def is_name_column_label(column_name: str) -> bool:
    return normalize_column_label(column_name) in NAME_FIELD_NAMES


def is_username_column_label(column_name: str) -> bool:
    return normalize_column_label(column_name) in USERNAME_FIELD_NAMES


def is_phone_column_label(column_name: str) -> bool:
    return normalize_column_label(column_name) in PHONE_FIELD_NAMES


def _column_tokens(column_name: str) -> set[str]:
    normalized = normalize_column_label(column_name)
    return {token for token in normalized.split("_") if token}


def infer_column_type(series: pd.Series) -> str:
    sample = series.dropna().astype(str).str.strip().head(50)

    if sample.empty:
        return "unknown"

    col_name = str(series.name)
    normalized_name = normalize_column_label(col_name)
    tokens = _column_tokens(col_name)

    if LOCATION_TOKENS & tokens and normalized_name not in EMAIL_FIELD_NAMES:
        return "unknown"

    if normalized_name in EMAIL_FIELD_NAMES or "email" in normalized_name or EMAIL_TOKENS & tokens:
        return "email"

    if is_username_column_label(col_name):
        return "username"

    if normalized_name in DATE_OF_BIRTH_FIELD_NAMES or DATE_OF_BIRTH_TOKENS & tokens:
        return "date_of_birth"

    if GENERIC_DATE_TOKENS & tokens:
        return "date"

    if is_phone_column_label(col_name):
        return "phone"

    if is_name_column_label(col_name):
        return "name"

    pure_numeric_ratio = sample.str.match(r"^\d+$").mean()
    if pure_numeric_ratio > 0.8:
        return "unknown"

    iso_date_score = sample.str.match(ISO_DATE_REGEX).mean()
    alt_date_score = sample.str.match(ALT_DATE_REGEX).mean()
    if iso_date_score > 0.6 or alt_date_score > 0.6:
        return "date"

    name_score = sample.apply(
        lambda value: bool(re.match(r"^[A-Za-z]+(?: [A-Za-z]+)+$", value))
    ).mean()
    if name_score > 0.6:
        return "name"

    return "unknown"
