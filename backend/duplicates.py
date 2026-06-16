import pandas as pd

 
def detect_duplicates(df, email_quality):
    duplicate_tables = {}
    duplicate_summary = {}

    total_rows = len(df)

    # -------------------------
    # Exact duplicates
    # -------------------------
    exact = df[df.duplicated(keep=False)]
    exact_count = int(exact.shape[0])

    duplicate_tables["exact_duplicates"] = exact.head(50)
    duplicate_summary["exact_duplicates_count"] = exact_count
    duplicate_summary["exact_duplicates_pct"] = (
        (exact_count / total_rows) * 100 if total_rows > 0 else 0
    )

    # -------------------------
    # Email duplicates
    # -------------------------
    email_dupes = pd.DataFrame()

    for col in email_quality:
        dupes = df[df[col].duplicated(keep=False)]
        if not dupes.empty:
            email_dupes = dupes
            break

    email_count = int(email_dupes.shape[0])

    duplicate_tables["email_duplicates"] = email_dupes.head(50)
    duplicate_summary["email_duplicates_count"] = email_count
    duplicate_summary["email_duplicates_pct"] = (
        (email_count / total_rows) * 100 if total_rows > 0 else 0
    )

    return duplicate_tables, duplicate_summary