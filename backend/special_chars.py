import pandas as pd
import re

# Regex for special characters (excluding normal text)
SPECIAL_CHAR_REGEX = re.compile(r"[^A-Za-z0-9\s]")

# Simple emoji detection (unicode ranges)
EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "]+",
    flags=re.UNICODE,
)

def detect_special_chars(df: pd.DataFrame):
    results = []

    for col in df.columns:
        series = df[col].dropna().astype(str)

        special_chars = []
        emojis = []

        col_lower = col.lower()

        # ✅ Define allowed characters by column type
        allowed_chars = set()

        if "email" in col_lower:
            allowed_chars = {"@", "-", "_", "."}

        elif any(token in col_lower for token in ["address", "dob", "date"]):
            allowed_chars = {"/"}

        for value in series.head(5000):  # limit for performance
            found_special = SPECIAL_CHAR_REGEX.findall(value)
            found_emojis = EMOJI_REGEX.findall(value)

            # ✅ Remove allowed characters from "special" list
            filtered_special = [
                char for char in found_special if char not in allowed_chars
            ]

            special_chars.extend(filtered_special)
            emojis.extend(found_emojis)

        results.append({
            "column": col,
            "special_char_count": len(special_chars),
            "emoji_count": len(emojis),
            "unique_special_chars": list(set(special_chars))[:10],
            "unique_emojis": list(set(emojis))[:10],
        })

    return pd.DataFrame(results)
