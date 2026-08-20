from __future__ import annotations

import html
import sys
from io import BytesIO
from pathlib import Path

import pandas as pd

from utils.validation_config import VALIDATION_ORDER


def _add_reportlab_fallback_paths() -> None:
    project_root = Path(__file__).resolve().parents[1]
    fallback_paths = [
        project_root / ".venv" / "Lib" / "site-packages",
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "python",
    ]

    for fallback_path in fallback_paths:
        if fallback_path.exists():
            fallback_str = str(fallback_path)
            if fallback_str not in sys.path:
                sys.path.append(fallback_str)


def _load_reportlab_dependencies() -> dict:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import (
            KeepTogether,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        _add_reportlab_fallback_paths()
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import (
            KeepTogether,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

    return {
        "A4": A4,
        "Canvas": Canvas,
        "KeepTogether": KeepTogether,
        "Paragraph": Paragraph,
        "ParagraphStyle": ParagraphStyle,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
        "TA_CENTER": TA_CENTER,
        "TA_LEFT": TA_LEFT,
        "colors": colors,
        "getSampleStyleSheet": getSampleStyleSheet,
    }


def build_quality_report_pdf_bytes(
    dataset_info: dict,
    metrics: dict,
    quality_score: float,
    top_issues: list[dict],
    column_risk_ranking: pd.DataFrame,
) -> bytes:
    pdf = _load_reportlab_dependencies()
    A4 = pdf["A4"]
    Canvas = pdf["Canvas"]
    KeepTogether = pdf["KeepTogether"]
    Paragraph = pdf["Paragraph"]
    ParagraphStyle = pdf["ParagraphStyle"]
    SimpleDocTemplate = pdf["SimpleDocTemplate"]
    Spacer = pdf["Spacer"]
    Table = pdf["Table"]
    TableStyle = pdf["TableStyle"]
    TA_CENTER = pdf["TA_CENTER"]
    TA_LEFT = pdf["TA_LEFT"]
    colors = pdf["colors"]
    getSampleStyleSheet = pdf["getSampleStyleSheet"]

    validation_results = metrics.get("validation_results", {})
    duplicate_summary = metrics.get("duplicate_summary", {})
    special_character_columns = metrics.get("special_character_columns", pd.DataFrame())
    missing_by_column = metrics.get("missing_by_column", pd.DataFrame())

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CloverTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#132238"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CloverSection",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#132238"),
            spaceBefore=6,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CloverBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#24364d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CloverMeta",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#516983"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CloverCentered",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#516983"),
        )
    )

    section_fill = colors.HexColor("#EAF3FF")
    header_fill = colors.HexColor("#132238")
    header_text = colors.whitesmoke
    border_color = colors.HexColor("#A8BED6")
    row_fill = colors.HexColor("#F7FAFD")
    alt_row_fill = colors.HexColor("#EEF4FA")

    def paragraph(text: str, style_name: str = "CloverBody"):
        return Paragraph(html.escape(str(text)), styles[style_name])

    def section_heading(title: str) -> list:
        return [
            Table(
                [[paragraph(title, "CloverSection")]],
                colWidths=[510],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), section_fill),
                        ("BOX", (0, 0), (-1, -1), 0.8, border_color),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                ),
            ),
            Spacer(1, 8),
        ]

    def zebra_table(data: list[list], col_widths: list[float], repeat_rows: int = 1):
        table = Table(data, colWidths=col_widths, repeatRows=repeat_rows)
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), header_fill),
            ("TEXTCOLOR", (0, 0), (-1, 0), header_text),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
            ("TOPPADDING", (0, 0), (-1, 0), 7),
            ("GRID", (0, 0), (-1, -1), 0.6, border_color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ]
        for row_index in range(1, len(data)):
            style_commands.append(
                (
                    "BACKGROUND",
                    (0, row_index),
                    (-1, row_index),
                    row_fill if row_index % 2 else alt_row_fill,
                )
            )
        table.setStyle(TableStyle(style_commands))
        return table

    def recommendation_lines() -> list[str]:
        recommendations = []
        if metrics.get("validation_overview", {}).get("invalid_count", 0) > 0:
            if validation_results.get("dob", {}).get("invalid_count", 0) > 0:
                recommendations.append("Clean invalid dates.")
            if validation_results.get("email", {}).get("invalid_count", 0) > 0:
                recommendations.append("Review invalid email addresses.")
            if validation_results.get("phone", {}).get("invalid_count", 0) > 0:
                recommendations.append("Standardize invalid phone numbers.")
            if validation_results.get("name", {}).get("invalid_count", 0) > 0:
                recommendations.append("Correct invalid name values.")
            if validation_results.get("username", {}).get("invalid_count", 0) > 0:
                recommendations.append("Correct invalid username values.")
        if metrics.get("duplicate_rows", 0) > 0:
            recommendations.append("Remove duplicate rows.")
        if int(duplicate_summary.get("email_duplicates_count", 0)) > 0:
            recommendations.append("Review duplicate email records.")
        if metrics.get("missing_values", 0) > 0:
            recommendations.append("Review missing values in the most affected columns.")
        if metrics.get("special_character_total", 0) > 0:
            recommendations.append("Standardize special characters and emojis where unexpected.")
        if not metrics.get("low_uniqueness_columns", pd.DataFrame()).empty:
            recommendations.append("Review low uniqueness columns for duplicate-value risk.")
        if not recommendations:
            recommendations.append("Maintain the current data quality controls and monitoring.")
        return recommendations

    class NumberedCanvas(Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_footer(total_pages)
                super().showPage()
            super().save()

        def draw_footer(self, total_pages: int):
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#516983"))
            self.drawString(42, 24, "Generated by Clover")
            self.drawString(42, 14, "Dataset Quality Assessment Dashboard")
            self.drawRightString(553, 19, f"Page {self._pageNumber} of {total_pages}")

    story = []
    story.append(paragraph("Clover", "CloverSection"))
    story.append(paragraph("Clover Dataset Quality Assessment Report", "CloverTitle"))
    story.append(
        Table(
            [
                [
                    paragraph(
                        f"Dataset Name: {dataset_info.get('file_name', 'No dataset loaded')}",
                        "CloverMeta",
                    ),
                    paragraph(
                        f"Generated: {dataset_info.get('last_analyzed', 'Not analyzed')}",
                        "CloverMeta",
                    ),
                ],
                [
                    paragraph(
                        "Analysis Version: Clover Dashboard",
                        "CloverMeta",
                    ),
                    paragraph(
                        f"Quality Status: {metrics.get('quality_status_raw', 'FAIL')}",
                        "CloverMeta",
                    ),
                ],
            ],
            colWidths=[255, 255],
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, border_color),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    story.append(Spacer(1, 12))

    story.extend(section_heading("Executive Summary"))
    summary_table = zebra_table(
        [
            ["Metric", "Value", "Metric", "Value"],
            ["Overall Quality Score", f"{quality_score:.1f}/100", "Total Rows", f"{metrics.get('total_rows', 0):,}"],
            ["Total Columns", f"{metrics.get('total_columns', 0):,}", "Missing Values", f"{metrics.get('missing_values', 0):,}"],
            ["Duplicate Rows", f"{metrics.get('duplicate_rows', 0):,}", "Valid Records", f"{metrics.get('valid_records', 0):,}"],
        ],
        [150, 105, 150, 105],
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    story.extend(section_heading("Top Issues Found"))
    issues_data = [["Issue", "Details"]]
    if top_issues:
        for issue in top_issues:
            issues_data.append(
                [
                    paragraph(issue.get("title", "Issue")),
                    paragraph(issue.get("message", "")),
                ]
            )
    else:
        issues_data.append(
            [
                paragraph("No major issues detected."),
                paragraph("The current dataset does not have major issues in the tracked Clover checks."),
            ]
        )
    story.append(zebra_table(issues_data, [150, 360]))
    story.append(Spacer(1, 10))

    story.extend(section_heading("Validation Summary"))
    validation_data = [["Validation Check", "Valid Count", "Invalid Count", "Valid Percentage"]]
    for key in VALIDATION_ORDER:
        result = validation_results.get(key, {})
        validation_data.append(
            [
                result.get("label", key.title()),
                f"{int(result.get('valid_count', 0)):,}",
                f"{int(result.get('invalid_count', 0)):,}",
                f"{float(result.get('valid_percentage', 0.0)):.1f}%",
            ]
        )
    story.append(zebra_table(validation_data, [185, 95, 95, 135]))
    story.append(Spacer(1, 10))

    story.extend(section_heading("Duplicate Analysis"))
    duplicate_ratio = float(duplicate_summary.get("exact_duplicates_pct", 0.0))
    duplicate_data = [
        ["Metric", "Value"],
        ["Exact Duplicate Rows", f"{int(duplicate_summary.get('exact_duplicates_count', 0)):,}"],
        ["Duplicate Emails", f"{int(duplicate_summary.get('email_duplicates_count', 0)):,}"],
        ["Duplicate Ratio", f"{duplicate_ratio:.1f}%"],
    ]
    story.append(zebra_table(duplicate_data, [255, 255]))
    story.append(Spacer(1, 10))

    missing_section = []
    missing_section.extend(section_heading("Missing Values"))
    top_missing = (
        missing_by_column[missing_by_column["column"] != "No data loaded"].head(5)
        if isinstance(missing_by_column, pd.DataFrame)
        else pd.DataFrame()
    )
    missing_data = [["Metric", "Value"], ["Total Missing Values", f"{metrics.get('missing_values', 0):,}"]]
    missing_section.append(zebra_table(missing_data, [255, 255]))
    missing_section.append(Spacer(1, 6))
    if not top_missing.empty:
        top_missing_data = [["Top Affected Column", "Missing Values"]]
        for row in top_missing.itertuples(index=False):
            top_missing_data.append([str(row.column), f"{int(row.missing_values):,}"])
        missing_section.append(zebra_table(top_missing_data, [350, 160]))
    else:
        missing_section.append(paragraph("No missing-value analysis available."))
    missing_section.append(Spacer(1, 10))
    story.append(KeepTogether(missing_section))

    story.extend(section_heading("Special Characters"))
    special_summary_data = [
        ["Metric", "Value"],
        ["Columns Containing Special Characters", f"{len(special_character_columns):,}"],
        ["Flagged Character Rows", f"{int(metrics.get('special_character_total', 0)):,}"],
    ]
    story.append(zebra_table(special_summary_data, [255, 255]))
    story.append(Spacer(1, 6))
    if isinstance(special_character_columns, pd.DataFrame) and not special_character_columns.empty:
        special_data = [["Column", "Type", "Affected Rows", "Special Chars", "Emojis"]]
        for row in special_character_columns.head(10).itertuples(index=False):
            special_data.append(
                [
                    str(row.column),
                    str(row.column_type),
                    f"{int(row.affected_rows):,}",
                    f"{int(row.special_char_count):,}",
                    f"{int(row.emoji_count):,}",
                ]
            )
        story.append(zebra_table(special_data, [145, 95, 95, 90, 85]))
    else:
        story.append(paragraph("No special or unexpected character issues detected."))
    story.append(Spacer(1, 10))

    story.extend(section_heading("Column Risk Ranking"))
    if column_risk_ranking.empty:
        story.append(paragraph("No column risk analysis available."))
    else:
        risk_data = [["Rank", "Column", "Risk Level", "Primary Issue", "Risk Score"]]
        for row in column_risk_ranking.itertuples(index=False):
            risk_data.append(
                [
                    str(int(row.rank)),
                    str(row.column),
                    str(row.risk_level),
                    str(row.primary_issue),
                    str(int(row.risk_score)),
                ]
            )
        story.append(zebra_table(risk_data, [45, 170, 90, 135, 70]))
    story.append(Spacer(1, 10))

    recommendations_section = []
    recommendations_section.extend(section_heading("Recommendations"))
    for recommendation in recommendation_lines():
        recommendations_section.append(paragraph(f"- {recommendation}"))
        recommendations_section.append(Spacer(1, 3))
    story.append(KeepTogether(recommendations_section))

    pdf_buffer = BytesIO()
    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=36,
        bottomMargin=36,
    )
    document.build(story, canvasmaker=NumberedCanvas)
    return pdf_buffer.getvalue()
