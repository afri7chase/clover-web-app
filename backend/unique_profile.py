from pathlib import Path
import pandas as pd

from backend.profiling import compute_missingness, profile_columns
from backend.validation import validate_fields
from backend.duplicates import detect_duplicates
from backend.scoring import compute_quality_score, quality_status
from backend.insights import generate_insights
from backend.special_chars import detect_special_chars
def unique_profile(csv_path: Path):
    df = pd.read_csv(csv_path)

    missingness = compute_missingness(df)
    column_df, potential_keys = profile_columns(df)

    email_quality, field_quality, validation_previews = validate_fields(df)

    duplicate_tables, duplicate_summary = detect_duplicates(
        df, email_quality
    )
    special_chars_df = detect_special_chars(df)

    quality_score = compute_quality_score(
        df,
        column_df,
        email_quality,
        field_quality,
        duplicate_summary,
    )

    status = quality_status(quality_score)

    results = {
        "missingness": missingness,
        "columns": column_df,
        "potential_keys": potential_keys,
        "email_quality": email_quality,
        "field_quality": field_quality,
        "validation_previews": validation_previews,
        "duplicate_tables": duplicate_tables,
        "duplicate_summary": duplicate_summary,
        "quality_score": quality_score,
        "quality_status": status,
        "special_characters": special_chars_df,
    }

    results["insights"] = generate_insights(results)
    
    return results
