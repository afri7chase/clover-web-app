import importlib
import html
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

import components.cards as cards_module
import components.charts as charts_module
import components.sidebar as sidebar_module
from backend.detection import (
    is_name_column_label,
    is_phone_column_label,
    is_username_column_label,
    normalize_column_label,
)
from backend.unique_profile import read_csv_preserve_strings, unique_profile
from utils.pdf_report import build_quality_report_pdf_bytes
from utils.validation_config import VALIDATION_BUCKETS, VALIDATION_ORDER

importlib.reload(cards_module)
importlib.reload(charts_module)
importlib.reload(sidebar_module)

render_kpi_cards = cards_module.render_kpi_cards
render_duplicate_summary_cards = cards_module.render_duplicate_summary_cards
render_validation_summary_cards = cards_module.render_validation_summary_cards
render_top_issues_panel = cards_module.render_top_issues_panel
render_duplicate_donut_chart = charts_module.render_duplicate_donut_chart
render_missing_values_chart = charts_module.render_missing_values_chart
render_quality_score_gauge = charts_module.render_quality_score_gauge
render_uniqueness_analysis_chart = charts_module.render_uniqueness_analysis_chart
render_validation_quality_section = charts_module.render_validation_quality_section
render_sidebar = sidebar_module.render_sidebar

LOW_UNIQUENESS_THRESHOLD = 25.0
QUALITY_STATUS_MAP = {
    "PASS": {"label": "Good", "color": "#39d98a"},
    "WARN": {"label": "Warning", "color": "#ffb020"},
    "FAIL": {"label": "Poor", "color": "#ff6b6b"},
}
ANALYSIS_STATUS_MESSAGES = {
    "idle": "Upload a CSV file to run dataset profiling and validation checks.",
    "running": "Analyzing dataset...",
    "complete": "All checks finished successfully.",
}


