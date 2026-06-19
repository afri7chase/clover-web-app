import streamlit as st


def _render_card(
    title: str,
    value: str,
    tone: str,
    icon: str,
    status: str | None,
    note: str | None = None,
    value_suffix: str | None = None,
    card_class: str | None = None,
) -> None:
    note_html = (
        f'<div class="clover-kpi-note">{note}</div>'
        if note
        else ""
    )
    status_html = (
        f'<div class="clover-kpi-status">{status}</div>'
        if status
        else ""
    )
    suffix_html = (
        f'<span class="clover-kpi-value-suffix">{value_suffix}</span>'
        if value_suffix
        else ""
    )
    classes = " ".join(
        part for part in ["clover-kpi-card", f"clover-tone-{tone}", f"clover-kpi-{tone}", card_class] if part
    )
    card_html = f"""
        <div class="{classes}">
            <div class="clover-kpi-shell">
                <div class="clover-kpi-icon">{icon}</div>
                <div class="clover-kpi-copy">
                    <div class="clover-kpi-title">{title}</div>
                    <div class="clover-kpi-value">{value}{suffix_html}</div>
                    {status_html}
                    {note_html}
                </div>
            </div>
        </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_kpi_cards(metrics: dict, quality_score: float, quality_status: dict) -> None:
    """Render the dashboard's KPI summary cards."""
    missing_tone = "warning" if metrics["missing_values"] > 0 else "good"
    duplicate_tone = "danger" if metrics["duplicate_rows"] > 0 else "good"
    quality_tone = "quality"
    valid_records = metrics.get("valid_records", 0)
    valid_tone = "good" if valid_records > 0 else "warning"

    columns = st.columns(6, gap="small")
    card_values = [
        {
            "title": "Quality Score",
            "value": f"{quality_score:.1f}",
            "tone": quality_tone,
            "icon": "&#9681;",
            "status": quality_status["label"].upper(),
            "note": "Overall dataset quality",
            "value_suffix": "%",
        },
        {
            "title": "Total Rows",
            "value": f"{metrics['total_rows']:,}",
            "tone": "teal",
            "icon": "&#9635;",
            "status": "RECORDS",
            "note": "Rows profiled in this run",
        },
        {
            "title": "Total Columns",
            "value": f"{metrics['total_columns']:,}",
            "tone": "purple",
            "icon": "&#9638;",
            "status": "FIELDS",
            "note": "Columns detected in schema",
        },
        {
            "title": "Missing Values",
            "value": f"{metrics['missing_values']:,}",
            "tone": missing_tone,
            "icon": "&#9888;",
            "status": "REVIEW" if metrics["missing_values"] > 0 else "CLEAR",
            "note": "Null or blank cells",
        },
        {
            "title": "Duplicate Rows",
            "value": f"{metrics['duplicate_rows']:,}",
            "tone": duplicate_tone,
            "icon": "&#10697;",
            "status": "ACTION" if metrics["duplicate_rows"] > 0 else "CLEAR",
            "note": "Repeated records found",
        },
        {
            "title": "Valid Records",
            "value": f"{valid_records:,}",
            "tone": valid_tone,
            "icon": "&#10003;",
            "status": "GOOD" if valid_records > 0 else "PENDING",
            "note": "Records passing baseline checks",
        },
    ]

    for column, card in zip(columns, card_values):
        with column:
            _render_card(**card)


