import re
import pandas as pd

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_REGEX = re.compile(r"^\+?[\d\s\-\(\)\.]{7,20}$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}[/\-]\d{2}[/\-]\d{4}$")

EMAIL_TOKENS = {"email", "email_address", "e-mail", "mail_address"}
PHONE_TOKENS = {"phone", "mobile", "cell", "tel", "contact", "number"}
NAME_TOKENS = {"name", "first", "last", "surname", "given"}
DATE_OF_BIRTH_TOKENS = {"dob", "birth", "date_of_birth"}
GENERIC_DATE_TOKENS = {"date","created", "updated", "joined", "timestamp","signup"}
LOCATION_TOKENS = {"street", "road", "avenue", "ave", "city", "country", "parish", "branch"}

def infer_column_type(series: pd.Series) -> str:
    sample = series.dropna().astype(str).str.strip().head(50)

    if sample.empty:
        return "unknown"

    col_name = str(series.name).lower()

    # ✅ EXCLUDE LOCATION-LIKE COLUMNS (PUT IT HERE ✅)
    if any(token in col_name for token in LOCATION_TOKENS):
        return "unknown"

    # ✅ STRONG NAME SIGNALS
    if any(token in col_name for token in NAME_TOKENS):
        return "name"

    # ✅ STRONG DATE SIGNALS
    if any(token in col_name for token in DATE_OF_BIRTH_TOKENS):
        return "date_of_birth"
    
    if any(token in col_name for token in GENERIC_DATE_TOKENS):
        return "date"

    # ✅ EMAIL
    if any(token in col_name for token in EMAIL_TOKENS):
        return "email"

    # ✅ PHONE
    if any(token in col_name for token in PHONE_TOKENS):
        return "phone"

    # -------------------------
    # FALLBACK LOGIC
    # -------------------------

    # ✅ numeric noise guard
    pure_numeric_ratio = sample.str.match(r"^\d+$").mean()
    if pure_numeric_ratio > 0.8:
        return "unknown"

    # ✅ phone fallback
    phone_score = sample.str.match(r"^\+?[\d\s\-\(\)\.]{7,20}$").mean()
    digits_only = sample.str.replace(r"\D", "", regex=True)
    length_score = digits_only.str.len().between(7, 15).mean()

    if phone_score > 0.6 and length_score > 0.7:
        return "phone"

    # ✅ date fallback
    date_score = sample.str.match(r"^\d{4}-\d{2}-\d{2}$").mean()
    alt_date_score = sample.str.match(r"^\d{2}[/\-]\d{2}[/\-]\d{4}$").mean()

    if date_score > 0.6 or alt_date_score > 0.6:
        return "date"

    # ✅ multi-word names (full names)
    name_score = sample.str.match(r"^[A-Za-z]+(?: [A-Za-z]+)+$").mean()

    if name_score > 0.6:
        return "name"

# ✅ single-word names (first/last) — ONLY if column name suggests it
    if any(token in col_name for token in NAME_TOKENS):
        single_word_score = sample.str.match(r"^[A-Za-z]+$").mean()

        if single_word_score > 0.7:
            return "name"