def apply_theme() -> None:
    """Apply the dashboard's dark visual system."""
    st.markdown(
        """
        <style>
            :root {
                --clover-bg: #07111f;
                --clover-panel: #0d1b2a;
                --clover-card: #132238;
                --clover-border: rgba(124, 156, 191, 0.16);
                --clover-border-strong: rgba(124, 156, 191, 0.28);
                --clover-text: #e6edf7;
                --clover-muted: #8aa0b8;
                --clover-accent: #39d98a;
                --clover-info: #5da9ff;
                --clover-warning: #ffb020;
                --clover-danger: #ff6b6b;
            }

            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(57, 217, 138, 0.12), transparent 22%),
                    radial-gradient(circle at bottom left, rgba(93, 169, 255, 0.10), transparent 18%),
                    linear-gradient(180deg, #07111f 0%, #050b14 100%);
                color: var(--clover-text);
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #081321 0%, #060d16 100%);
                border-right: 1px solid var(--clover-border);
            }

            [data-testid="stSidebar"][aria-expanded="true"] {
                min-width: 256px;
                max-width: 256px;
            }

            [data-testid="stSidebar"][aria-expanded="false"] {
                min-width: 0 !important;
                max-width: 0 !important;
                width: 0 !important;
                border-right: 0;
            }

            [data-testid="stAppViewContainer"] > .main,
            [data-testid="stAppViewContainer"] > section.main {
                width: 100%;
                max-width: 100%;
                margin-left: 0 !important;
                padding-left: 0 !important;
            }

            [data-testid="stAppViewContainer"] .main .block-container,
            [data-testid="stAppViewContainer"] section.main .block-container {
                max-width: 100%;
                margin-left: 0;
                margin-right: 0;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }

            [data-testid="stSidebar"] * {
                color: var(--clover-text);
            }

            [data-testid="stSidebar"] .block-container {
                padding-top: 0.4rem;
                padding-bottom: 0.4rem;
                padding-left: 0.64rem;
                padding-right: 0.64rem;
            }

            .clover-sidebar-brand {
                display: flex;
                align-items: center;
                gap: 0.66rem;
                padding: 0.05rem 0 0.24rem;
            }

            .clover-sidebar-brand-mark {
                width: 34px;
                height: 34px;
                min-width: 34px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(180deg, rgba(57, 217, 138, 0.26), rgba(57, 217, 138, 0.14));
                color: var(--clover-accent);
                font-size: 1.1rem;
                box-shadow: inset 0 0 0 1px rgba(57, 217, 138, 0.18);
            }

            .clover-sidebar-brand-name {
                font-size: 1.08rem;
                font-weight: 700;
                color: var(--clover-text);
                line-height: 1.02;
            }

            .clover-sidebar-brand-subtitle {
                margin-top: 0.04rem;
                font-size: 0.64rem;
                color: rgba(230, 237, 247, 0.74);
                line-height: 1.16;
            }

            .clover-sidebar-section-label {
                margin: 0.18rem 0 0.18rem;
                font-size: 0.62rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: rgba(138, 160, 184, 0.9);
            }

            div[class*="st-key-clover-nav-item-"],
            div[class*="st-key-clover-nav-active-"] {
                margin-bottom: 0.02rem;
            }

            div[class*="st-key-clover-nav-item-"] button,
            div[class*="st-key-clover-nav-active-"] button {
                width: 100%;
                display: flex;
                justify-content: flex-start;
                align-items: center;
                min-height: 2.34rem;
                padding: 0.24rem 0.88rem 0.24rem 0.92rem;
                border-radius: 12px;
                border: 1px solid transparent;
                background: transparent;
                color: rgba(230, 237, 247, 0.88);
                box-shadow: none;
                transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
            }

            div[class*="st-key-clover-nav-item-"] button > div,
            div[class*="st-key-clover-nav-active-"] button > div {
                width: 100%;
                display: flex;
                justify-content: flex-start;
                align-items: center;
                gap: 0.66rem;
            }

            div[class*="st-key-clover-nav-item-"] button svg,
            div[class*="st-key-clover-nav-active-"] button svg {
                width: 1.2rem;
                height: 1.2rem;
                min-width: 1.2rem;
                min-height: 1.2rem;
            }

            div[class*="st-key-clover-nav-item-"] button:hover,
            div[class*="st-key-clover-nav-active-"] button:hover {
                border-color: rgba(93, 169, 255, 0.24);
                background: linear-gradient(180deg, rgba(14, 46, 112, 0.34), rgba(9, 31, 79, 0.38));
            }

            div[class*="st-key-clover-nav-item-"] button p,
            div[class*="st-key-clover-nav-active-"] button p {
                margin: 0;
                width: 100%;
                text-align: left;
                white-space: nowrap;
                font-size: 0.81rem;
                font-weight: 700;
                line-height: 1.1;
            }

            div[class*="st-key-clover-nav-active-"] button {
                border-color: rgba(93, 169, 255, 0.38);
                background: linear-gradient(180deg, rgba(24, 79, 181, 0.92), rgba(12, 49, 126, 1));
                color: #f3f7fc;
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 8px 18px rgba(10, 29, 74, 0.22);
            }

            div[class*="st-key-clover-sidebar-upload-card"] {
                margin-top: 0.18rem;
                margin-bottom: 0.2rem;
                padding: 0.38rem 0.46rem 0.04rem;
                border: 1px solid var(--clover-border);
                border-radius: 12px;
                background: linear-gradient(180deg, rgba(14, 25, 41, 0.96), rgba(9, 17, 29, 0.99));
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploader"] {
                margin-top: 0.02rem;
                margin-bottom: -0.16rem;
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderDropzone"] {
                padding: 0.24rem 0.34rem;
                min-height: 0;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.02);
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderDropzone"] > div {
                gap: 0.22rem;
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderDropzoneInstructions"] {
                gap: 0.1rem;
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderDropzoneInstructions"] span,
            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderDropzoneInstructions"] small {
                font-size: 0.58rem;
                line-height: 1.1;
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderDropzoneInstructions"] small {
                display: none;
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stBaseButton-secondary"] {
                min-height: 1.6rem;
                padding: 0.08rem 0.5rem;
                border-radius: 9px;
                font-size: 0.64rem;
                font-weight: 700;
            }

            div[class*="st-key-clover-sidebar-upload-card"] [data-testid="stFileUploaderFile"] {
                display: none;
            }

            .clover-sidebar-card,
            .clover-sidebar-tip-card,
            .clover-sidebar-status-card {
                margin-top: 0.26rem;
                padding: 0.5rem 0.58rem;
                border-radius: 12px;
                border: 1px solid var(--clover-border);
                background: linear-gradient(180deg, rgba(14, 25, 41, 0.96), rgba(9, 17, 29, 0.99));
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
            }

            .clover-sidebar-card-title {
                font-size: 0.62rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: rgba(138, 160, 184, 0.92);
                margin-bottom: 0.3rem;
            }

            .clover-sidebar-metadata {
                display: grid;
                gap: 0.22rem;
            }

            .clover-sidebar-metadata div {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.45rem;
            }

            .clover-sidebar-metadata span {
                font-size: 0.68rem;
                color: rgba(138, 160, 184, 0.9);
            }

            .clover-sidebar-metadata strong {
                font-size: 0.69rem;
                font-weight: 700;
                color: var(--clover-text);
                text-align: right;
            }

            .clover-sidebar-status-card {
                margin-top: 0.24rem;
                padding: 0.42rem 0.52rem;
                border-color: var(--clover-border);
                background: linear-gradient(180deg, rgba(14, 25, 41, 0.96), rgba(9, 17, 29, 0.99));
            }

            .clover-sidebar-status-card.is-complete {
                border-top: 3px solid rgba(57, 217, 138, 0.72);
            }

            .clover-sidebar-status-card.is-running {
                border-top: 3px solid rgba(93, 169, 255, 0.7);
            }

            .clover-sidebar-status-card.is-error {
                border-top: 3px solid rgba(255, 107, 107, 0.78);
            }

            .clover-sidebar-status-title,
            .clover-sidebar-tip-title {
                font-size: 0.74rem;
                font-weight: 700;
                color: var(--clover-text);
                line-height: 1.15;
            }

            .clover-sidebar-status-title {
                display: flex;
                align-items: center;
                gap: 0.34rem;
                color: var(--clover-text);
            }

            .clover-sidebar-status-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1rem;
                height: 1rem;
                min-width: 1rem;
                border-radius: 999px;
                color: #98f2bd;
                background: rgba(57, 217, 138, 0.14);
                font-size: 0.68rem;
                line-height: 1;
            }

            .clover-sidebar-status-card.is-running .clover-sidebar-status-icon {
                color: #8cc6ff;
                background: rgba(93, 169, 255, 0.14);
            }

            .clover-sidebar-status-card.is-error .clover-sidebar-status-icon {
                color: #ffb0b0;
                background: rgba(255, 107, 107, 0.14);
            }

            .clover-sidebar-status-copy,
            .clover-sidebar-tip-copy {
                margin-top: 0.16rem;
                font-size: 0.68rem;
                line-height: 1.26;
                color: rgba(230, 237, 247, 0.72);
            }

            .clover-sidebar-status-copy {
                margin-top: 0.14rem;
            }

            .clover-sidebar-pending-card .clover-sidebar-card-title {
                margin-bottom: 0.1rem;
            }

            .clover-sidebar-tip-card {
                margin-top: 0.28rem;
            }

            .block-container {
                padding-top: 1.34rem;
                padding-bottom: 1.7rem;
                padding-left: 0.9rem;
                padding-right: 0.9rem;
            }

            div[class*="st-key-clover-top-header-shell"] {
                min-height: 5.2rem;
                padding: 1rem 0.88rem 0.9rem;
                border: 1px solid var(--clover-border);
                border-radius: 20px;
                background: linear-gradient(135deg, rgba(19, 34, 56, 0.96), rgba(9, 19, 32, 0.99));
                box-shadow: 0 18px 48px rgba(0, 0, 0, 0.2);
                margin-top: 0.2rem;
                margin-bottom: 0.48rem;
                overflow: visible;
            }

            div[class*="st-key-clover-top-header-shell"] > div[data-testid="stVerticalBlock"] {
                gap: 0;
            }

            div[class*="st-key-clover-top-header-shell"] [data-testid="stHorizontalBlock"] {
                align-items: center;
            }

            div[class*="st-key-clover-top-header-shell"] [data-testid="stColumn"] {
                display: flex;
                align-items: center;
            }

            div[class*="st-key-clover-top-header-shell"] [data-testid="stColumn"] > div {
                width: 100%;
            }

            .clover-header-grid {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.8rem;
                align-items: center;
            }

            .clover-header-copy h1 {
                margin: 0;
                font-size: 1.08rem;
                font-weight: 700;
                color: var(--clover-text);
                letter-spacing: 0.06em;
            }

            .clover-header-copy p {
                margin: 0.18rem 0 0;
                color: var(--clover-muted);
                font-size: 0.8rem;
                max-width: 38rem;
                line-height: 1.3;
            }

            div[class*="st-key-clover-header-dataset"] {
                min-width: 0;
                max-width: none;
                width: 100%;
                padding-top: 0.05rem;
            }

            div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] > div {
                min-height: 1.98rem;
                padding-right: 0.2rem;
                border-radius: 12px;
                border-color: rgba(124, 156, 191, 0.18);
                background: rgba(255, 255, 255, 0.04);
            }

            div[class*="st-key-clover-header-dataset"] [data-testid="stWidgetLabel"] {
                display: none;
            }

            div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] span {
                font-size: 0.76rem;
                font-weight: 600;
                color: var(--clover-text);
            }

            div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] {
                width: 100%;
            }

            div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] [title] {
                max-width: 100%;
            }

            div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] [title] > div,
            div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] [title] span {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .clover-header-chip {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                min-height: 1.82rem;
                padding: 0.3rem 0.54rem;
                border-radius: 12px;
                border: 1px solid rgba(124, 156, 191, 0.18);
                background: rgba(255, 255, 255, 0.04);
                color: var(--clover-text);
                font-size: 0.69rem;
                font-weight: 600;
                white-space: nowrap;
                flex: 0 0 auto;
            }

            div[class*="st-key-clover-header-controls-shell"] {
                width: 100%;
            }

            div[class*="st-key-clover-header-controls-shell"] [data-testid="stHorizontalBlock"] {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: flex-end;
                gap: 0.82rem;
                row-gap: 0.58rem;
            }

            div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"] {
                min-width: 0;
            }

            div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"]:first-child {
                flex: 1 1 360px !important;
                min-width: 300px;
            }

            div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"]:last-child {
                flex: 0 1 auto !important;
                min-width: max-content;
            }

            @media (max-width: 980px) {
                .clover-header-chip {
                    font-size: 0.66rem;
                    padding: 0.28rem 0.48rem;
                }

                .clover-risk-card {
                    padding: 0.82rem 0.82rem 0.76rem;
                }

                .clover-risk-head,
                .clover-risk-row {
                    grid-template-columns: 0.45fr 1.15fr 0.9fr 1fr;
                }

                .clover-risk-head div:last-child,
                .clover-risk-row div:last-child {
                    grid-column: 1 / -1;
                }

                div[class*="st-key-clover-header-controls-shell"] [data-testid="stHorizontalBlock"] {
                    justify-content: stretch;
                    gap: 0.68rem;
                }

                div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"]:first-child,
                div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"]:last-child {
                    flex: 1 1 100% !important;
                    min-width: 100%;
                }
            }

            @media (max-width: 1440px) {
                [data-testid="stSidebar"][aria-expanded="true"] {
                    min-width: 244px;
                    max-width: 244px;
                }

                [data-testid="stAppViewContainer"] .main .block-container,
                [data-testid="stAppViewContainer"] section.main .block-container,
                .block-container {
                    padding-top: 1.12rem;
                    padding-bottom: 1.42rem;
                    padding-left: 0.58rem;
                    padding-right: 0.58rem;
                }

                [data-testid="stSidebar"] .block-container {
                    padding-left: 0.56rem;
                    padding-right: 0.56rem;
                }

                div[class*="st-key-clover-nav-item-"] button,
                div[class*="st-key-clover-nav-active-"] button {
                    min-height: 2.18rem;
                    padding: 0.22rem 0.76rem 0.22rem 0.8rem;
                }

                div[class*="st-key-clover-nav-item-"] button p,
                div[class*="st-key-clover-nav-active-"] button p {
                    font-size: 0.78rem;
                }

                div[class*="st-key-clover-top-header-shell"] {
                    min-height: 4.95rem;
                    padding: 0.86rem 0.74rem 0.8rem;
                }

                .clover-header-grid {
                    gap: 0.72rem;
                }

                .clover-header-copy h1 {
                    font-size: 1rem;
                }

                .clover-header-copy p {
                    font-size: 0.76rem;
                }

                div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] > div {
                    min-height: 1.86rem;
                }

                div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] span {
                    font-size: 0.73rem;
                }

                .clover-header-chip {
                    min-height: 1.7rem;
                    padding: 0.26rem 0.48rem;
                    font-size: 0.66rem;
                }

                div[class*="st-key-clover-header-controls-shell"] [data-testid="stHorizontalBlock"] {
                    gap: 0.72rem;
                    row-gap: 0.52rem;
                }

                div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"]:first-child {
                    flex-basis: 340px !important;
                    min-width: 280px;
                }

                .clover-section-head {
                    margin: 1.24rem 0 0.66rem;
                }

                .clover-section-title {
                    font-size: 0.98rem;
                }

                .clover-section-subtitle {
                    font-size: 0.84rem;
                    line-height: 1.38;
                }

                .clover-kpi-card {
                    min-height: 90px;
                    padding: 0.56rem 0.62rem;
                }

                .clover-kpi-shell {
                    gap: 0.58rem;
                }

                .clover-kpi-icon {
                    width: 32px;
                    height: 32px;
                    min-width: 32px;
                    font-size: 0.92rem;
                }

                .clover-kpi-title {
                    font-size: 0.61rem;
                }

                .clover-kpi-value {
                    font-size: 1.42rem;
                }

                .clover-kpi-note,
                .clover-kpi-status {
                    font-size: 0.6rem;
                }

                .clover-kpi-duplicate-summary {
                    min-height: 126px;
                }

                .clover-panel {
                    padding: 0.84rem 0.84rem 0.92rem;
                    margin-bottom: 0.82rem;
                }

                .clover-risk-card {
                    padding: 0.82rem 0.82rem 0.76rem;
                }

                .clover-risk-head,
                .clover-risk-row {
                    gap: 0.56rem;
                }

                .clover-risk-column {
                    font-size: 0.8rem;
                }

                .clover-risk-issue,
                .clover-risk-score-value {
                    font-size: 0.72rem;
                }

                .clover-panel-header {
                    margin-bottom: 0.68rem;
                }

                .clover-issue-list {
                    gap: 0.6rem;
                }

                .clover-issue-item {
                    gap: 0.68rem;
                    padding: 0.76rem;
                }

                .clover-issue-icon {
                    width: 31px;
                    height: 31px;
                    min-width: 31px;
                }

                .clover-issue-title {
                    font-size: 0.86rem;
                }

                .clover-issue-message,
                .clover-gauge-recommendation,
                .clover-report-copy {
                    font-size: 0.78rem;
                }

                .clover-status-pill {
                    font-size: 0.68rem;
                    padding: 0.24rem 0.58rem;
                }

                .clover-mini-title {
                    font-size: 0.88rem;
                }

                .clover-mini-subtitle {
                    font-size: 0.74rem;
                    min-height: 1.95rem;
                }

                .clover-mini-stats {
                    gap: 0.36rem;
                    margin-top: 0.28rem;
                    padding: 0.7rem 0.8rem;
                }

                .clover-mini-stats span {
                    font-size: 0.76rem;
                }

                .clover-mini-stats strong {
                    font-size: 0.82rem;
                }

                div[class*="st-key-clover-overview-card-"] {
                    min-height: 24.2rem;
                    padding: 0.76rem 0.76rem 0.72rem;
                }

                .clover-overview-chart-head {
                    min-height: 2.85rem;
                }

                .clover-overview-chart-title,
                .clover-validation-preview-title {
                    font-size: 0.92rem;
                }

                .clover-overview-chart-subtitle,
                .clover-validation-preview-subtitle {
                    font-size: 0.76rem;
                    line-height: 1.34;
                }

                div[class*="st-key-clover-validation-preview-"] {
                    min-height: 19.2rem;
                    padding: 0.78rem 0.78rem 0.74rem;
                }

                .clover-validation-preview-head {
                    min-height: 3.5rem;
                }

                .clover-preview-shell {
                    padding: 0.8rem;
                }
            }

            @media (max-width: 1280px) {
                [data-testid="stSidebar"][aria-expanded="true"] {
                    min-width: 232px;
                    max-width: 232px;
                }

                [data-testid="stAppViewContainer"] .main .block-container,
                [data-testid="stAppViewContainer"] section.main .block-container,
                .block-container {
                    padding-top: 0.98rem;
                    padding-bottom: 1.22rem;
                    padding-left: 0.45rem;
                    padding-right: 0.45rem;
                }

                [data-testid="stSidebar"] .block-container {
                    padding-left: 0.48rem;
                    padding-right: 0.48rem;
                }

                div[class*="st-key-clover-nav-item-"] button,
                div[class*="st-key-clover-nav-active-"] button {
                    min-height: 2.08rem;
                    padding: 0.2rem 0.7rem 0.2rem 0.74rem;
                }

                div[class*="st-key-clover-nav-item-"] button p,
                div[class*="st-key-clover-nav-active-"] button p {
                    font-size: 0.75rem;
                }

                div[class*="st-key-clover-top-header-shell"] {
                    min-height: 4.7rem;
                    padding: 0.78rem 0.66rem 0.72rem;
                }

                .clover-header-grid {
                    gap: 0.64rem;
                }

                .clover-header-copy h1 {
                    font-size: 0.96rem;
                }

                .clover-header-copy p {
                    font-size: 0.73rem;
                }

                div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] > div {
                    min-height: 1.78rem;
                }

                div[class*="st-key-clover-header-dataset"] [data-baseweb="select"] span {
                    font-size: 0.71rem;
                }

                .clover-header-chip {
                    min-height: 1.62rem;
                    padding: 0.24rem 0.44rem;
                    font-size: 0.63rem;
                }

                div[class*="st-key-clover-header-controls-shell"] [data-testid="stHorizontalBlock"] {
                    gap: 0.64rem;
                    row-gap: 0.48rem;
                }

                div[class*="st-key-clover-header-controls-shell"] [data-testid="stColumn"]:first-child {
                    flex-basis: 300px !important;
                    min-width: 250px;
                }

                .clover-section-head {
                    margin: 1.12rem 0 0.58rem;
                }

                .clover-section-title {
                    font-size: 0.94rem;
                }

                .clover-section-subtitle {
                    font-size: 0.81rem;
                }

                .clover-kpi-card {
                    min-height: 84px;
                    padding: 0.5rem 0.56rem;
                }

                .clover-kpi-shell {
                    gap: 0.52rem;
                }

                .clover-kpi-icon {
                    width: 30px;
                    height: 30px;
                    min-width: 30px;
                    font-size: 0.86rem;
                }

                .clover-kpi-title {
                    font-size: 0.58rem;
                }

                .clover-kpi-value {
                    font-size: 1.28rem;
                }

                .clover-kpi-note,
                .clover-kpi-status {
                    font-size: 0.57rem;
                }

                .clover-kpi-duplicate-summary {
                    min-height: 118px;
                }

                .clover-panel {
                    padding: 0.76rem 0.76rem 0.84rem;
                    margin-bottom: 0.72rem;
                }

                .clover-risk-card {
                    padding: 0.76rem 0.76rem 0.7rem;
                }

                .clover-risk-head,
                .clover-risk-row {
                    gap: 0.48rem;
                }

                .clover-risk-head {
                    font-size: 0.61rem;
                }

                .clover-risk-rank,
                .clover-risk-column {
                    font-size: 0.76rem;
                }

                .clover-risk-issue,
                .clover-risk-score-value {
                    font-size: 0.68rem;
                }

                .clover-risk-badge {
                    min-width: 4rem;
                    font-size: 0.58rem;
                }

                .clover-issue-item {
                    gap: 0.6rem;
                    padding: 0.68rem;
                }

                .clover-issue-title {
                    font-size: 0.82rem;
                }

                .clover-issue-message,
                .clover-gauge-recommendation,
                .clover-report-copy {
                    font-size: 0.74rem;
                }

                .clover-mini-subtitle {
                    font-size: 0.72rem;
                    min-height: 1.8rem;
                }

                .clover-mini-stats {
                    padding: 0.64rem 0.72rem;
                }

                .clover-mini-stats span {
                    font-size: 0.72rem;
                }

                .clover-mini-stats strong {
                    font-size: 0.78rem;
                }

                div[class*="st-key-clover-overview-card-"] {
                    min-height: 22.4rem;
                    padding: 0.7rem 0.7rem 0.66rem;
                }

                div[class*="st-key-clover-validation-preview-"] {
                    min-height: 18rem;
                    padding: 0.72rem 0.72rem 0.68rem;
                }

                .clover-overview-chart-head {
                    min-height: 2.7rem;
                }

                .clover-overview-chart-title,
                .clover-validation-preview-title {
                    font-size: 0.88rem;
                }

                .clover-overview-chart-subtitle,
                .clover-validation-preview-subtitle {
                    font-size: 0.73rem;
                }

                .clover-preview-shell {
                    padding: 0.74rem;
                }
            }

            .clover-section-head {
                margin: 1.55rem 0 0.76rem;
            }

            .clover-section-title {
                font-size: 1rem;
                font-weight: 700;
                color: var(--clover-text);
            }

            .clover-section-subtitle {
                margin-top: 0.22rem;
                color: var(--clover-muted);
                font-size: 0.88rem;
                line-height: 1.38;
            }

            .clover-kpi-card {
                background: linear-gradient(180deg, rgba(19, 34, 56, 0.97), rgba(10, 18, 30, 1));
                border: 1px solid var(--clover-border);
                border-radius: 18px;
                padding: 0.64rem 0.7rem;
                min-height: 98px;
                height: 100%;
                box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
                transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
                margin-bottom: 0.08rem;
            }

            .clover-kpi-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 18px 42px rgba(0, 0, 0, 0.22);
                border-color: var(--clover-border-strong);
            }

            .clover-kpi-shell {
                display: flex;
                align-items: flex-start;
                gap: 0.64rem;
                height: 100%;
            }

            .clover-kpi-copy {
                min-width: 0;
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            .clover-kpi-icon {
                width: 34px;
                height: 34px;
                min-width: 34px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(255, 255, 255, 0.07);
                color: var(--clover-text);
                font-size: 0.96rem;
                font-weight: 700;
                box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
            }

            .clover-kpi-status {
                font-size: 0.61rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: var(--clover-muted);
                margin-top: 0.14rem;
            }

            .clover-kpi-title {
                font-size: 0.64rem;
                color: var(--clover-muted);
                margin-bottom: 0.12rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                font-weight: 700;
            }

            .clover-kpi-value {
                font-size: 1.56rem;
                line-height: 1.05;
                font-weight: 700;
                color: var(--clover-text);
                margin-bottom: 0;
            }

            .clover-kpi-value-suffix {
                margin-left: 0.1rem;
                font-size: 0.82rem;
                color: var(--clover-muted);
            }

            .clover-kpi-note {
                font-size: 0.64rem;
                color: var(--clover-muted);
                line-height: 1.22;
                margin-top: 0.12rem;
            }

            .clover-kpi-duplicate-summary {
                min-height: 130px;
            }

            .clover-kpi-duplicate-summary .clover-kpi-title {
                min-height: 2.1em;
                display: flex;
                align-items: flex-start;
                font-size: 0.6rem;
            }

            .clover-kpi-duplicate-summary .clover-kpi-note {
                min-height: 1.25em;
            }

            .clover-kpi-good { border-top: 3px solid var(--clover-accent); }
            .clover-kpi-warning { border-top: 3px solid var(--clover-warning); }
            .clover-kpi-danger { border-top: 3px solid var(--clover-danger); }
            .clover-kpi-poor { border-top: 3px solid var(--clover-danger); }
            .clover-kpi-quality { border-top: 3px solid #3fb4ff; }
            .clover-kpi-teal { border-top: 3px solid #17c4b8; }
            .clover-kpi-purple { border-top: 3px solid #8f6bff; }

            .clover-kpi-quality .clover-kpi-icon {
                background: linear-gradient(180deg, rgba(63, 180, 255, 0.18), rgba(57, 217, 138, 0.12));
                color: #76dbff;
            }

            .clover-kpi-good .clover-kpi-icon {
                background: rgba(57, 217, 138, 0.13);
                color: #8ef0be;
            }

            .clover-kpi-warning .clover-kpi-icon {
                background: rgba(255, 176, 32, 0.14);
                color: #ffc761;
            }

            .clover-kpi-danger .clover-kpi-icon,
            .clover-kpi-poor .clover-kpi-icon {
                background: rgba(255, 107, 107, 0.13);
                color: #ff9b9b;
            }

            .clover-kpi-teal .clover-kpi-icon {
                background: rgba(23, 196, 184, 0.13);
                color: #57efe1;
            }

            .clover-kpi-purple .clover-kpi-icon {
                background: rgba(143, 107, 255, 0.14);
                color: #c7b6ff;
            }

            .clover-panel {
                background: linear-gradient(180deg, rgba(18, 31, 49, 0.94), rgba(9, 18, 30, 0.98));
                border: 1px solid var(--clover-border);
                border-radius: 22px;
                padding: 0.92rem 0.92rem 1rem;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
                margin-bottom: 0.9rem;
            }

            .clover-panel-header {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                margin-bottom: 0.7rem;
            }

            .clover-risk-card {
                background: linear-gradient(180deg, rgba(18, 31, 49, 0.94), rgba(9, 18, 30, 0.98));
                border: 1px solid var(--clover-border);
                border-radius: 22px;
                padding: 0.96rem 0.96rem 0.88rem;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
            }

            .clover-risk-head,
            .clover-risk-row {
                display: grid;
                grid-template-columns: 0.48fr 1.5fr 0.9fr 1.15fr 1.45fr;
                gap: 0.7rem;
                align-items: center;
            }

            .clover-risk-head {
                padding: 0 0.12rem 0.48rem;
                border-bottom: 1px solid rgba(124, 156, 191, 0.14);
                color: rgba(138, 160, 184, 0.92);
                font-size: 0.66rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .clover-risk-body {
                display: grid;
            }

            .clover-risk-row {
                padding: 0.72rem 0.12rem;
                border-bottom: 1px solid rgba(124, 156, 191, 0.1);
            }

            .clover-risk-row:last-child {
                border-bottom: 0;
                padding-bottom: 0.28rem;
            }

            .clover-risk-rank {
                color: var(--clover-text);
                font-size: 0.84rem;
                font-weight: 700;
            }

            .clover-risk-column {
                color: var(--clover-text);
                font-size: 0.84rem;
                font-weight: 600;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .clover-risk-issue {
                color: var(--clover-muted);
                font-size: 0.76rem;
                line-height: 1.28;
            }

            .clover-risk-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: fit-content;
                min-width: 4.4rem;
                padding: 0.22rem 0.48rem;
                border-radius: 999px;
                font-size: 0.62rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                border: 1px solid transparent;
            }

            .clover-risk-badge.high {
                color: #ffb1b1;
                background: rgba(255, 107, 107, 0.14);
                border-color: rgba(255, 107, 107, 0.24);
            }

            .clover-risk-badge.medium {
                color: #ffd381;
                background: rgba(255, 176, 32, 0.14);
                border-color: rgba(255, 176, 32, 0.24);
            }

            .clover-risk-badge.low {
                color: #98f2bd;
                background: rgba(57, 217, 138, 0.14);
                border-color: rgba(57, 217, 138, 0.24);
            }

            .clover-risk-score-wrap {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.55rem;
                align-items: center;
            }

            .clover-risk-score-track {
                position: relative;
                height: 0.46rem;
                border-radius: 999px;
                overflow: hidden;
                background: rgba(255, 255, 255, 0.08);
            }

            .clover-risk-score-fill {
                position: absolute;
                inset: 0 auto 0 0;
                border-radius: 999px;
            }

            .clover-risk-score-fill.high {
                background: linear-gradient(90deg, #ff6b6b, #ff8a8a);
            }

            .clover-risk-score-fill.medium {
                background: linear-gradient(90deg, #ffb020, #ffd166);
            }

            .clover-risk-score-fill.low {
                background: linear-gradient(90deg, #39d98a, #6df3af);
            }

            .clover-risk-score-value {
                color: var(--clover-text);
                font-size: 0.76rem;
                font-weight: 700;
                min-width: 1.8rem;
                text-align: right;
            }

            .clover-issue-list {
                display: grid;
                gap: 0.64rem;
            }

            .clover-issue-item {
                display: flex;
                gap: 0.72rem;
                align-items: flex-start;
                padding: 0.82rem;
                border-radius: 16px;
                border: 1px solid rgba(124, 156, 191, 0.12);
                background: rgba(255, 255, 255, 0.03);
            }

            .clover-issue-icon {
                width: 32px;
                height: 32px;
                min-width: 32px;
                border-radius: 11px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
            }

            .clover-issue-title {
                font-size: 0.88rem;
                font-weight: 700;
                color: var(--clover-text);
                margin-bottom: 0.16rem;
            }

            .clover-issue-message {
                font-size: 0.8rem;
                line-height: 1.38;
                color: var(--clover-muted);
            }

            .clover-issue-error .clover-issue-icon {
                background: rgba(255, 107, 107, 0.16);
                color: var(--clover-danger);
            }

            .clover-issue-warning .clover-issue-icon {
                background: rgba(255, 176, 32, 0.16);
                color: var(--clover-warning);
            }

            .clover-issue-info .clover-issue-icon {
                background: rgba(93, 169, 255, 0.16);
                color: var(--clover-info);
            }

            .clover-gauge-meta {
                display: grid;
                gap: 0.56rem;
                margin-top: 0.4rem;
            }

            .clover-gauge-meta-compact {
                gap: 0.38rem;
                margin-top: 0.12rem;
            }

            .clover-gauge-footer {
                margin-top: 0.15rem;
            }

            .clover-status-pill {
                display: inline-flex;
                align-items: center;
                width: fit-content;
                border: 1px solid;
                border-radius: 999px;
                padding: 0.24rem 0.6rem;
                font-size: 0.69rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                background: rgba(255, 255, 255, 0.03);
            }

            .clover-gauge-recommendation {
                color: var(--clover-muted);
                line-height: 1.36;
                font-size: 0.8rem;
            }

            .clover-mini-panel {
                margin-bottom: 0.35rem;
            }

            .clover-mini-title {
                font-size: 0.9rem;
                font-weight: 700;
                color: var(--clover-text);
            }

            .clover-mini-subtitle {
                margin-top: 0.18rem;
                font-size: 0.76rem;
                color: var(--clover-muted);
                line-height: 1.34;
                min-height: 2rem;
            }

            .clover-mini-stats {
                display: grid;
                gap: 0.4rem;
                margin-top: 0.3rem;
                padding: 0.76rem 0.84rem;
                border-radius: 16px;
                border: 1px solid var(--clover-border);
                background: rgba(255, 255, 255, 0.03);
            }

            .clover-mini-stats div {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
            }

            .clover-mini-stats span {
                color: var(--clover-muted);
                font-size: 0.78rem;
            }

            .clover-mini-stats strong {
                color: var(--clover-text);
                font-size: 0.84rem;
            }

            .clover-preview-shell {
                border: 1px solid var(--clover-border);
                border-radius: 20px;
                padding: 0.9rem;
                background: linear-gradient(180deg, rgba(18, 31, 49, 0.92), rgba(9, 18, 30, 0.98));
                box-shadow: 0 18px 46px rgba(0, 0, 0, 0.22);
            }

            div[class*="st-key-clover-validation-preview-"] {
                min-height: 21.5rem;
                padding: 0.88rem 0.88rem 0.82rem;
                border: 1px solid var(--clover-border);
                border-radius: 22px;
                background: linear-gradient(180deg, rgba(18, 31, 49, 0.94), rgba(9, 18, 30, 0.98));
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
            }

            div[class*="st-key-clover-validation-preview-"] > div[data-testid="stVerticalBlock"] {
                height: 100%;
                gap: 0.55rem;
                justify-content: flex-start;
            }

            .clover-validation-preview-head {
                min-height: 3.7rem;
                display: grid;
                align-content: start;
                gap: 0.25rem;
            }

            .clover-validation-preview-title {
                font-size: 0.94rem;
                font-weight: 700;
                color: var(--clover-text);
                line-height: 1.28;
            }

            .clover-validation-preview-subtitle {
                color: var(--clover-muted);
                font-size: 0.76rem;
                line-height: 1.34;
            }

            .clover-report-copy {
                color: var(--clover-muted);
                line-height: 1.5;
                font-size: 0.86rem;
            }

            div[class*="st-key-clover-overview-card-"] {
                height: 100%;
                min-height: 27.25rem;
                padding: 0.9rem 0.9rem 0.82rem;
                border: 1px solid var(--clover-border);
                border-radius: 22px;
                background: linear-gradient(180deg, rgba(18, 31, 49, 0.94), rgba(9, 18, 30, 0.98));
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.22);
            }

            div[class*="st-key-clover-overview-card-"] > div[data-testid="stVerticalBlock"] {
                height: 100%;
                gap: 0.55rem;
                justify-content: flex-start;
            }

            div[class*="st-key-clover-overview-card-"] [data-testid="stPlotlyChart"] {
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .clover-overview-chart-head {
                min-height: 3.15rem;
                display: grid;
                align-content: start;
                gap: 0.25rem;
            }

            .clover-overview-chart-title {
                font-size: 0.94rem;
                font-weight: 700;
                color: var(--clover-text);
                line-height: 1.28;
            }

            .clover-overview-chart-subtitle {
                color: var(--clover-muted);
                font-size: 0.76rem;
                line-height: 1.34;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_default_analysis_status() -> dict:
    """Return the default sidebar analysis status."""
    return {
        "state": "idle",
        "title": "Status",
        "message": ANALYSIS_STATUS_MESSAGES["idle"],
        "signature": None,
    }


def get_analysis_status() -> dict:
    """Return the normalized analysis status stored in session state."""
    status = st.session_state.get("clover_analysis_status")
    default = get_default_analysis_status()
    if not isinstance(status, dict):
        return default
    return {
        "state": status.get("state", default["state"]),
        "title": status.get("title", default["title"]),
        "message": status.get("message", default["message"]),
        "signature": status.get("signature"),
    }


def set_analysis_status(
    state: str,
    *,
    signature=None,
    message: str | None = None,
    title: str | None = None,
) -> dict:
    """Persist the current analysis status for sidebar rendering."""
    default = get_default_analysis_status()
    status = {
        "state": state,
        "title": title or default["title"],
        "message": message or ANALYSIS_STATUS_MESSAGES.get(state, default["message"]),
        "signature": signature,
    }
    st.session_state["clover_analysis_status"] = status
    return status


def build_report_filename(dataset_name: str) -> str:
    """Build a filesystem-safe Clover PDF report filename."""
    safe_name = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in str(dataset_name).strip()
    ).strip("_")
    if not safe_name:
        safe_name = "dataset"
    return f"Clover_Report_{safe_name}.pdf"


def render_section_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="clover-section-head">
            <div class="clover-section-title">{title}</div>
            <div class="clover-section-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_header(dataset_info: dict) -> None:
    """Render the compact dashboard header area."""
    with st.container(key="clover-top-header-shell"):
        header_left, header_right = st.columns((1.2, 1.1), gap="large")
        with header_left:
            st.markdown(
                """
                <div class="clover-header-copy">
                    <h1>DATA QUALITY OVERVIEW</h1>
                    <p>Understand the health and reliability of your dataset at a glance.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with header_right:
            with st.container(key="clover-header-controls-shell"):
                control_left, control_right = st.columns((1.8, 0.75), gap="medium")
                with control_left:
                    with st.container(key="clover-header-dataset"):
                        st.selectbox(
                            "Dataset",
                            options=[dataset_info.get("file_name", "No dataset loaded")],
                            index=0,
                            label_visibility="collapsed",
                            help=f"Full filename: {dataset_info.get('file_name', 'No dataset loaded')}",
                            key="clover_header_dataset_selector",
                        )
                with control_right:
                    st.markdown(
                        f'<div class="clover-header-chip">Last analyzed: {dataset_info.get("upload_date", "Not uploaded")}</div>',
                        unsafe_allow_html=True,
                    )


def load_dataset(uploaded_file) -> pd.DataFrame | None:
    """Read the uploaded CSV into a DataFrame."""
    if uploaded_file is None:
        return None
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return read_csv_preserve_strings(uploaded_file)
    except Exception as exc:
        st.error(f"Unable to read the uploaded CSV: {exc}")
        return None


def _empty_validation_result(label: str) -> dict:
    return {
        "label": label,
        "matched_columns": [],
        "valid_count": 0,
        "invalid_count": 0,
        "total_checked": 0,
        "valid_percentage": 0.0,
        "has_match": False,
    }


def _empty_validation_preview_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["row_number", "column_name", "invalid_value", "reason"]
    )


