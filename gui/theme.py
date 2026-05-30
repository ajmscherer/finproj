# finproj - UI theme tokens and CSS injection for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.
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
    "title_margin_top": "0.25rem",
    "title_margin_bottom": "0.35rem",
    "title_padding_top": "0.35rem",
    "title_line_height": "1.35",
    "title_letter_spacing": "-0.02em",
    # Section headers (st.header → h2, sidebar headers)
    "section_font_size": "1.2rem",
    "section_font_weight": "600",
    "section_color": "#111827",
    "section_margin_top": "0.035rem",
    "section_margin_bottom": "0.025rem",
    "section_padding_bottom": "0.035rem",
    "section_border_bottom": "1px solid #e5e7eb",
    # Subsection headers (st.subheader → h3)
    "subsection_font_size": "1.1rem",
    "subsection_font_weight": "600",
    "subsection_color": "#374151",
    "subsection_margin_top": "0.25rem",
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
    # Bordered panels (sections 1–3 and other bordered containers)
    "panel_border": "1px solid #d1d5db",
    "panel_border_radius": "0.5rem",
    "panel_background": "#f9fafb",  # read-only section background
    "panel_background_edit": "#fffbeb",  # edit-mode section background
    "panel_padding": "0.75rem 1rem",
    "panel_margin_bottom": "0.5rem",
    # Section edit/done icon buttons (hidden by default; click panel to toggle mode)
    "section_mode_buttons_visible": "false",
    # Metric cards inside panels
    "metric_label_size": "0.8rem",
    "metric_label_color": "#6b7280",
    "metric_value_size": "1.25rem",
    "metric_value_color": "#111827",
    "return_metric_line_gap": "0.35rem",
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
    "main_padding_top": "1.25rem",
    # Title background bandeau (three lines; positions match SVG viewBox 0 0 10 1)
    "header_band_height": "4rem",
    "header_band_color": "green",
    "header_band_opacity": "1",
    "header_band_line_height_pct": "15%",
    "header_band_line_1_top_pct": "40%",
    "header_band_line_2_top_pct": "70%",
    "header_band_line_3_top_pct": "100%",
    # Summary statistics table
    "summary_table_font_size": "0.875rem",
    "summary_table_header_background": "#f9fafb",
    "summary_table_header_color": "#374151",
    "summary_table_border": "1px solid #e5e7eb",
    "summary_table_cell_padding": "0.5rem 0.75rem",
}


def _band_line_gradient(theme: Mapping[str, str]) -> str:
    color = theme["header_band_color"]
    opacity = theme["header_band_opacity"]
    if color.startswith("#"):
        hex_color = color.lstrip("#")
        r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return (
            f"linear-gradient(to right, rgba({r}, {g}, {b}, 0) 0%, "
            f"rgba({r}, {g}, {b}, {opacity}) 100%)"
        )
    return f"linear-gradient(to right, transparent 0%, {color} 100%)"


