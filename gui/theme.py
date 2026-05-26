# finproj - UI theme tokens and CSS injection for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Edit THEME below to control typography, colors, spacing, and borders in the browser.
# Changes take effect after refreshing the Streamlit page.

from __future__ import annotations

from typing import Mapping

import streamlit as st

# ---------------------------------------------------------------------------
# Theme tokens — adjust these values to customize the GUI appearance
# ---------------------------------------------------------------------------
THEME: dict[str, str] = {
    # App title (st.title → h1)
    "title_font_size": "2.25rem",
    "title_font_weight": "600",
    "title_color": "#1f2937",
    "title_margin_top": "0",
    "title_margin_bottom": "0.35rem",
    "title_padding_top": "0.15rem",
    "title_line_height": "1.25",
    "title_letter_spacing": "-0.02em",
    # Section headers (st.header → h2, sidebar headers)
    "section_font_size": "1.2rem",
    "section_font_weight": "600",
    "section_color": "#111827",
    "section_margin_top": "0.25rem",
    "section_margin_bottom": "0.05rem",
    "section_padding_bottom": "0.35rem",
    "section_border_bottom": "1px solid #e5e7eb",
    # Subsection headers (st.subheader → h3)
    "subsection_font_size": "1.1rem",
    "subsection_font_weight": "600",
    "subsection_color": "#374151",
    "subsection_margin_top": "1.25rem",
    "subsection_margin_bottom": "0.5rem",
    # Tagline and captions
    "caption_font_size": "0.9rem",
    "caption_color": "#6b7280",
    "caption_margin_bottom": "0.1rem",
    # Body / labels on inputs
    "label_font_size": "0.875rem",
    "label_color": "#374151",
    "body_font_size": "1rem",
    "body_color": "#111827",
    # Bordered panels (e.g. portfolio read-only summary)
    "panel_border": "1px solid #d1d5db",
    "panel_border_radius": "0.5rem",
    "panel_background": "#f9fafb",
    "panel_padding": "0.75rem 1rem",
    "panel_margin_bottom": "0.5rem",
    # Metric cards inside panels
    "metric_label_size": "0.8rem",
    "metric_label_color": "#6b7280",
    "metric_value_size": "1.25rem",
    "metric_value_color": "#111827",
    # Sidebar
    "sidebar_background": "#f3f4f6",
    "sidebar_header_size": "1.1rem",
    "sidebar_header_color": "#111827",
    "sidebar_section_spacing": "1rem",
    # Buttons
    "button_border_radius": "0.375rem",
    "primary_button_background": "#2563eb",
    "primary_button_color": "#ffffff",
    # Main content spacing
    "block_gap": "0.75rem",
    "main_padding_top": "1rem",
}


def build_css(theme: Mapping[str, str] | None = None) -> str:
    t = {**THEME, **(theme or {})}
    return f"""
<style>
/* App title */
h1 {{
    font-size: {t["title_font_size"]};
    font-weight: {t["title_font_weight"]};
    color: {t["title_color"]};
    margin-top: {t["title_margin_top"]};
    margin-bottom: {t["title_margin_bottom"]};
    padding-top: {t["title_padding_top"]};
    line-height: {t["title_line_height"]};
    letter-spacing: {t["title_letter_spacing"]};
    overflow: visible;
}}
[data-testid="stMain"] [data-testid="stMarkdownContainer"]:has(h1),
[data-testid="stMain"] [data-testid="stHeading"] {{
    overflow: visible;
    line-height: {t["title_line_height"]};
}}

/* Section headers in main area */
section.main h2,
[data-testid="stMain"] h2 {{
    font-size: {t["section_font_size"]};
    font-weight: {t["section_font_weight"]};
    color: {t["section_color"]};
    margin-top: {t["section_margin_top"]};
    margin-bottom: {t["section_margin_bottom"]};
    padding-bottom: {t["section_padding_bottom"]};
    border-bottom: {t["section_border_bottom"]};
}}

/* Section title with inline action icon (edit/done) */
.st-key-portfolio_section_header,
.st-key-asset_classes_section_header {{
    margin-top: {t["section_margin_top"]};
    margin-bottom: {t["section_margin_bottom"]};
}}
.st-key-portfolio_section_header h2,
.st-key-asset_classes_section_header h2 {{
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}}
.st-key-portfolio_section_header [data-testid="stButton"],
.st-key-asset_classes_section_header [data-testid="stButton"] {{
    margin: 0;
    padding: 0;
}}
.st-key-portfolio_section_header [data-testid="stButton"] button,
.st-key-asset_classes_section_header [data-testid="stButton"] button {{
    min-height: 1.5rem;
    padding: 0.05rem 0.35rem;
    line-height: 1;
    margin-bottom: 0.35rem;
}}

/* Subsection headers */
section.main h3,
[data-testid="stMain"] h3 {{
    font-size: {t["subsection_font_size"]};
    font-weight: {t["subsection_font_weight"]};
    color: {t["subsection_color"]};
    margin-top: {t["subsection_margin_top"]};
    margin-bottom: {t["subsection_margin_bottom"]};
}}

/* Captions and helper text */
[data-testid="stCaptionContainer"] {{
    font-size: {t["caption_font_size"]};
    color: {t["caption_color"]};
    margin-bottom: {t["caption_margin_bottom"]};
}}

/* Input labels */
[data-testid="stWidgetLabel"] {{
    font-size: {t["label_font_size"]};
    color: {t["label_color"]};
}}

/* Bordered containers (portfolio summary, etc.) */
[data-testid="stVerticalBlockBorderWrapper"] {{
    border: {t["panel_border"]} !important;
    border-radius: {t["panel_border_radius"]} !important;
    background: {t["panel_background"]} !important;
    padding: {t["panel_padding"]} !important;
    margin-bottom: {t["panel_margin_bottom"]} !important;
}}

/* Metrics */
[data-testid="stMetricLabel"] {{
    font-size: {t["metric_label_size"]};
    color: {t["metric_label_color"]};
}}
[data-testid="stMetricValue"] {{
    font-size: {t["metric_value_size"]};
    color: {t["metric_value_color"]};
    font-weight: 600;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {t["sidebar_background"]};
}}
[data-testid="stSidebar"] h2 {{
    font-size: {t["sidebar_header_size"]};
    color: {t["sidebar_header_color"]};
    border-bottom: none;
    margin-top: {t["sidebar_section_spacing"]};
    margin-bottom: 0.5rem;
    padding-bottom: 0;
}}
[data-testid="stSidebar"] [data-testid="stHeader"] {{
    font-size: {t["sidebar_header_size"]};
}}

/* Primary button */
[data-testid="stBaseButton-primary"] {{
    border-radius: {t["button_border_radius"]};
    background-color: {t["primary_button_background"]};
    color: {t["primary_button_color"]};
}}

/* General main-area spacing */
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div {{
    gap: {t["block_gap"]};
}}
[data-testid="stMain"] .block-container {{
    padding-top: {t["main_padding_top"]};
}}

/* Markdown body text in main area */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {{
    font-size: {t["body_font_size"]};
    color: {t["body_color"]};
}}
</style>
"""


def inject_theme(theme: Mapping[str, str] | None = None) -> None:
    """Inject custom CSS into the Streamlit page."""
    st.markdown(build_css(theme), unsafe_allow_html=True)
