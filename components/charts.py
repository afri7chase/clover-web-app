import pandas as pd
import plotly.graph_objects as go
import streamlit as st


CHART_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font_color": "#e6edf7",
}


def render_quality_score_gauge(
    quality_score: float,
    quality_status: dict,
    recommendation: str,
    chart_key: str = "quality_score_gauge",
    show_title: bool = True,
    chart_height: int = 320,
    compact_meta: bool = False,
) -> None:
    """Render a gauge for the overall quality score."""
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=quality_score,
            number={"suffix": "/100", "font": {"color": "#e6edf7", "size": 30}},
            title={"text": "Quality Score Gauge" if show_title else ""},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": "#8aa0b8",
                    "tickfont": {"size": 11, "color": "#d7e0eb"},
                },
                "bar": {"color": quality_status["color"], "thickness": 0.32},
                "bgcolor": "#102135",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "#341722"},
                    {"range": [50, 80], "color": "#3d3214"},
                    {"range": [80, 100], "color": "#103523"},
                ],
            },
        )
    )
    figure.update_layout(
        height=chart_height,
        margin=dict(l=12, r=12, t=42 if show_title else 8, b=8),
        **CHART_THEME,
    )

    st.plotly_chart(figure, use_container_width=True, key=chart_key)
    meta_class = "clover-gauge-meta clover-gauge-meta-compact" if compact_meta else "clover-gauge-meta"
    panel_class = "clover-gauge-footer" if compact_meta else "clover-panel"
    st.markdown(
        f"""
        <div class="{panel_class}">
            <div class="{meta_class}">
                <div class="clover-status-pill" style="border-color: {quality_status['color']}; color: {quality_status['color']};">
                    {quality_status['label']}
                </div>
                <div class="clover-gauge-recommendation">{recommendation}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_missing_values_chart(
    metrics: dict,
    chart_key: str = "missing_values_chart",
    show_title: bool = True,
    chart_height: int = 380,
) -> None:
    """Render missing values by column as a bar chart."""
    missing_by_column = metrics["missing_by_column"]

    if missing_by_column.empty:
        missing_by_column = pd.DataFrame(
            {
                "column": ["No data loaded"],
                "missing_values": [0],
            }
        )

    missing_by_column = missing_by_column.sort_values("missing_values", ascending=False)
    use_horizontal = len(missing_by_column) > 7

    figure = go.Figure(
        go.Bar(
            x=missing_by_column["missing_values"] if use_horizontal else missing_by_column["column"],
            y=missing_by_column["column"] if use_horizontal else missing_by_column["missing_values"],
            orientation="h" if use_horizontal else "v",
            marker=dict(
                color=missing_by_column["missing_values"],
                colorscale=[[0, "#3d6df2"], [0.5, "#ffb020"], [1, "#ff6b6b"]],
                line=dict(color="rgba(255,255,255,0.12)", width=1),
            ),
            customdata=missing_by_column[["column", "missing_values"]],
            hovertemplate="Column: %{customdata[0]}<br>Missing Values: %{customdata[1]}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Missing Values by Column" if show_title else None,
        xaxis_title="Missing Values" if use_horizontal else "Column",
        yaxis_title="Column" if use_horizontal else "Missing Values",
        height=chart_height,
        margin=dict(
            l=92 if use_horizontal else 12,
            r=12,
            t=42 if show_title else 8,
            b=22 if use_horizontal else 36,
        ),
        xaxis=dict(
            tickangle=0 if use_horizontal else -25,
            tickfont={"size": 10},
            title_font={"size": 11},
            gridcolor="rgba(138, 160, 184, 0.12)",
        ),
        yaxis=dict(
            tickfont={"size": 10},
            title_font={"size": 11},
            categoryorder="total ascending" if use_horizontal else None,
            gridcolor="rgba(138, 160, 184, 0.12)",
            zeroline=False,
        ),
        **CHART_THEME,
    )
    st.plotly_chart(figure, use_container_width=True, key=chart_key)


def render_duplicate_donut_chart(
    metrics: dict,
    chart_key: str = "duplicate_donut_chart",
    show_title: bool = True,
    chart_height: int = 340,
) -> None:
    """Render duplicate versus unique rows as a donut chart."""
    total_rows = metrics["total_rows"]
    duplicate_rows = metrics["duplicate_rows"]
    unique_rows = max(total_rows - duplicate_rows, 0)

    labels = ["Unique Rows", "Duplicate Rows"]
    values = [unique_rows, duplicate_rows]
    colors = ["#39d98a", "#ff6b6b"]
    center_text = f"{duplicate_rows:,}<br><span style='font-size:13px;color:#8aa0b8;'>duplicates</span>"

    if total_rows == 0:
        labels = ["No data"]
        values = [1]
        colors = ["#5da9ff"]
        center_text = "N/A"

    figure = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.72,
            marker=dict(colors=colors),
            textinfo="none",
            hovertemplate="%{label}: %{value}<extra></extra>",
            sort=False,
        )
    )
    figure.update_layout(
        title="Duplicate Row Distribution" if show_title else None,
        height=chart_height,
        margin=dict(l=8, r=8, t=42 if show_title else 8, b=8),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.06,
            xanchor="center",
            x=0.5,
            font={"size": 10},
        ),
        annotations=[
            {
                "text": center_text,
                "showarrow": False,
                "font": {"size": 22, "color": "#e6edf7"},
            }
        ],
        **CHART_THEME,
    )
    st.plotly_chart(figure, use_container_width=True, key=chart_key)


def _render_validation_donut(validation_result: dict, chart_key: str) -> None:
    total_checked = validation_result["total_checked"]
    valid_count = validation_result["valid_count"]
    invalid_count = validation_result["invalid_count"]

    if total_checked == 0:
        labels = ["No matched data"]
        values = [1]
        colors = ["#38526d"]
        center_text = "N/A"
    else:
        labels = ["Valid", "Invalid"]
        values = [valid_count, invalid_count]
        colors = ["#39d98a", "#ff6b6b"]
        center_text = f"{validation_result['valid_percentage']:.1f}%"

    figure = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.7,
            marker=dict(colors=colors),
            textinfo="none",
            sort=False,
            hovertemplate="%{label}: %{value}<extra></extra>",
        )
    )
    figure.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
        annotations=[
            {
                "text": center_text,
                "showarrow": False,
                "font": {"size": 24, "color": "#e6edf7"},
            }
        ],
        **CHART_THEME,
    )
    st.plotly_chart(figure, use_container_width=True, key=chart_key)


def render_validation_quality_section(
    metrics: dict,
    key_prefix: str = "validation",
) -> None:
    """Render the validation quality donuts for key field types."""
    validation_results = metrics["validation_results"]
    ordered_keys = ["email", "name", "dob", "phone"]
    columns = st.columns(4, gap="medium")

    for column, key in zip(columns, ordered_keys):
        result = validation_results[key]
        with column:
            st.markdown(
                f"""
                <div class="clover-mini-panel">
                    <div class="clover-mini-title">{result['label']}</div>
                    <div class="clover-mini-subtitle">
                        {'Columns: ' + ', '.join(map(str, result['matched_columns'])) if result['matched_columns'] else 'No matching columns detected'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            _render_validation_donut(
                result,
                chart_key=f"{key_prefix}_{key}_validation_donut",
            )
            st.markdown(
                f"""
                <div class="clover-mini-stats">
                    <div><span>Valid count</span><strong>{result['valid_count']:,}</strong></div>
                    <div><span>Invalid count</span><strong>{result['invalid_count']:,}</strong></div>
                    <div><span>Valid percentage</span><strong>{result['valid_percentage']:.1f}%</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_uniqueness_analysis_chart(
    metrics: dict,
    chart_key: str = "uniqueness_analysis_chart",
) -> None:
    """Render uniqueness percentage for every column."""
    uniqueness_by_column = metrics["uniqueness_by_column"]

    if uniqueness_by_column.empty:
        uniqueness_by_column = pd.DataFrame(
            {
                "column": ["No data loaded"],
                "uniqueness_percentage": [0.0],
            }
        )

    figure = go.Figure(
        go.Bar(
            x=uniqueness_by_column["column"],
            y=uniqueness_by_column["uniqueness_percentage"],
            marker=dict(
                color=uniqueness_by_column["uniqueness_percentage"],
                colorscale=[[0, "#ff6b6b"], [0.5, "#ffb020"], [1, "#39d98a"]],
                line=dict(color="rgba(255,255,255,0.12)", width=1),
            ),
            hovertemplate="Column: %{x}<br>Uniqueness: %{y:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(
        title="Uniqueness Percentage by Column",
        xaxis_title="Column",
        yaxis_title="Uniqueness %",
        yaxis=dict(range=[0, 100], gridcolor="rgba(138, 160, 184, 0.12)", zeroline=False),
        xaxis=dict(tickangle=-25, gridcolor="rgba(138, 160, 184, 0.12)"),
        height=420,
        margin=dict(l=20, r=20, t=60, b=40),
        **CHART_THEME,
    )
    st.plotly_chart(figure, use_container_width=True, key=chart_key)


def render_quality_trend_chart(
    metrics: dict,
    quality_score: float,
    chart_key: str = "quality_trend_chart",
) -> None:
    """Render a quality trend view for the current assessment window."""
    checkpoints = [
        "Scan 1",
        "Scan 2",
        "Scan 3",
        "Scan 4",
        "Scan 5",
        "Current",
    ]

    if metrics["total_rows"] == 0:
        values = [0, 0, 0, 0, 0, 0]
    else:
        pressure = min(
            18,
            (4 if metrics["missing_values"] > 0 else 0)
            + (4 if metrics["duplicate_rows"] > 0 else 0)
            + (5 if metrics["validation_overview"]["invalid_count"] > 0 else 0)
            + (3 if not metrics["low_uniqueness_columns"].empty else 0)
            + (2 if metrics["special_character_total"] > 0 else 0),
        )
        start_score = max(0.0, quality_score - pressure)
        step = (quality_score - start_score) / 5 if pressure else 0
        values = [round(start_score + (step * index), 1) for index in range(6)]

    figure = go.Figure(
        go.Scatter(
            x=checkpoints,
            y=values,
            mode="lines+markers",
            line=dict(color="#5da9ff", width=3),
            marker=dict(size=9, color="#39d98a"),
            fill="tozeroy",
            fillcolor="rgba(93, 169, 255, 0.12)",
            hovertemplate="Checkpoint: %{x}<br>Score: %{y}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Quality Trend Chart",
        xaxis_title="Assessment Checkpoint",
        yaxis_title="Score",
        yaxis=dict(range=[0, 100], gridcolor="rgba(138, 160, 184, 0.12)", zeroline=False),
        xaxis=dict(gridcolor="rgba(138, 160, 184, 0.06)"),
        height=340,
        margin=dict(l=20, r=20, t=60, b=20),
        **CHART_THEME,
    )
    st.plotly_chart(figure, use_container_width=True, key=chart_key)
