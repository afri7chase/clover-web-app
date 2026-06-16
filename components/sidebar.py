import streamlit as st


NAVIGATION_OPTIONS = [
    "Overview",
    "Column Profile",
    "Missing Values",
    "Duplicate Analysis",
    "Validation Checks",
    "Data Preview",
    "Special Characters",
    "Reports",
    "Settings",
]

NAVIGATION_ICONS = {
    "Overview": ":material/home:",
    "Column Profile": ":material/table_chart:",
    "Missing Values": ":material/bar_chart:",
    "Duplicate Analysis": ":material/groups:",
    "Validation Checks": ":material/shield:",
    "Data Preview": ":material/visibility:",
    "Special Characters": ":material/auto_awesome:",
    "Reports": ":material/description:",
    "Settings": ":material/settings:",
}


def _nav_slug(label: str) -> str:
    return label.lower().replace(" ", "-")


def render_sidebar(dataset_info=None):
    """Render the left navigation and file uploader."""
    if st.session_state.get("clover_nav") not in NAVIGATION_OPTIONS:
        st.session_state["clover_nav"] = "Overview"

    with st.sidebar:
        st.markdown(
            """
            <div class="clover-sidebar-brand">
                <div class="clover-sidebar-brand-mark">&#127808;</div>
                <div>
                    <div class="clover-sidebar-brand-name">Clover</div>
                    <div class="clover-sidebar-brand-subtitle">Clover Dataset Quality Assessment</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="clover-sidebar-section-label">Navigation</div>',
            unsafe_allow_html=True,
        )
        for item in NAVIGATION_OPTIONS:
            slug = _nav_slug(item)
            is_active = st.session_state["clover_nav"] == item
            container_key = (
                f"clover-nav-active-{slug}" if is_active else f"clover-nav-item-{slug}"
            )
            with st.container(key=container_key):
                if st.button(
                    item,
                    key=f"clover_sidebar_nav_{slug}",
                    icon=NAVIGATION_ICONS[item],
                    use_container_width=True,
                ):
                    if st.session_state["clover_nav"] != item:
                        st.session_state["clover_nav"] = item
                        st.rerun()

        with st.container(key="clover-sidebar-upload-card"):
            st.markdown(
                '<div class="clover-sidebar-section-label">Upload CSV</div>',
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Upload CSV",
                type=["csv"],
                label_visibility="collapsed",
            )

        if dataset_info is None:
            dataset_info = {
                "rows": "-",
                "columns": "-",
                "file_size": "-",
                "uploaded_by": "Current session",
                "upload_date": "Not uploaded",
                "upload_complete": False,
            }

        st.markdown(
            f"""
            <div class="clover-sidebar-card">
                <div class="clover-sidebar-card-title">Dataset Info</div>
                <div class="clover-sidebar-metadata">
                    <div><span>Rows</span><strong>{dataset_info.get("rows", "-")}</strong></div>
                    <div><span>Columns</span><strong>{dataset_info.get("columns", "-")}</strong></div>
                    <div><span>File Size</span><strong>{dataset_info.get("file_size", "-")}</strong></div>
                    <div><span>Uploaded By</span><strong>{dataset_info.get("uploaded_by", "Current session")}</strong></div>
                    <div><span>Last Updated</span><strong>{dataset_info.get("upload_date", "Not uploaded")}</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if dataset_info.get("upload_complete", False):
            st.markdown(
                """
                <div class="clover-sidebar-status-card">
                    <div class="clover-sidebar-status-title">&#10003; Analysis Complete</div>
                    <div class="clover-sidebar-status-copy">All checks finished successfully.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="clover-sidebar-card clover-sidebar-pending-card">
                    <div class="clover-sidebar-card-title">Status</div>
                    <div class="clover-sidebar-tip-copy">Upload a CSV file to run dataset profiling and validation checks.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="clover-sidebar-tip-card">
                <div class="clover-sidebar-tip-title">&#128161; Tip</div>
                <div class="clover-sidebar-tip-copy">Click on any chart for more details</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["clover_nav"], uploaded_file