def _empty_validation_previews() -> dict:
    return {
        "email": _empty_validation_preview_frame(),
        "name": _empty_validation_preview_frame(),
        "username": _empty_validation_preview_frame(),
        "dob": _empty_validation_preview_frame(),
        "phone": _empty_validation_preview_frame(),
    }


def build_empty_metrics() -> dict:
    empty_missing = pd.DataFrame({"column": ["No data loaded"], "missing_values": [0]})
    empty_uniqueness = pd.DataFrame(
        {
            "column": ["No data loaded"],
            "unique_values": [0],
            "uniqueness_percentage": [0.0],
        }
    )
    empty_special = pd.DataFrame(
        columns=[
            "column",
            "column_type",
            "affected_rows",
            "affected_percentage",
            "special_char_count",
            "emoji_count",
            "unique_special_chars",
            "unique_emojis",
        ]
    )
    empty_validation = {
        key: _empty_validation_result(config["label"])
        for key, config in VALIDATION_BUCKETS.items()
    }
    empty_validation_by_column = pd.DataFrame(
        columns=[
            "column",
            "bucket",
            "primary_issue",
            "invalid_count",
            "total_checked",
            "invalid_percentage",
        ]
    )
    empty_email_duplicates = pd.DataFrame(
        columns=["column", "duplicate_rows", "duplicate_percentage"]
    )
    return {
        "total_rows": 0,
        "total_columns": 0,
        "missing_values": 0,
        "duplicate_rows": 0,
        "missing_by_column": empty_missing,
        "uniqueness_by_column": empty_uniqueness,
        "low_uniqueness_columns": empty_uniqueness.iloc[0:0].copy(),
        "special_character_columns": empty_special,
        "special_character_total": 0,
        "validation_results": empty_validation,
        "validation_by_column": empty_validation_by_column,
        "validation_previews": _empty_validation_previews(),
        "validation_overview": {
            "valid_count": 0,
            "invalid_count": 0,
            "total_checked": 0,
            "invalid_percentage": 0.0,
        },
        "duplicate_summary": {
            "exact_duplicates_count": 0,
            "exact_duplicates_pct": 0.0,
            "email_duplicates_count": 0,
            "email_duplicates_pct": 0.0,
        },
        "duplicate_tables": {},
        "email_duplicate_columns": empty_email_duplicates,
        "potential_keys": [],
        "insights": [],
        "quality_status_raw": "FAIL",
    }