def build_css(theme: Mapping[str, str] | None = None) -> str:
    t = {**THEME, **(theme or {})}
    band_line = _band_line_gradient(t)
    line_height = t["header_band_line_height_pct"]
    show_section_mode_buttons = t.get("section_mode_buttons_visible", "false") == "true"
    section_mode_button_hide_css = ""
    if not show_section_mode_buttons:
        section_mode_button_hide_css = """
/* Hidden section edit/done triggers (panel click toggles mode; set section_mode_buttons_visible=true to show) */
.st-key-portfolio_assumptions_edit,
.st-key-portfolio_assumptions_done,
.st-key-asset_allocation_edit,
.st-key-asset_allocation_done,
.st-key-return_assumptions_edit,
.st-key-return_assumptions_done {
    display: none !important;
}
"""
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
[data-testid="stMain"] [data-testid="stHeading"] {{
    overflow: visible !important;
    padding-top: 0.25rem;
    padding-bottom: 0.15rem;
}}
[data-testid="stMain"] [data-testid="stMarkdownContainer"]:has(h1) {{
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
.st-key-portfolio_allocation_section_header,
.st-key-assets_performance_and_vol_header {{
    margin-top: {t["section_margin_top"]};
    margin-bottom: {t["section_margin_bottom"]};
}}
.st-key-portfolio_section_header h2,
.st-key-portfolio_allocation_section_header h2,
.st-key-assets_performance_and_vol_header h2 {{
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}}
.st-key-portfolio_section_header [data-testid="stButton"],
.st-key-portfolio_allocation_section_header [data-testid="stButton"],
.st-key-assets_performance_and_vol_header [data-testid="stButton"] {{
    margin: 0;
    padding: 0;
}}
.st-key-portfolio_section_header [data-testid="stButton"] button,
.st-key-portfolio_allocation_section_header [data-testid="stButton"] button,
.st-key-assets_performance_and_vol_header [data-testid="stButton"] button {{
    min-height: 1.5rem;
    padding: 0.05rem 0.35rem;
    line-height: 1;
    margin-bottom: 0.35rem;
}}

/* Clickable sections 1–3 (bordered panel; JS forwards clicks to edit/done buttons) */
.st-key-portfolio_section:has(.st-key-portfolio_assumptions_edit),
.st-key-portfolio_allocation_section:has(.st-key-asset_allocation_edit),
.st-key-assets_performance_and_vol:has(.st-key-return_assumptions_edit),
.st-key-portfolio_section:has(.st-key-portfolio_assumptions_edit) [data-testid="stVerticalBlockBorderWrapper"],
.st-key-portfolio_allocation_section:has(.st-key-asset_allocation_edit) [data-testid="stVerticalBlockBorderWrapper"],
.st-key-assets_performance_and_vol:has(.st-key-return_assumptions_edit) [data-testid="stVerticalBlockBorderWrapper"] {{
    cursor: pointer;
    background: {t["panel_background"]} !important;
}}
.st-key-portfolio_section:has(.st-key-portfolio_assumptions_done),
.st-key-portfolio_allocation_section:has(.st-key-asset_allocation_done),
.st-key-assets_performance_and_vol:has(.st-key-return_assumptions_done),
.st-key-portfolio_section:has(.st-key-portfolio_assumptions_done) [data-testid="stVerticalBlockBorderWrapper"],
.st-key-portfolio_allocation_section:has(.st-key-asset_allocation_done) [data-testid="stVerticalBlockBorderWrapper"],
.st-key-assets_performance_and_vol:has(.st-key-return_assumptions_done) [data-testid="stVerticalBlockBorderWrapper"] {{
    cursor: pointer;
    background: {t["panel_background_edit"]} !important;
}}
.st-key-portfolio_section:has(.st-key-portfolio_assumptions_edit):hover,
.st-key-portfolio_allocation_section:has(.st-key-asset_allocation_edit):hover,
.st-key-assets_performance_and_vol:has(.st-key-return_assumptions_edit):hover,
.st-key-portfolio_section:has(.st-key-portfolio_assumptions_done):hover,
.st-key-portfolio_allocation_section:has(.st-key-asset_allocation_done):hover,
.st-key-assets_performance_and_vol:has(.st-key-return_assumptions_done):hover {{
    border-color: #cbd5e1 !important;
}}
.st-key-portfolio_section_header [data-testid="stButton"],
.st-key-portfolio_allocation_section_header [data-testid="stButton"],
.st-key-assets_performance_and_vol_header [data-testid="stButton"] {{
    position: relative;
    z-index: 2;
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
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMetric"] {{
    gap: {t["return_metric_line_gap"]};
}}
[data-testid="stMetricLabel"] {{
    font-size: {t["metric_label_size"]};
    color: {t["metric_label_color"]};
}}
[data-testid="stMetricValue"] {{
    font-size: {t["metric_value_size"]};
    color: {t["metric_value_color"]};
    font-weight: 600;
    line-height: 1.2;
}}

/* Return assumptions read-only: match section 1/2 metric typography */
[data-testid="stVerticalBlockBorderWrapper"] .fp-return-metric-stack {{
    display: flex;
    flex-direction: column;
    gap: {t["return_metric_line_gap"]};
}}
[data-testid="stVerticalBlockBorderWrapper"] .fp-return-metric-label {{
    font-size: {t["metric_label_size"]} !important;
    color: {t["metric_label_color"]} !important;
    font-weight: 400 !important;
    line-height: 1.2;
    margin: 0;
}}
[data-testid="stVerticalBlockBorderWrapper"] .fp-return-metric-value {{
    font-size: {t["metric_value_size"]} !important;
    color: {t["metric_value_color"]} !important;
    font-weight: 600 !important;
    line-height: 1.2;
    margin: 0;
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

/* Title background bandeau — full-width SVG behind finproj */
.st-key-app_header,
.st-key-app_header_title {{
    overflow: visible !important;
}}
.st-key-app_header_title {{
    position: relative;
}}
.st-key-app_header_title [data-testid="stHeading"] {{
    position: relative;
    z-index: 1;
    overflow: visible !important;
}}
.st-key-app_header_title [data-testid="stHeading"]::before {{
    content: "";
    position: absolute;
    z-index: 0;
    left: 50%;
    width: 100vw;
    margin-left: -50vw;
    top: 50%;
    transform: translateY(-50%);
    height: {t["header_band_height"]};
    pointer-events: none;
    background-image: {band_line}, {band_line}, {band_line};
    background-size: 100% {line_height};
    background-repeat: no-repeat;
    background-position:
        0 {t["header_band_line_1_top_pct"]},
        0 {t["header_band_line_2_top_pct"]},
        0 {t["header_band_line_3_top_pct"]};
}}
.st-key-app_header_title [data-testid="stHeading"] h1 {{
    position: relative;
    z-index: 1;
    background: transparent;
}}

/* Summary statistics table */
.fp-summary-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: {t["summary_table_font_size"]};
    margin-bottom: 0.75rem;
}}
.fp-summary-table th,
.fp-summary-table td {{
    padding: {t["summary_table_cell_padding"]};
    border-bottom: {t["summary_table_border"]};
    vertical-align: middle;
}}
.fp-summary-table th {{
    font-weight: 600;
    color: {t["summary_table_header_color"]};
    background: {t["summary_table_header_background"]};
    text-align: left;
}}
.fp-summary-table th.fp-summary-num,
.fp-summary-table td.fp-summary-num {{
    text-align: center;
}}

/* Markdown body text in main area */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {{
    font-size: {t["body_font_size"]};
    color: {t["body_color"]};
}}
{section_mode_button_hide_css}
</style>
"""


def inject_theme(theme: Mapping[str, str] | None = None) -> None:
    """Inject custom CSS into the Streamlit page."""
    st.markdown(build_css(theme), unsafe_allow_html=True)
