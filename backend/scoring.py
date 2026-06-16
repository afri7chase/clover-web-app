import numpy as np

def compute_quality_score(df, column_df, email_quality, field_quality, duplicate_summary):
    completeness = 1.0 - df.isna().mean().mean()

    uniqueness = (
        column_df["uniqueness_%"].mean() / 100
        if not column_df.empty else 0.0
    )

    email_score = 1.0
    if email_quality:
        scores = []
        for stats in email_quality.values():
            non_missing = stats["total"] - stats["missing"]
            if non_missing > 0:
                scores.append(stats["valid"] / non_missing)
        email_score = float(np.mean(scores))

    duplicate_penalty = min(
        duplicate_summary["exact_duplicates_count"] / len(df),
        0.2
    )

    invalid_penalty = np.mean([
        stats["invalid"] / stats["total"]
        for stats in field_quality.values()
    ]) if field_quality else 0

    return round(
        0.35 * completeness +
        0.25 * uniqueness +
        0.2 * email_score +
        0.1 * (1 - duplicate_penalty) +
        0.1 * (1 - invalid_penalty),
        3
    )

def quality_status(score):
    if score >= 1.00:
        return "PASS"
    elif score >= 0.75:
        return "WARN"
    return "FAIL"
