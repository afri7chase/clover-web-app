def calculate_quality_score(metrics: dict) -> float:
    """Estimate an overall dataset quality score out of 100."""
    total_rows = metrics["total_rows"]
    total_columns = metrics["total_columns"]

    if total_rows == 0 or total_columns == 0:
        return 0.0

    total_cells = total_rows * total_columns
    missing_ratio = metrics["missing_values"] / total_cells if total_cells else 0.0
    duplicate_ratio = metrics["duplicate_rows"] / total_rows if total_rows else 0.0
    invalid_ratio = metrics["validation_overview"]["invalid_count"] / metrics["validation_overview"]["total_checked"] if metrics["validation_overview"]["total_checked"] else 0.0
    special_character_ratio = metrics["special_character_total"] / total_rows if total_rows else 0.0
    low_uniqueness_ratio = len(metrics["low_uniqueness_columns"]) / total_columns if total_columns else 0.0

    penalty = (
        (missing_ratio * 0.35)
        + (duplicate_ratio * 0.25)
        + (invalid_ratio * 0.25)
        + (special_character_ratio * 0.10)
        + (low_uniqueness_ratio * 0.05)
    )
    quality_score = max(0.0, min(100.0, (1 - penalty) * 100))

    return round(quality_score, 1)


def get_quality_status(quality_score: float) -> dict:
    """Map a score to a label and accent color."""
    if quality_score >= 85:
        return {"label": "Good", "color": "#39d98a"}
    if quality_score >= 70:
        return {"label": "Warning", "color": "#ffb020"}
    return {"label": "Poor", "color": "#ff6b6b"}


def get_quality_recommendation(quality_score: float, metrics: dict) -> str:
    """Return a short recommendation based on the current score and issues."""
    if metrics["total_rows"] == 0:
        return "Upload a dataset to generate targeted cleanup recommendations."

    if quality_score >= 85:
        if metrics["missing_values"] or metrics["validation_overview"]["invalid_count"]:
            return "Quality is strong overall. Clean the flagged fields to harden downstream analytics and activation workflows."
        return "Quality is in a healthy state. Maintain the current standards and monitor new uploads for drift."

    if quality_score >= 70:
        return "Prioritize missing values, invalid records, and duplicate cleanup before using this data in reporting or segmentation."

    return "This dataset needs remediation before broad operational use. Resolve validation failures, deduplicate records, and review low-uniqueness columns first."