def render_duplicate_summary_cards(duplicate_summary: dict, total_rows: int) -> None:
    """Render duplicate-analysis summary cards using the shared KPI styling."""
    exact_duplicate_rows = int(duplicate_summary.get("exact_duplicates_count", 0))
    email_duplicate_rows = int(duplicate_summary.get("email_duplicates_count", 0))
    duplicate_ratio = float(duplicate_summary.get("exact_duplicates_pct", 0.0))

    exact_tone = "danger" if exact_duplicate_rows > 0 else "good"
    email_tone = "warning" if email_duplicate_rows > 0 else "good"
    ratio_tone = "danger" if duplicate_ratio >= 10 else "warning" if duplicate_ratio > 0 else "good"

    card_values = [
        {
            "title": "Exact Duplicate Rows",
            "value": f"{exact_duplicate_rows:,}",
            "tone": exact_tone,
            "icon": "&#10697;",
            "status": "ACTION" if exact_duplicate_rows > 0 else "CLEAR",
            "note": "Rows matched exactly",
            "card_class": "clover-kpi-duplicate-summary",
        },
        {
            "title": "Email Duplicate Rows",
            "value": f"{email_duplicate_rows:,}",
            "tone": email_tone,
            "icon": "&#9993;",
            "status": "REVIEW" if email_duplicate_rows > 0 else "CLEAR",
            "note": "Duplicate email values",
            "card_class": "clover-kpi-duplicate-summary",
        },
        {
            "title": "Total Rows",
            "value": f"{total_rows:,}",
            "tone": "teal",
            "icon": "&#9635;",
            "status": "RECORDS",
            "note": "Rows evaluated",
            "card_class": "clover-kpi-duplicate-summary",
        },
        {
            "title": "Duplicate Ratio",
            "value": f"{duplicate_ratio:.1f}",
            "tone": ratio_tone,
            "icon": "&#9681;",
            "status": "IMPACT" if duplicate_ratio > 0 else "CLEAR",
            "note": "Duplicate impact",
            "value_suffix": "%",
            "card_class": "clover-kpi-duplicate-summary",
        },
    ]

    first_row = st.columns(2, gap="medium")
    for column, card in zip(first_row, card_values[:2]):
        with column:
            _render_card(**card)

    second_row = st.columns(2, gap="medium")
    for column, card in zip(second_row, card_values[2:]):
        with column:
            _render_card(**card)


def render_validation_summary_cards(validation_overview: dict) -> None:
    """Render validation-summary cards using the shared KPI styling."""
    total_checked = int(validation_overview.get("total_checked", 0))
    valid_count = int(validation_overview.get("valid_count", 0))
    invalid_count = int(validation_overview.get("invalid_count", 0))
    invalid_rate = float(validation_overview.get("invalid_percentage", 0.0))

    invalid_tone = "danger" if invalid_count > 0 else "good"
    rate_tone = "danger" if invalid_rate >= 15 else "warning" if invalid_rate > 0 else "good"
    valid_tone = "good" if valid_count > 0 else "warning"

    card_values = [
        {
            "title": "Values Checked",
            "value": f"{total_checked:,}",
            "tone": "teal",
            "icon": "&#9635;",
            "status": "CHECKED",
            "note": "Validated non-empty values",
            "card_class": "clover-kpi-duplicate-summary",
        },
        {
            "title": "Invalid Values",
            "value": f"{invalid_count:,}",
            "tone": invalid_tone,
            "icon": "&#9888;",
            "status": "REVIEW" if invalid_count > 0 else "CLEAR",
            "note": "Values failing format rules",
            "card_class": "clover-kpi-duplicate-summary",
        },
        {
            "title": "Valid Values",
            "value": f"{valid_count:,}",
            "tone": valid_tone,
            "icon": "&#10003;",
            "status": "PASS" if valid_count > 0 else "PENDING",
            "note": "Values passing checks",
            "card_class": "clover-kpi-duplicate-summary",
        },
        {
            "title": "Invalid Rate",
            "value": f"{invalid_rate:.1f}",
            "tone": rate_tone,
            "icon": "&#9681;",
            "status": "RISK" if invalid_rate > 0 else "CLEAR",
            "note": "Share of invalid values",
            "value_suffix": "%",
            "card_class": "clover-kpi-duplicate-summary",
        },
    ]

    first_row = st.columns(2, gap="medium")
    for column, card in zip(first_row, card_values[:2]):
        with column:
            _render_card(**card)

    second_row = st.columns(2, gap="medium")
    for column, card in zip(second_row, card_values[2:]):
        with column:
            _render_card(**card)


def render_top_issues_panel(issues: list[dict]) -> None:
    """Render the prioritized issue summary panel."""
    issue_items = []
    for issue in issues:
        issue_items.append(
            (
                f'<div class="clover-issue-item clover-issue-{issue["severity"]}">'
                f'<div class="clover-issue-icon">{issue["icon"]}</div>'
                '<div class="clover-issue-copy">'
                f'<div class="clover-issue-title">{issue["title"]}</div>'
                f'<div class="clover-issue-message">{issue["message"]}</div>'
                "</div>"
                "</div>"
            )
        )

    panel_html = (
        '<div class="clover-panel">'
        '<div class="clover-panel-header">'
        '<div>'
        '<div class="clover-section-title">Top Issues Found</div>'
        '<div class="clover-section-subtitle">The most important quality signals surfaced automatically from the uploaded dataset.</div>'
        "</div>"
        "</div>"
        f'<div class="clover-issue-list">{"".join(issue_items)}</div>'
        "</div>"
    )

    if hasattr(st, "html"):
        st.html(panel_html)
    else:
        st.markdown(panel_html, unsafe_allow_html=True)
