import pandas as pd

def compute_missingness(df: pd.DataFrame) -> pd.DataFrame:
    na_counts = df.isna().sum()
    na_pct = (df.isna().mean() * 100).round(2)

    return (
        pd.DataFrame({"na_count": na_counts, "missing_pct": na_pct})
        .sort_values("missing_pct", ascending=False)
    )

def profile_columns(df: pd.DataFrame):
    profiles = []
    potential_keys = []

    for col in df.columns:
        series = df[col]

        total = len(series)
        missing = int(series.isna().sum())
        non_null = total - missing
        unique_non_null = int(series.nunique(dropna=True))

        uniqueness_pct = (
            (unique_non_null / non_null) * 100 if non_null > 0 else 0
        )

        is_key = non_null > 0 and missing == 0 and unique_non_null == non_null

        if is_key:
            potential_keys.append(col)

        profiles.append({
            "column": col,
            "dtype": str(series.dtype),
            # "total_rows": total,
            "missing": missing,
            "missing_%": round((missing / total) * 100, 2),
            "uniqueness_%": round(uniqueness_pct, 2),
            "Key": is_key,
        })

    return pd.DataFrame(profiles), potential_keys