def _normalize_column_name(column_name: str) -> str:
    return normalize_column_label(column_name)


def _resolve_validation_bucket(column_name: str, field_type: str | None = None) -> str | None:
    if field_type == "phone":
        return "phone"
    if field_type == "username":
        return "username"
    if field_type in {"date_of_birth", "date"}:
        return "dob"
    if field_type == "name":
        return "name"

    normalized = _normalize_column_name(column_name)
    for bucket_key, config in VALIDATION_BUCKETS.items():
        if bucket_key == "name":
            if is_name_column_label(column_name):
                return bucket_key
            continue
        if bucket_key == "username":
            if is_username_column_label(column_name):
                return bucket_key
            continue
        if bucket_key == "phone":
            if is_phone_column_label(column_name):
                return bucket_key
            continue
        if any(keyword in normalized for keyword in config["keywords"]):
            return bucket_key
    return None


def _aggregate_validation_results(clover_results: dict) -> tuple[dict, dict]:
    validation_results = {
        key: _empty_validation_result(config["label"])
        for key, config in VALIDATION_BUCKETS.items()
    }

    for column_name, stats in (clover_results.get("email_quality") or {}).items():
        result = validation_results["email"]
        result["matched_columns"].append(str(column_name))
        result["valid_count"] += int(stats.get("valid", 0))
        result["invalid_count"] += int(stats.get("invalid", 0))
        result["total_checked"] += int(stats.get("valid", 0)) + int(stats.get("invalid", 0))
        result["has_match"] = True

    for column_name, stats in (clover_results.get("field_quality") or {}).items():
        bucket_key = _resolve_validation_bucket(
            column_name,
            field_type=stats.get("type"),
        )
        if bucket_key is None:
            continue
        result = validation_results[bucket_key]
        result["matched_columns"].append(str(column_name))
        result["valid_count"] += int(stats.get("valid", 0))
        result["invalid_count"] += int(stats.get("invalid", 0))
        result["total_checked"] += int(stats.get("valid", 0)) + int(stats.get("invalid", 0))
        result["has_match"] = True

    total_valid = 0
    total_invalid = 0
    total_checked = 0
    for result in validation_results.values():
        result["matched_columns"] = list(dict.fromkeys(result["matched_columns"]))
        if result["total_checked"] > 0:
            result["valid_percentage"] = round(
                (result["valid_count"] / result["total_checked"]) * 100,
                1,
            )
        total_valid += result["valid_count"]
        total_invalid += result["invalid_count"]
        total_checked += result["total_checked"]

    validation_overview = {
        "valid_count": total_valid,
        "invalid_count": total_invalid,
        "total_checked": total_checked,
        "invalid_percentage": round((total_invalid / total_checked) * 100, 1)
        if total_checked
        else 0.0,
    }
    return validation_results, validation_overview


