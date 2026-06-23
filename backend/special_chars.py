import re
import unicodedata

import pandas as pd

from backend.detection import infer_column_type


EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "]+",
    flags=re.UNICODE,
)
ADDRESS_TOKENS = {
    "address",
    "street",
    "road",
    "avenue",
    "ave",
    "lane",
    "drive",
    "blvd",
    "boulevard",
    "box",
    "po",
    "postal",
    "zip",
    "postcode",
    "apartment",
    "apt",
    "unit",
}
EMAIL_TOKENS = {
    "email",
    "e_mail",
    "user_email",
    "mail",
}
PASSWORD_TOKENS = {
    "password",
    "passwd",
    "passcode",
    "secret",
    "pin",
}
TECHNICAL_TOKENS = {
    "salt",
    "hash",
    "token",
    "key",
    "encrypted",
    "encryption",
    "checksum",
    "signature",
    "digest",
    "uuid",
}
DEFAULT_ALLOWED_PUNCTUATION = {" ", "-", "'", "’", ".", ",", "/", "&", "#", "(", ")", "+", "_", ":"}
NAME_ALLOWED_PUNCTUATION = {" ", "-", "'", "’", "."}
ADDRESS_ALLOWED_PUNCTUATION = {" ", "#", ".", ",", "/", "-", "&", "'", "’"}
PHONE_ALLOWED_PUNCTUATION = {" ", "+", "-", "(", ")"}
EMAIL_ALLOWED_PUNCTUATION = {"@", ".", "_", "-", "+"}
SKIP_COLUMN_TYPES = {"password", "technical"}


def _is_letter(char: str) -> bool:
    return unicodedata.category(char).startswith("L")


def _is_digit(char: str) -> bool:
    return unicodedata.category(char) == "Nd"


def _contains_emoji(char: str) -> bool:
    return bool(EMOJI_REGEX.fullmatch(char))


def _normalized_column_tokens(column_name: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(column_name).lower())
    return {token for token in normalized.split() if token}


def _looks_like_email_column(column_name: str, tokens: set[str]) -> bool:
    lowered = str(column_name).lower()
    return (
        "email" in tokens
        or lowered in {"email_address", "e_mail", "user_email"}
        or "email" in lowered
    )


def _infer_special_char_column_type(column_name: str, series: pd.Series) -> str:
    tokens = _normalized_column_tokens(column_name)
    if PASSWORD_TOKENS & tokens:
        return "password"
    if TECHNICAL_TOKENS & tokens:
        return "technical"
    if _looks_like_email_column(column_name, tokens) or EMAIL_TOKENS & tokens:
        return "email"
    if ADDRESS_TOKENS & tokens:
        return "address"

    inferred = infer_column_type(series)
    if inferred in {"email", "name", "phone"}:
        return inferred
    if inferred in {"date_of_birth", "date"}:
        return "date"
    return "generic"


def _is_allowed_char(char: str, column_type: str) -> bool:
    if char.isspace():
        return True

    if column_type == "email":
        return char.isascii() and (char.isalpha() or char.isdigit() or char in EMAIL_ALLOWED_PUNCTUATION)

    if column_type == "phone":
        return _is_digit(char) or char in PHONE_ALLOWED_PUNCTUATION

    if column_type == "address":
        return _is_letter(char) or _is_digit(char) or char in ADDRESS_ALLOWED_PUNCTUATION

    if column_type == "name":
        return _is_letter(char) or char in NAME_ALLOWED_PUNCTUATION

    if column_type == "date":
        return _is_digit(char) or char in {"-", "/", " "}

    return _is_letter(char) or _is_digit(char) or char in DEFAULT_ALLOWED_PUNCTUATION


def _analyze_value(value: str, column_type: str) -> tuple[list[str], list[str]]:
    suspicious_chars: list[str] = []
    emojis: list[str] = []

    for char in value:
        if _contains_emoji(char):
            emojis.append(char)
            continue
        if not _is_allowed_char(char, column_type):
            suspicious_chars.append(char)

    return suspicious_chars, emojis


def detect_special_chars(df: pd.DataFrame):
    results = []

    for col in df.columns:
        series = df[col].dropna().astype(str).str.strip()
        column_type = _infer_special_char_column_type(col, series)

        special_chars: list[str] = []
        emojis: list[str] = []
        affected_rows = 0

        if column_type not in SKIP_COLUMN_TYPES:
            for value in series.head(5000):
                found_special, found_emojis = _analyze_value(value, column_type)
                if found_special or found_emojis:
                    affected_rows += 1
                special_chars.extend(found_special)
                emojis.extend(found_emojis)

        scanned_rows = int(len(series.head(5000)))
        results.append(
            {
                "column": str(col),
                "column_type": column_type,
                "special_char_count": len(special_chars),
                "emoji_count": len(emojis),
                "affected_rows": affected_rows,
                "affected_percentage": round((affected_rows / scanned_rows) * 100, 1)
                if scanned_rows
                else 0.0,
                "unique_special_chars": sorted(set(special_chars))[:10],
                "unique_emojis": sorted(set(emojis))[:10],
            }
        )

    return pd.DataFrame(results)
