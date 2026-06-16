def generate_insights(results):
    insights = []

    if results["quality_score"] < 0.7:
        insights.append("High number of missing values detected.")

    if results["duplicate_summary"]["exact_duplicates_count"] > 0:
        insights.append("Dataset contains duplicate rows.")

    if results["email_quality"]:
        for col, stats in results["email_quality"].items():
            non_missing = stats["total"] - stats["missing"]
            if non_missing and stats["valid"] / non_missing < 0.8:
                insights.append(f"Low email validity in column '{col}'.")

    return insights