def _build_validation_by_column(clover_results: dict) -> pd.DataFrame:
    """Create per-column validation failure metrics from Clover results."""
    validation_rows: list[dict] = []
    issue_labels = {
        "email": "Invalid Emails",
        "name": "Invalid Names",
        "username": "Invalid Usernames",
        "dob": "Invalid Dates",
        "phone": "Invalid Phone",
    }

    for column_name, stats in (clover_results.get("email_quality") or {}).items():
        valid_count = int(stats.get("valid", 0))
        invalid_count = int(stats.get("invalid", 0))
        total_checked = valid_count + invalid_count
        validation_rows.append(
            {
                "column": str(column_name),
                "bucket": "email",
                "primary_issue": issue_labels["email"],
                "invalid_count": invalid_count,
                "total_checked": total_checked,
            }
        )

    for column_name, stats in (clover_results.get("field_quality") or {}).items():
        bucket_key = _resolve_validation_bucket(
            column_name,
            field_type=stats.get("type"),
        )
        if bucket_key is None:
            continue
        valid_count = int(stats.get("valid", 0))
        invalid_count = int(stats.get("invalid", 0))
        total_checked = valid_count + invalid_count
        validation_rows.append(
            {
                "column": str(column_name),
                "bucket": bucket_key,
                "primary_issue": issue_labels[bucket_key],
                "invalid_count": invalid_count,
                "total_checked": total_checked,
            }
        )

    if not validation_rows:
        return build_empty_metrics()["validation_by_column"].copy()

    validation_by_column = pd.DataFrame(validation_rows)
    validation_by_column = (
        validation_by_column.groupby(
            ["column", "bucket", "primary_issue"],
            as_index=False,
        )[["invalid_count", "total_checked"]]
        .sum()
    )
    validation_by_column["invalid_percentage"] = validation_by_column.apply(
        lambda row: round((row["invalid_count"] / row["total_checked"]) * 100, 1)
        if row["total_checked"]
        else 0.0,
        axis=1,
    )
    return validation_by_column.sort_values(
        by=["invalid_percentage", "invalid_count"],
        ascending=[False, False],
    ).reset_index(drop=True)


def _build_email_duplicate_columns(
    dataset: pd.DataFrame,
    duplicate_tables: dict,
    duplicate_summary: dict,
    validation_by_column: pd.DataFrame,
) -> pd.DataFrame:
    """Map backend email-duplicate results onto email-like columns."""
    email_columns = validation_by_column.loc[
        validation_by_column["bucket"] == "email",
        "column",
    ].drop_duplicates().tolist()

    if not email_columns:
        email_columns = [
            str(column)
            for column in dataset.columns
            if _resolve_validation_bucket(str(column)) == "email"
        ]

    if not email_columns:
        return build_empty_metrics()["email_duplicate_columns"].copy()

    email_duplicate_rows = int(duplicate_summary.get("email_duplicates_count", 0))
    email_duplicate_percentage = float(duplicate_summary.get("email_duplicates_pct", 0.0))
    email_duplicate_table = duplicate_tables.get("email_duplicates")

    email_duplicate_columns: list[dict] = []
    for column_name in email_columns:
        duplicate_rows = email_duplicate_rows
        duplicate_percentage = email_duplicate_percentage
        if (
            isinstance(email_duplicate_table, pd.DataFrame)
            and not email_duplicate_table.empty
            and column_name in email_duplicate_table.columns
        ):
            duplicate_rows = int(email_duplicate_table[column_name].notna().sum())
            duplicate_percentage = round((duplicate_rows / len(dataset)) * 100, 1) if len(dataset) else 0.0

        email_duplicate_columns.append(
            {
                "column": str(column_name),
                "duplicate_rows": duplicate_rows,
                "duplicate_percentage": duplicate_percentage,
            }
        )

    return pd.DataFrame(email_duplicate_columns).sort_values(
        by=["duplicate_percentage", "duplicate_rows"],
        ascending=[False, False],
    ).reset_index(drop=True)


def _coerce_validation_preview(preview_data) -> pd.DataFrame:
    if isinstance(preview_data, pd.DataFrame):
        preview = preview_data.copy()
    elif isinstance(preview_data, list):
        preview = pd.DataFrame(preview_data)
    else:
        return _empty_validation_preview_frame()

    if preview.empty:
        return _empty_validation_preview_frame()

    for column in ["row_number", "column_name", "invalid_value", "reason"]:
        if column not in preview.columns:
            preview[column] = ""

    preview = preview[["row_number", "column_name", "invalid_value", "reason"]].copy()
    preview["row_number"] = pd.to_numeric(preview["row_number"], errors="coerce").fillna(0).astype(int)
    preview["column_name"] = preview["column_name"].astype(str)
    preview["invalid_value"] = preview["invalid_value"].astype(str)
    preview["reason"] = preview["reason"].astype(str)
    return preview.head(10).reset_index(drop=True)


def adapt_clover_results(dataset: pd.DataFrame | None, clover_results: dict | None) -> dict:
    if dataset is None or clover_results is None:
        return build_empty_metrics()

    total_rows = int(dataset.shape[0])

    missingness = clover_results.get("missingness")
    if isinstance(missingness, pd.DataFrame) and not missingness.empty:
        missing_by_column = (
            missingness.reset_index()
            .rename(
                columns={
                    "index": "column",
                    "na_count": "missing_values",
                    "missing_pct": "missing_percentage",
                }
            )[["column", "missing_values"]]
            .copy()
        )
        missing_by_column["column"] = missing_by_column["column"].astype(str)
        missing_by_column["missing_values"] = (
            missing_by_column["missing_values"].fillna(0).astype(int)
        )
        missing_by_column = missing_by_column.sort_values(
            by="missing_values",
            ascending=False,
        ).reset_index(drop=True)
    else:
        missing_by_column = pd.DataFrame(
            {
                "column": [str(column) for column in dataset.columns],
                "missing_values": [0 for _ in dataset.columns],
            }
        )

    column_profiles = clover_results.get("columns")
    unique_counts = {
        str(column): int(dataset[column].nunique(dropna=False))
        for column in dataset.columns
    }
    if isinstance(column_profiles, pd.DataFrame) and not column_profiles.empty:
        uniqueness_by_column = column_profiles[["column", "uniqueness_%"]].rename(
            columns={"uniqueness_%": "uniqueness_percentage"}
        ).copy()
        uniqueness_by_column["column"] = uniqueness_by_column["column"].astype(str)
        uniqueness_by_column["unique_values"] = (
            uniqueness_by_column["column"].map(unique_counts).fillna(0).astype(int)
        )
        uniqueness_by_column["uniqueness_percentage"] = (
            uniqueness_by_column["uniqueness_percentage"].fillna(0.0).astype(float)
        )
        uniqueness_by_column = uniqueness_by_column[
            ["column", "unique_values", "uniqueness_percentage"]
        ].sort_values(by="uniqueness_percentage", ascending=True).reset_index(drop=True)
    else:
        uniqueness_by_column = pd.DataFrame(
            {
                "column": [str(column) for column in dataset.columns],
                "unique_values": [unique_counts[str(column)] for column in dataset.columns],
                "uniqueness_percentage": [0.0 for _ in dataset.columns],
            }
        )

    low_uniqueness_columns = uniqueness_by_column[
        uniqueness_by_column["uniqueness_percentage"] < LOW_UNIQUENESS_THRESHOLD
    ].reset_index(drop=True)

    validation_results, validation_overview = _aggregate_validation_results(clover_results)
    validation_by_column = _build_validation_by_column(clover_results)
    raw_validation_previews = dict(clover_results.get("validation_previews") or {})
    validation_previews = _empty_validation_previews()
    validation_previews["email"] = _coerce_validation_preview(raw_validation_previews.get("email"))
    validation_previews["name"] = _coerce_validation_preview(raw_validation_previews.get("name"))
    validation_previews["username"] = _coerce_validation_preview(raw_validation_previews.get("username"))
    dob_preview_frames = [
        _coerce_validation_preview(raw_validation_previews.get("date_of_birth")),
        _coerce_validation_preview(raw_validation_previews.get("date")),
    ]
    validation_previews["dob"] = (
        pd.concat([frame for frame in dob_preview_frames if not frame.empty], ignore_index=True)
        .head(10)
        .reset_index(drop=True)
        if any(not frame.empty for frame in dob_preview_frames)
        else _empty_validation_preview_frame()
    )
    validation_previews["phone"] = _coerce_validation_preview(raw_validation_previews.get("phone"))

    special_characters = clover_results.get("special_characters")
    if isinstance(special_characters, pd.DataFrame) and not special_characters.empty:
        special_character_columns = special_characters.copy()
        special_character_columns["column"] = special_character_columns["column"].astype(str)
        if "column_type" not in special_character_columns.columns:
            special_character_columns["column_type"] = "generic"
        special_character_columns["column_type"] = special_character_columns["column_type"].astype(str)
        special_character_columns["special_char_count"] = (
            special_character_columns.get("special_char_count", 0).fillna(0).astype(int)
        )
        special_character_columns["emoji_count"] = (
            special_character_columns.get("emoji_count", 0).fillna(0).astype(int)
        )
        special_character_columns["affected_rows"] = (
            special_character_columns.get("affected_rows", 0).fillna(0).astype(int)
        )
        special_character_columns["affected_percentage"] = (
            special_character_columns.get("affected_percentage", 0.0).fillna(0.0).astype(float)
        )
        special_character_columns = special_character_columns[
            special_character_columns["affected_rows"] > 0
        ].sort_values(by="affected_rows", ascending=False).reset_index(drop=True)
        special_character_columns = special_character_columns[
            [
                "column",
                "column_type",
                "unique_special_chars",
                "unique_emojis",
                "special_char_count",
                "emoji_count",
                "affected_rows",
                "affected_percentage",
            ]
        ]
    else:
        special_character_columns = pd.DataFrame(
            columns=[
                "column",
                "column_type",
                "unique_special_chars",
                "unique_emojis",
                "special_char_count",
                "emoji_count",
                "affected_rows",
                "affected_percentage",
            ]
        )

    duplicate_summary = dict(clover_results.get("duplicate_summary") or {})
    duplicate_tables = dict(clover_results.get("duplicate_tables") or {})
    email_duplicate_columns = _build_email_duplicate_columns(
        dataset,
        duplicate_tables,
        duplicate_summary,
        validation_by_column,
    )
    duplicate_rows = int(duplicate_summary.get("exact_duplicates_count", 0))
    special_character_total = (
        int(special_character_columns["affected_rows"].sum())
        if not special_character_columns.empty
        else 0
    )

    return {
        "total_rows": int(dataset.shape[0]),
        "total_columns": int(dataset.shape[1]),
        "missing_values": int(missing_by_column["missing_values"].sum())
        if not missing_by_column.empty
        else 0,
        "duplicate_rows": duplicate_rows,
        "missing_by_column": missing_by_column,
        "uniqueness_by_column": uniqueness_by_column,
        "low_uniqueness_columns": low_uniqueness_columns,
        "special_character_columns": special_character_columns,
        "special_character_total": special_character_total,
        "validation_results": validation_results,
        "validation_by_column": validation_by_column,
        "validation_previews": validation_previews,
        "validation_overview": validation_overview,
        "duplicate_summary": duplicate_summary,
        "duplicate_tables": duplicate_tables,
        "email_duplicate_columns": email_duplicate_columns,
        "potential_keys": list(clover_results.get("potential_keys") or []),
        "insights": list(clover_results.get("insights") or []),
        "quality_status_raw": str(clover_results.get("quality_status", "FAIL")).upper(),
    }


def normalize_quality_score(raw_score: float | int | None) -> float:
    score = float(raw_score or 0.0)
    if score <= 1.0:
        score *= 100
    return round(max(0.0, min(100.0, score)), 1)


