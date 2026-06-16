import streamlit as st


def _render_card(
    title: str,
    value: str,
    tone: str,
    icon: str,
    status: str,
    note: str | None = None,
    value_suffix: str | None = None,
) -> None:
    note_html = (
        f'<div class="clover-kpi-note">{note}</div>'
        if note
        else ""
    )
    suffix_html = (
        f'<span class="clover-kpi-value-suffix">{value_suffix}</span>'
        if value_suffix
        else ""
    )
    st.markdown(
        f"""
        <div class="clover-kpi-card clover-tone-{tone} clover-kpi-{tone}">
            <div class="clover-kpi-shell">
                <div class="clover-kpi-icon">{icon}</div>
                <div class="clover-kpi-copy">
                    <div class="clover-kpi-title">{title}</div>
                    <div class="clover-kpi-value">{value}{suffix_html}</div>
                    <div class="clover-kpi-status">{status}</div>
                    {note_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
