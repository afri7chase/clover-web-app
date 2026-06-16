import re
import pandas as pd
from backend.detection import infer_column_type


NAME_REGEX = re.compile(r"^[A-Za-z ,.'-]+$")
FULL_NAME_REGEX = re.compile(r"^[A-Za-z]+(?: [A-Za-z]+)+$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def validate_pattern(values, regex):
    valid_mask = values.str.match(regex)

    return {
        "valid": int(valid_mask.sum()),
        "invalid": int((~valid_mask).sum()),
        "invalid_examples": values[~valid_mask].head(5).tolist(),
    }

def validate_fields(df: pd.DataFrame):
    email_quality = {}
    field_quality = {}

    for col in df.columns:
        series = df[col]
        values = series.dropna().astype(str)

        total = len(series)
        missing = int(series.isna().sum())

        # ✅ unified detection
        col_type = infer_column_type(series)

        # EMAIL handled separately
        if col_type == "email":
            result = validate_pattern(values, EMAIL_REGEX)
            result.update({"missing": missing, "total": total})
            email_quality[col] = result

        elif col_type == "phone":
            result = validate_pattern(values, PHONE_REGEX)
            result.update({"type": "phone", "missing": missing, "total": total})
            field_quality[col] = result

        elif col_type == "date_of_birth":
            result = validate_pattern(values, DATE_REGEX)
            result.update({"type": "date_of_birth", "missing": missing, "total": total})
            field_quality[col] = result
            
        elif col_type == "date":
            result = validate_pattern(values, DATE_REGEX)
            result.update({"type": "date", "missing": missing, "total": total})
            field_quality[col] = result

        elif col_type == "name":
            regex = FULL_NAME_REGEX if " " in values.head(1).to_string() else NAME_REGEX
            result = validate_pattern(values, regex)
            result.update({"type": "name", "missing": missing, "total": total})
            field_quality[col] = result

    return email_quality, field_quality