def map_quality_status(raw_status: str, has_dataset: bool) -> dict:
    if not has_dataset:
        return {"label": "Pending", "color": "#5da9ff"}
    return QUALITY_STATUS_MAP.get(str(raw_status).upper(), QUALITY_STATUS_MAP["FAIL"])


def build_quality_recommendation(
    metrics: dict,
    clover_results: dict | None,
    quality_status: dict,
) -> str:
    if metrics["total_rows"] == 0:
        return "Upload a dataset to generate Clover profiling, validation, and duplicate insights."

    insights = [
        str(item).strip()
        for item in (clover_results or {}).get("insights", [])
        if str(item).strip()
    ]
    if insights:
        return " ".join(insights[:2])

    if quality_status["label"] == "Good":
        return "Quality checks are passing. Monitor future uploads and review any edge-case fields before downstream use."
    if quality_status["label"] == "Warning":
        return "Review missing values, duplicates, and field validation warnings before using this dataset broadly."
    return "This dataset needs remediation before operational use. Prioritize duplicates, invalid fields, and missing values first."


def summarize_top_issues(metrics: dict) -> list[dict]:
    if metrics["total_rows"] == 0 or metrics["total_columns"] == 0:
        return [
            {
                "severity": "info",
                "icon": "&#9432;",
                "title": "No dataset loaded",
                "message": "Upload a CSV file to generate Clover issue summaries, validations, and uniqueness analysis.",
            }
        ]

    issues = []
    total_cells = metrics["total_rows"] * metrics["total_columns"]
    missing_ratio = (metrics["missing_values"] / total_cells) * 100 if total_cells else 0.0
    duplicate_summary = metrics.get("duplicate_summary", {})
    exact_duplicate_count = int(duplicate_summary.get("exact_duplicates_count", 0))
    email_duplicate_count = int(duplicate_summary.get("email_duplicates_count", 0))
    exact_duplicate_ratio = (
        (exact_duplicate_count / metrics["total_rows"]) * 100
        if metrics["total_rows"]
        else 0.0
    )
    invalid_ratio = metrics["validation_overview"]["invalid_percentage"]

    if exact_duplicate_count > 0:
        severity = "error" if exact_duplicate_ratio >= 10 else "warning"
        issues.append(
            {
                "severity": severity,
                "icon": "&#10006;" if severity == "error" else "&#9888;",
                "title": "Exact duplicates detected",
                "message": (
                    f"{exact_duplicate_count:,} rows are exact duplicates "
                    f"({exact_duplicate_ratio:.1f}% of the dataset)."
                ),
            }
        )

    if email_duplicate_count > 0:
        issues.append(
            {
                "severity": "warning",
                "icon": "&#9888;",
                "title": "Email duplicates detected",
                "message": f"{email_duplicate_count:,} rows share duplicate email values.",
            }
        )

    if metrics["missing_values"] > 0:
        top_columns = metrics["missing_by_column"]
        top_columns = top_columns[top_columns["missing_values"] > 0]["column"].head(3).tolist()
        severity = "error" if missing_ratio >= 10 else "warning"
        issues.append(
            {
                "severity": severity,
                "icon": "&#10006;" if severity == "error" else "&#9888;",
                "title": "Missing values require review",
                "message": (
                    f"{metrics['missing_values']:,} missing values detected "
                    f"({missing_ratio:.1f}% of all cells). "
                    f"Most affected columns: {', '.join(top_columns) or 'n/a'}."
                ),
            }
        )

    if metrics["validation_overview"]["invalid_count"] > 0:
        failing_checks = [
            result["label"].replace(" Validation", "")
            for result in metrics["validation_results"].values()
            if result["invalid_count"] > 0
        ]
        severity = "error" if invalid_ratio >= 15 else "warning"
        issues.append(
            {
                "severity": severity,
                "icon": "&#10006;" if severity == "error" else "&#9888;",
                "title": "Validation failures found",
                "message": (
                    f"{metrics['validation_overview']['invalid_count']:,} invalid values "
                    f"across {', '.join(failing_checks)} checks."
                ),
            }
        )

    if metrics["special_character_total"] > 0:
        top_special_columns = metrics["special_character_columns"]["column"].head(3).tolist()
        issues.append(
            {
                "severity": "info",
                "icon": "&#9432;",
                "title": "Special characters detected",
                "message": (
                    f"{metrics['special_character_total']:,} flagged characters or emojis were found. "
                    f"Review columns: {', '.join(top_special_columns)}."
                ),
            }
        )

    if not metrics["low_uniqueness_columns"].empty:
        low_unique_columns = metrics["low_uniqueness_columns"]["column"].head(4).tolist()
        severity = "warning" if len(low_unique_columns) >= 2 else "info"
        issues.append(
            {
                "severity": severity,
                "icon": "&#9888;" if severity == "warning" else "&#9432;",
                "title": "Low uniqueness columns identified",
                "message": (
                    f"{len(metrics['low_uniqueness_columns'])} columns have uniqueness below "
                    f"{LOW_UNIQUENESS_THRESHOLD:.0f}%. "
                    f"Examples: {', '.join(low_unique_columns)}."
                ),
            }
        )

    if not issues:
        insights = metrics.get("insights") or []
        if insights:
            issues.append(
                {
                    "severity": "info",
                    "icon": "&#9432;",
                    "title": "Clover insights",
                    "message": " ".join(str(insight) for insight in insights[:2]),
                }
            )
        else:
            issues.append(
                {
                    "severity": "info",
                    "icon": "&#9432;",
                    "title": "No major issues detected",
                    "message": "The current dataset has no major duplicate, missing, or validation issues in the tracked Clover checks.",
                }
            )

    severity_order = {"error": 0, "warning": 1, "info": 2}
    return sorted(issues, key=lambda issue: severity_order[issue["severity"]])


