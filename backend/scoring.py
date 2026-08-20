import numpy as np


VALIDATION_WEIGHT = 0.45
DUPLICATE_WEIGHT = 0.25
COMPLETENESS_WEIGHT = 0.15
UNIQUENESS_WEIGHT = 0.10
UNEXPECTED_CHARACTER_WEIGHT = 0.05
LOW_UNIQUENESS_FLOOR = 0.25
LOW_UNIQUENESS_CAP = 0.50
EXACT_DUPLICATE_SHARE = 0.65
EMAIL_DUPLICATE_SHARE = 0.35
SCORING_TYPES = {"email", "phone", "date", "date_of_birth", "name", "username"}


def _clamp01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _checked_count(stats: dict) -> int:
    return int(stats.get("valid", 0)) + int(stats.get("invalid", 0))


def _compute_validation_quality(email_quality: dict, field_quality: dict) -> float:
    total_checked = 0
    total_valid = 0

    for stats in email_quality.values():
        checked = _checked_count(stats)
        total_checked += checked
        total_valid += int(stats.get("valid", 0))

    for stats in field_quality.values():
        if str(stats.get("type", "")).lower() not in SCORING_TYPES:
            continue
        checked = _checked_count(stats)
        total_checked += checked
        total_valid += int(stats.get("valid", 0))

    if total_checked == 0:
        return 1.0

    return _clamp01(total_valid / total_checked)


def _compute_duplicate_quality(total_rows: int, duplicate_summary: dict) -> float:
    if total_rows <= 0:
        return 1.0

    exact_ratio = int(duplicate_summary.get("exact_duplicates_count", 0)) / total_rows
    email_ratio = int(duplicate_summary.get("email_duplicates_count", 0)) / total_rows
    duplicate_ratio = (
        EXACT_DUPLICATE_SHARE * exact_ratio +
        EMAIL_DUPLICATE_SHARE * email_ratio
    )
    return _clamp01(1.0 - duplicate_ratio)


def _compute_completeness_quality(df) -> float:
    total_cells = int(df.shape[0] * df.shape[1])
    if total_cells == 0:
        return 1.0

    non_missing_cells = int(df.notna().sum().sum())
    return _clamp01(non_missing_cells / total_cells)


def _compute_uniqueness_quality(column_df) -> float:
    if column_df.empty or "uniqueness_%" not in column_df:
        return 1.0

    uniqueness = column_df["uniqueness_%"].fillna(100).astype(float) / 100.0
    low_uniqueness_penalty = ((LOW_UNIQUENESS_FLOOR - uniqueness) / LOW_UNIQUENESS_FLOOR).clip(lower=0.0, upper=1.0)
    average_penalty = float(low_uniqueness_penalty.mean()) if len(low_uniqueness_penalty) else 0.0
    return _clamp01(1.0 - (LOW_UNIQUENESS_CAP * average_penalty))


def _compute_unexpected_character_quality(special_chars_df) -> float:
    if special_chars_df is None or special_chars_df.empty or "affected_percentage" not in special_chars_df:
        return 1.0

    affected_ratio = special_chars_df["affected_percentage"].fillna(0).astype(float) / 100.0
    return _clamp01(1.0 - float(affected_ratio.mean()))


def compute_quality_components(
    df,
    column_df,
    email_quality,
    field_quality,
    duplicate_summary,
    special_chars_df,
) -> dict:
    total_rows = int(len(df))
    components = {
        "validation_quality": _compute_validation_quality(email_quality, field_quality),
        "duplicate_quality": _compute_duplicate_quality(total_rows, duplicate_summary),
        "completeness_quality": _compute_completeness_quality(df),
        "uniqueness_quality": _compute_uniqueness_quality(column_df),
        "unexpected_character_quality": _compute_unexpected_character_quality(special_chars_df),
    }
    return {name: _clamp01(score) for name, score in components.items()}


def compute_quality_score(
    df,
    column_df,
    email_quality,
    field_quality,
    duplicate_summary,
    special_chars_df,
):
    components = compute_quality_components(
        df,
        column_df,
        email_quality,
        field_quality,
        duplicate_summary,
        special_chars_df,
    )

    weighted_score = (
        VALIDATION_WEIGHT * components["validation_quality"] +
        DUPLICATE_WEIGHT * components["duplicate_quality"] +
        COMPLETENESS_WEIGHT * components["completeness_quality"] +
        UNIQUENESS_WEIGHT * components["uniqueness_quality"] +
        UNEXPECTED_CHARACTER_WEIGHT * components["unexpected_character_quality"]
    )
    return round(_clamp01(weighted_score), 3)


def quality_status(score):
    if score >= 1.00:
        return "PASS"
    elif score >= 0.75:
        return "WARN"
    return "FAIL"