def analyze_uploaded_file(
    uploaded_file,
) -> tuple[pd.DataFrame | None, dict, dict, float, dict, str, list[dict]]:
    dataset = load_dataset(uploaded_file)
    if dataset is None:
        empty_metrics = build_empty_metrics()
        empty_status = map_quality_status("FAIL", has_dataset=False)
        return (
            None,
            empty_metrics,
            {},
            0.0,
            empty_status,
            build_quality_recommendation(empty_metrics, None, empty_status),
            summarize_top_issues(empty_metrics),
        )

    signature = (uploaded_file.name, uploaded_file.size)
    cached_bundle = st.session_state.get("clover_backend_bundle")
    if st.session_state.get("clover_backend_signature") == signature and cached_bundle:
        return (
            cached_bundle["dataset"],
            cached_bundle["metrics"],
            cached_bundle["clover_results"],
            cached_bundle["quality_score"],
            cached_bundle["quality_status"],
            cached_bundle["quality_recommendation"],
            cached_bundle["top_issues"],
        )

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
            temp_file.write(file_bytes)
            temp_path = Path(temp_file.name)
        clover_results = unique_profile(temp_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    metrics = adapt_clover_results(dataset, clover_results)
    metrics["valid_records"] = calculate_valid_records(dataset, metrics)
    quality_score = normalize_quality_score(clover_results.get("quality_score"))
    quality_status = map_quality_status(
        clover_results.get("quality_status", "FAIL"),
        has_dataset=True,
    )
    quality_recommendation = build_quality_recommendation(
        metrics,
        clover_results,
        quality_status,
    )
    top_issues = summarize_top_issues(metrics)

    bundle = {
        "dataset": dataset,
        "metrics": metrics,
        "clover_results": clover_results,
        "quality_score": quality_score,
        "quality_status": quality_status,
        "quality_recommendation": quality_recommendation,
        "top_issues": top_issues,
    }
    st.session_state["clover_backend_signature"] = signature
    st.session_state["clover_backend_bundle"] = bundle
    return (
        dataset,
        metrics,
        clover_results,
        quality_score,
        quality_status,
        quality_recommendation,
        top_issues,
    )


def build_dataset_info(uploaded_file, metrics: dict) -> dict:
    """Build sidebar dataset metadata."""
    analysis_status = get_analysis_status()
    upload_complete = (
        uploaded_file is not None and analysis_status.get("state") == "complete"
    )
    if uploaded_file is not None:
        signature = (uploaded_file.name, uploaded_file.size)
        if st.session_state.get("clover_upload_signature") != signature:
            st.session_state["clover_upload_signature"] = signature
            st.session_state["clover_upload_time"] = datetime.now()

    upload_time = st.session_state.get("clover_upload_time")
    analyzed_time = st.session_state.get("clover_last_analyzed_time")
    file_size = "0 KB"
    if uploaded_file is not None:
        size_kb = uploaded_file.size / 1024
        file_size = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"

    return {
        "rows": f"{metrics['total_rows']:,}",
        "columns": f"{metrics['total_columns']:,}",
        "file_size": file_size,
        "file_name": uploaded_file.name if uploaded_file is not None else "No dataset loaded",
        "uploaded_by": "Current user",
        "upload_date": upload_time.strftime("%Y-%m-%d %H:%M") if upload_time else "Not uploaded",
        "last_analyzed": analyzed_time.strftime("%Y-%m-%d %H:%M") if analyzed_time else "Not analyzed",
        "upload_complete": upload_complete,
    }


def calculate_valid_records(dataset: pd.DataFrame | None, metrics: dict) -> int:
    """Estimate record-level validity from completeness and duplicate checks."""
    if dataset is None or metrics["total_rows"] == 0:
        return 0
    rows_with_missing = int(dataset.isna().any(axis=1).sum())
    return max(metrics["total_rows"] - metrics["duplicate_rows"] - rows_with_missing, 0)


def build_column_profile(dataset: pd.DataFrame | None, metrics: dict) -> pd.DataFrame:
    """Build a per-column profile table."""
    if dataset is None:
        return pd.DataFrame(
            columns=[
                "column",
                "data_type",
                "missing_values",
                "uniqueness_percentage",
                "special_character_rows",
            ]
        )

    profile = pd.DataFrame(
        {
            "column": [str(column) for column in dataset.columns],
            "data_type": [str(dtype) for dtype in dataset.dtypes],
        }
    )
    missing = metrics["missing_by_column"][["column", "missing_values"]]
    uniqueness = metrics["uniqueness_by_column"][["column", "uniqueness_percentage"]]
    special = metrics["special_character_columns"][["column", "affected_rows"]].rename(
        columns={"affected_rows": "special_character_rows"}
    )

    profile = profile.merge(missing, on="column", how="left")
    profile = profile.merge(uniqueness, on="column", how="left")
    profile = profile.merge(special, on="column", how="left")
    return profile.fillna(
        {
            "missing_values": 0,
            "uniqueness_percentage": 0.0,
            "special_character_rows": 0,
        }
    )


def render_preview_panel(dataset: pd.DataFrame | None) -> None:
    """Render the mini preview section."""
    render_section_header(
        "Mini Dataset Preview",
        "A compact view of the first five rows, with a shortcut into the full preview page.",
    )
    st.markdown('<div class="clover-preview-shell">', unsafe_allow_html=True)
    if dataset is None:
        st.info("Upload a CSV file to preview the first rows.")
    else:
        st.dataframe(dataset.head(5), use_container_width=True)
    if st.button("View Full Preview", key="overview_full_preview", use_container_width=True):
        st.session_state["clover_nav"] = "Data Preview"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_overview_chart_card(
    container_key: str,
    title: str,
    subtitle: str,
    render_chart,
) -> None:
    """Render a consistently styled overview chart card."""
    with st.container(key=container_key):
        st.markdown(
            f"""
            <div class="clover-overview-chart-head">
                <div class="clover-overview-chart-title">{title}</div>
                <div class="clover-overview-chart-subtitle">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_chart()


def build_column_risk_ranking(metrics: dict, limit: int = 5) -> pd.DataFrame:
    """Rank columns by weighted live-quality risk signals from Clover."""
    total_rows = int(metrics.get("total_rows", 0))
    uniqueness_by_column = metrics.get("uniqueness_by_column", pd.DataFrame()).copy()
    if (
        total_rows == 0
        or uniqueness_by_column.empty
        or "column" not in uniqueness_by_column.columns
    ):
        return pd.DataFrame(
            columns=["rank", "column", "risk_level", "primary_issue", "risk_score"]
        )

    ranking = uniqueness_by_column[["column", "uniqueness_percentage"]].copy()
    ranking["column"] = ranking["column"].astype(str)
    ranking = ranking[ranking["column"] != "No data loaded"].reset_index(drop=True)
    if ranking.empty:
        return pd.DataFrame(
            columns=["rank", "column", "risk_level", "primary_issue", "risk_score"]
        )

    missing_by_column = metrics.get("missing_by_column", pd.DataFrame())
    if not missing_by_column.empty:
        ranking = ranking.merge(
            missing_by_column[["column", "missing_values"]],
            on="column",
            how="left",
        )
    if "missing_values" not in ranking.columns:
        ranking["missing_values"] = 0
    ranking["missing_values"] = ranking["missing_values"].fillna(0).astype(int)
    ranking["missing_percentage"] = (
        ranking["missing_values"] / total_rows * 100 if total_rows else 0.0
    )

    validation_by_column = metrics.get("validation_by_column", pd.DataFrame())
    if not validation_by_column.empty:
        strongest_validation = validation_by_column.sort_values(
            by=["invalid_percentage", "invalid_count"],
            ascending=[False, False],
        ).drop_duplicates(subset=["column"])
        ranking = ranking.merge(
            strongest_validation[
                ["column", "primary_issue", "invalid_percentage", "invalid_count"]
            ],
            on="column",
            how="left",
        )
    if "invalid_percentage" not in ranking.columns:
        ranking["invalid_percentage"] = 0.0
    if "invalid_count" not in ranking.columns:
        ranking["invalid_count"] = 0
    if "primary_issue" not in ranking.columns:
        ranking["primary_issue"] = ""
    ranking["invalid_percentage"] = ranking["invalid_percentage"].fillna(0.0).astype(float)
    ranking["invalid_count"] = ranking["invalid_count"].fillna(0).astype(int)
    ranking["validation_issue"] = ranking["primary_issue"].fillna("").astype(str)

    special_character_columns = metrics.get("special_character_columns", pd.DataFrame())
    if not special_character_columns.empty:
        ranking = ranking.merge(
            special_character_columns[["column", "affected_percentage"]],
            on="column",
            how="left",
        )
    if "affected_percentage" not in ranking.columns:
        ranking["affected_percentage"] = 0.0
    ranking["affected_percentage"] = ranking["affected_percentage"].fillna(0.0).astype(float)

    email_duplicate_columns = metrics.get("email_duplicate_columns", pd.DataFrame())
    if not email_duplicate_columns.empty:
        ranking = ranking.merge(
            email_duplicate_columns[["column", "duplicate_percentage"]],
            on="column",
            how="left",
        )
    if "duplicate_percentage" not in ranking.columns:
        ranking["duplicate_percentage"] = 0.0
    ranking["duplicate_percentage"] = ranking["duplicate_percentage"].fillna(0.0).astype(float)

    ranking["duplicate_value_percentage"] = (
        ((LOW_UNIQUENESS_THRESHOLD - ranking["uniqueness_percentage"]).clip(lower=0))
        / LOW_UNIQUENESS_THRESHOLD
        * 100
    )

    ranking["missing_contribution"] = ranking["missing_percentage"] * 0.28
    ranking["validation_contribution"] = ranking["invalid_percentage"] * 0.32
    ranking["duplicate_email_contribution"] = ranking["duplicate_percentage"] * 0.16
    ranking["duplicate_value_contribution"] = ranking["duplicate_value_percentage"] * 0.14
    ranking["special_contribution"] = ranking["affected_percentage"] * 0.10

    ranking["risk_score"] = (
        ranking[
            [
                "missing_contribution",
                "validation_contribution",
                "duplicate_email_contribution",
                "duplicate_value_contribution",
                "special_contribution",
            ]
        ]
        .sum(axis=1)
        .clip(upper=100)
        .round()
        .astype(int)
    )

    def primary_issue_for_row(row) -> str:
        issue_contributions = {
            "Missing Values": row["missing_contribution"],
            row["validation_issue"] or "Validation Failures": row["validation_contribution"],
            "Duplicate Emails": row["duplicate_email_contribution"],
            "Duplicate Values": row["duplicate_value_contribution"],
            "Special Characters": row["special_contribution"],
        }
        strongest_issue = max(issue_contributions.items(), key=lambda item: item[1])
        return strongest_issue[0] if strongest_issue[1] > 0 else "No Major Issues"

    ranking["primary_issue"] = ranking.apply(primary_issue_for_row, axis=1)

    ranking["risk_level"] = ranking["risk_score"].apply(
        lambda value: "High" if value >= 75 else "Medium" if value >= 45 else "Low"
    )
    ranking = ranking.sort_values(
        by=["risk_score", "missing_percentage", "invalid_percentage", "affected_percentage"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    ranking["rank"] = range(1, len(ranking) + 1)
    return ranking[["rank", "column", "risk_level", "primary_issue", "risk_score"]].head(limit)


def render_column_risk_ranking(
    metrics: dict,
    *,
    limit: int = 5,
) -> None:
    """Render the column risk ranking table."""
    render_section_header(
        "Column Risk Ranking",
        "Columns ranked by overall quality risk based on all Clover quality checks.",
    )
    ranking = build_column_risk_ranking(metrics, limit=limit)
    if ranking.empty:
        st.info("No column risk analysis available.")
        return

    display_ranking = ranking.rename(
        columns={
            "column": "Column",
            "risk_level": "Risk",
            "primary_issue": "Primary Issue",
            "risk_score": "Score",
        }
    ).copy()
    risk_icons = {
        "High": "🔴 High",
        "Medium": "🟡 Medium",
        "Low": "🟢 Low",
    }
    display_ranking["Risk"] = display_ranking["Risk"].map(risk_icons).fillna(display_ranking["Risk"])
    display_ranking["Score"] = display_ranking["Score"].astype(int)
    display_ranking = display_ranking[["Column", "Risk", "Primary Issue", "Score"]]
    st.dataframe(display_ranking, use_container_width=True, hide_index=True)


def _load_reportlab_dependencies() -> dict:
    """Load reportlab with a fallback to the bundled Codex runtime."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from reportlab.pdfgen.canvas import Canvas
    except ImportError:
        import sys

        fallback_paths = [
            Path.home()
            / ".cache"
            / "codex-runtimes"
            / "codex-primary-runtime"
            / "dependencies"
            / "python",
        ]
        for fallback_path in fallback_paths:
            if fallback_path.exists() and str(fallback_path) not in sys.path:
                sys.path.append(str(fallback_path))

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from reportlab.pdfgen.canvas import Canvas

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


def build_quality_report_pdf(
    dataset_info: dict,
    metrics: dict,
    quality_score: float,
    top_issues: list[dict],
) -> bytes:
    """Build a polished Clover PDF report from the current analysis results."""
    column_risk_ranking = build_column_risk_ranking(metrics, limit=10)
    return build_quality_report_pdf_bytes(
        dataset_info,
        metrics,
        quality_score,
        top_issues,
        column_risk_ranking,
    )

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

    validation_overview = metrics.get("validation_overview", {})
    validation_results = metrics.get("validation_results", {})
    duplicate_summary = metrics.get("duplicate_summary", {})
    special_character_columns = metrics.get("special_character_columns", pd.DataFrame())
    column_risk_ranking = build_column_risk_ranking(metrics, limit=10)
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
    accent_green = colors.HexColor("#39D98A")

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
                        f"Analysis Version: Clover Dashboard",
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
        issues_data.append([paragraph("No major issues detected."), paragraph("The current dataset does not have major issues in the tracked Clover checks.")])
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
        missing_by_column[missing_by_column["column"] != "No data loaded"]
        .head(5)
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


def render_overview_page(dataset: pd.DataFrame | None, metrics: dict, quality_score: float, quality_status: dict, quality_recommendation: str, top_issues: list[dict]) -> None:
    """Render the enterprise overview dashboard."""
    render_section_header(
        "Executive Quality Overview",
        "A modern control plane for completeness, duplication, validation, and profiling across the uploaded dataset.",
    )
    main_left, main_center, main_right = st.columns(3, gap="large")
    with main_left:
        render_overview_chart_card(
            "clover-overview-card-gauge",
            "Quality Score Gauge",
            "Overall health signal for completeness, duplication, and field-level validation quality.",
            lambda: render_quality_score_gauge(
                quality_score,
                quality_status,
                quality_recommendation,
                chart_key="overview_quality_score_gauge",
                show_title=False,
                chart_height=320,
                compact_meta=True,
            ),
        )
    with main_center:
        render_overview_chart_card(
            "clover-overview-card-missing",
            "Missing Values Chart",
            "Column-level null pressure highlights where completeness cleanup should begin first.",
            lambda: render_missing_values_chart(
                metrics,
                chart_key="overview_missing_values_chart",
                show_title=False,
                chart_height=320,
            ),
        )
    with main_right:
        render_overview_chart_card(
            "clover-overview-card-duplicate",
            "Duplicate Analysis Donut",
            "A quick split between unique and duplicate records to expose deduplication risk immediately.",
            lambda: render_duplicate_donut_chart(
                metrics,
                chart_key="overview_duplicate_donut_chart",
                show_title=False,
                chart_height=320,
            ),
        )

    render_section_header(
        "Secondary Signals",
        "Prioritized issues and the highest-risk columns are surfaced together for faster triage.",
    )
    secondary_left, secondary_right = st.columns((1.05, 1.15), gap="large")
    with secondary_left:
        render_top_issues_panel(top_issues)
    with secondary_right:
        render_column_risk_ranking(metrics, limit=5)

    render_section_header(
        "Validation and Uniqueness",
        "Pass and fail distributions sit alongside uniqueness analysis to surface structural risk quickly.",
    )
    render_validation_quality_section(metrics, key_prefix="overview")
    render_uniqueness_analysis_chart(metrics, chart_key="overview_uniqueness_analysis_chart")

    render_preview_panel(dataset)


def render_column_profile_page(dataset: pd.DataFrame | None, metrics: dict) -> None:
    render_section_header(
        "Column Profile",
        "Profile every field across data type, missingness, uniqueness, and special-character exposure.",
    )
    profile = build_column_profile(dataset, metrics)
    if profile.empty:
        st.info("Upload a CSV file to generate a full column profile.")
        return
    st.dataframe(profile, use_container_width=True)
    render_uniqueness_analysis_chart(metrics, chart_key="column_profile_uniqueness_chart")


def render_missing_values_page(metrics: dict) -> None:
    render_section_header(
        "Missing Values",
        "Inspect completeness issues by field and prioritize the columns with the highest null pressure.",
    )
    render_missing_values_chart(metrics, chart_key="missing_values_page_chart")
    st.dataframe(metrics["missing_by_column"], use_container_width=True)


def render_duplicate_analysis_page(metrics: dict) -> None:
    render_section_header(
        "Duplicate Analysis",
        "Quantify duplicate impact and review the balance between unique and repeated rows.",
    )
    duplicate_summary = metrics.get("duplicate_summary", {})
    duplicate_tables = metrics.get("duplicate_tables", {})

    top_left, top_right = st.columns((0.95, 1.05), gap="large")
    with top_left:
        render_duplicate_donut_chart(metrics, chart_key="duplicate_analysis_donut")
    with top_right:
        render_section_header(
            "Duplicate Summary",
            "A quick operational view of exact duplicate rows, repeated email values, and total duplicate impact.",
        )
        render_duplicate_summary_cards(duplicate_summary, metrics["total_rows"])

    render_section_header(
        "Duplicate Previews",
        "Expand the relevant preview to inspect duplicate rows returned by the Clover backend.",
    )
    exact_duplicates = duplicate_tables.get("exact_duplicates")
    with st.expander(
        "Exact Row Duplicates Preview",
        expanded=False,
    ):
        if isinstance(exact_duplicates, pd.DataFrame) and not exact_duplicates.empty:
            st.dataframe(exact_duplicates.head(10), use_container_width=True)
        else:
            st.info("No exact row duplicates found.")

    email_duplicates = duplicate_tables.get("email_duplicates")
    with st.expander(
        "Email Duplicates Preview",
        expanded=False,
    ):
        if isinstance(email_duplicates, pd.DataFrame) and not email_duplicates.empty:
            st.dataframe(email_duplicates.head(10), use_container_width=True)
        else:
            st.info("No email duplicates found.")


def render_validation_preview_card(
    container_key: str,
    title: str,
    subtitle: str,
    preview_df: pd.DataFrame,
    empty_message: str,
) -> None:
    with st.container(key=container_key):
        st.markdown(
            f"""
            <div class="clover-validation-preview-head">
                <div class="clover-validation-preview-title">{title}</div>
                <div class="clover-validation-preview-subtitle">{subtitle}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if preview_df.empty:
            st.info(empty_message)
        else:
            st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)


def render_validation_checks_page(metrics: dict) -> None:
    render_section_header(
        "Validation Checks",
        "Review pass and fail counts for the core identity and contact fields detected in the uploaded file.",
    )
    render_validation_quality_section(metrics, key_prefix="validation_page")
    render_section_header(
        "Validation Summary",
        "A compact summary of how many values passed, failed, and contributed to the current validation risk.",
    )
    render_validation_summary_cards(metrics["validation_overview"])

    validation_previews = metrics.get("validation_previews", _empty_validation_previews())
    render_section_header(
        "Invalid Value Previews",
        "Review up to 10 backend-supplied invalid examples for each tracked validation category.",
    )
    preview_specs = [
        (
            "clover-validation-preview-email",
            "Invalid Emails",
            "Preview invalid email values returned by the Clover backend.",
            validation_previews.get("email", _empty_validation_preview_frame()),
            "No invalid emails found.",
        ),
        (
            "clover-validation-preview-name",
            "Invalid Names",
            "Preview invalid name values returned by the Clover backend.",
            validation_previews.get("name", _empty_validation_preview_frame()),
            "No invalid names found.",
        ),
        (
            "clover-validation-preview-username",
            "Invalid Usernames",
            "Preview invalid username values returned by the Clover backend.",
            validation_previews.get("username", _empty_validation_preview_frame()),
            "No invalid usernames found.",
        ),
        (
            "clover-validation-preview-dob",
            "Invalid Dates of Birth",
            "Preview invalid date values returned by the Clover backend.",
            validation_previews.get("dob", _empty_validation_preview_frame()),
            "No invalid dates of birth found.",
        ),
        (
            "clover-validation-preview-phone",
            "Invalid Phone Numbers",
            "Preview invalid phone values returned by the Clover backend.",
            validation_previews.get("phone", _empty_validation_preview_frame()),
            "No invalid phone numbers found.",
        ),
    ]

    for start in range(0, len(preview_specs), 2):
        row_specs = preview_specs[start:start + 2]
        columns = st.columns(len(row_specs), gap="large")
        for column, (container_key, title, subtitle, preview_df, empty_message) in zip(columns, row_specs):
            with column:
                render_validation_preview_card(
                    container_key,
                    title,
                    subtitle,
                    preview_df,
                    empty_message,
                )


def render_data_preview_page(dataset: pd.DataFrame | None) -> None:
    render_section_header(
        "Data Preview",
        "Inspect the full sample view while preserving the existing upload and profiling workflow.",
    )
    if dataset is None:
        st.warning("Upload a CSV file to preview its contents.")
    else:
        preview_mode = st.radio(
            "Preview rows",
            options=["First rows", "Last rows", "Random rows"],
            index=0,
            horizontal=True,
            key="clover_data_preview_mode",
        )

        if preview_mode == "Last rows":
            preview_df = dataset.tail(10)
        elif preview_mode == "Random rows":
            preview_df = dataset.sample(min(10, len(dataset))) if not dataset.empty else dataset
        else:
            preview_df = dataset.head(10)

        st.dataframe(preview_df, use_container_width=True)


def render_special_characters_page(metrics: dict) -> None:
    render_section_header(
        "Special Characters",
        "Surface text fields containing uncommon symbols that may require normalization or cleaning.",
    )
    if metrics["special_character_columns"].empty:
        st.info("No special-character issues were detected in the current dataset.")
    else:
        st.dataframe(metrics["special_character_columns"], use_container_width=True)


def render_reports_page(
    metrics: dict,
    quality_score: float,
    top_issues: list[dict],
    dataset_info: dict,
) -> None:
    render_section_header(
        "Reports",
        "A leadership-ready rollup of current risk, quality movement, and the highest-priority remediation areas.",
    )
    analysis_ready = (
        get_analysis_status().get("state") == "complete"
        and dataset_info.get("file_name") not in {None, "", "No dataset loaded"}
        and metrics.get("total_rows", 0) > 0
    )
    report_filename = build_report_filename(dataset_info.get("file_name", "dataset"))
    pdf_bytes = None
    pdf_error = None

    if analysis_ready:
        try:
            pdf_bytes = build_quality_report_pdf(
                dataset_info,
                metrics,
                quality_score,
                top_issues,
            )
        except Exception as exc:
            pdf_error = str(exc)

    if analysis_ready and pdf_bytes is not None:
        st.download_button(
            "Download Report (PDF)",
            data=pdf_bytes,
            file_name=report_filename,
            mime="application/pdf",
            key="clover_download_report_pdf",
            use_container_width=False,
        )
    else:
        st.download_button(
            "Download Report (PDF)",
            data=b"",
            file_name="Clover_Report_dataset.pdf",
            mime="application/pdf",
            key="clover_download_report_pdf_disabled",
            disabled=True,
            use_container_width=False,
        )
        if analysis_ready and pdf_error:
            st.caption(f"PDF generation is unavailable: {pdf_error}")
        else:
            st.caption("Upload and analyze a dataset before downloading a report.")

    report_left, report_right = st.columns((1.05, 1.1), gap="large")
    with report_left:
        render_top_issues_panel(top_issues)
    with report_right:
        render_column_risk_ranking(metrics, limit=5)
    st.markdown(
        '<div class="clover-preview-shell"><div class="clover-report-copy">'
        f"The current upload contains {metrics['total_rows']:,} rows across {metrics['total_columns']:,} columns. "
        f"Missing values total {metrics['missing_values']:,}, duplicate rows total {metrics['duplicate_rows']:,}, "
        f"and the computed quality score is {quality_score:.1f}/100. Use the specialized pages in the left navigation to drill into validation, missing-value, duplicate, and special-character issues."
        "</div></div>",
        unsafe_allow_html=True,
    )


def render_settings_page() -> None:
    render_section_header(
        "Settings",
        "Reference the current platform assumptions and monitored quality rules.",
    )
    st.write(
        {
            "supported_format": "CSV",
            "validation_checks": ["Email", "Name", "Username", "Date of Birth", "Phone"],
            "low_uniqueness_threshold_pct": 25,
            "theme": "Clover enterprise layout",
        }
    )


st.set_page_config(page_title="Clover", page_icon="C", layout="wide")
apply_theme()

if "clover_uploaded_file" not in st.session_state:
    st.session_state["clover_uploaded_file"] = None

if "clover_analysis_status" not in st.session_state:
    st.session_state["clover_analysis_status"] = get_default_analysis_status()

active_file = st.session_state.get("clover_uploaded_file")
dataset = None
metrics = build_empty_metrics()
quality_score = 0.0
quality_status = map_quality_status("FAIL", has_dataset=False)
quality_recommendation = build_quality_recommendation(metrics, None, quality_status)
top_issues = summarize_top_issues(metrics)
active_signature = None
if active_file is not None:
    active_signature = (active_file.name, active_file.size)
    cached_bundle = st.session_state.get("clover_backend_bundle")
    if (
        st.session_state.get("clover_backend_signature") == active_signature
        and cached_bundle
    ):
        dataset = cached_bundle["dataset"]
        metrics = cached_bundle["metrics"]
        quality_score = cached_bundle["quality_score"]
        quality_status = cached_bundle["quality_status"]
        quality_recommendation = cached_bundle["quality_recommendation"]
        top_issues = cached_bundle["top_issues"]
rendered_status = get_analysis_status()
if active_file is None and rendered_status.get("state") != "idle":
    rendered_status = set_analysis_status("idle", signature=None, title="Status")
dataset_info = build_dataset_info(active_file, metrics)
try:
    navigation, uploaded_file = render_sidebar(dataset_info)
except TypeError as exc:
    if "render_sidebar() takes 0 positional arguments but 1 was given" not in str(exc):
        raise
    navigation, uploaded_file = render_sidebar()

if uploaded_file is not None:
    st.session_state["clover_uploaded_file"] = uploaded_file
    active_file = uploaded_file

if active_file is not None:
    active_signature = (active_file.name, active_file.size)
    try:
        set_analysis_status(
            "running",
            signature=active_signature,
            title="Analyzing Dataset",
        )
        (
            dataset,
            metrics,
            _clover_results,
            quality_score,
            quality_status,
            quality_recommendation,
            top_issues,
        ) = analyze_uploaded_file(active_file)
        st.session_state["clover_last_analyzed_time"] = datetime.now()
        latest_status = set_analysis_status(
            "complete",
            signature=active_signature,
            title="Analysis Complete",
        )
        dataset_info = build_dataset_info(active_file, metrics)
        if (
            rendered_status.get("state") != latest_status["state"]
            or rendered_status.get("signature") != latest_status["signature"]
        ):
            st.rerun()
    except Exception as exc:
        latest_status = set_analysis_status(
            "error",
            signature=active_signature,
            title="Analysis Failed",
            message=f"Analysis failed: {exc}",
        )
        dataset_info = build_dataset_info(active_file, metrics)
        if (
            rendered_status.get("state") != latest_status["state"]
            or rendered_status.get("signature") != latest_status["signature"]
            or rendered_status.get("message") != latest_status["message"]
        ):
            st.rerun()
        st.error(f"Analysis failed: {exc}")
else:
    st.session_state.pop("clover_last_analyzed_time", None)
    set_analysis_status("idle", signature=None, title="Status")

render_top_header(dataset_info)
render_kpi_cards(metrics, quality_score, quality_status)

if dataset is None:
    st.info("Upload a CSV file from the sidebar to populate the dashboard.")

if navigation == "Overview":
    render_overview_page(
        dataset,
        metrics,
        quality_score,
        quality_status,
        quality_recommendation,
        top_issues,
    )
elif navigation == "Column Profile":
    render_column_profile_page(dataset, metrics)
elif navigation == "Missing Values":
    render_missing_values_page(metrics)
elif navigation == "Duplicate Analysis":
    render_duplicate_analysis_page(metrics)
elif navigation == "Validation Checks":
    render_validation_checks_page(metrics)
elif navigation == "Data Preview":
    render_data_preview_page(dataset)
elif navigation == "Special Characters":
    render_special_characters_page(metrics)
elif navigation == "Reports":
    render_reports_page(metrics, quality_score, top_issues, dataset_info)
elif navigation == "Settings":
    render_settings_page()

