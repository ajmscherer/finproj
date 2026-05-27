# finproj - Display formatting helpers for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import html

SUMMARY_VALUE_COLUMNS = ('Mean', 'Std Dev', 'P10', 'P50', 'P90', 'Min', 'Max')


def format_compact_amount(value: float) -> str:
    """Format a number with K, M, or B suffix and one decimal place.

    Values below 1,000 are shown without a suffix (e.g. ``123.4``).
    """
    sign = '-' if value < 0 else ''
    amount = abs(value)

    if amount >= 1e9:
        return f'{sign}{amount / 1e9:.1f}B'
    if amount >= 1e6:
        return f'{sign}{amount / 1e6:.1f}M'
    if amount >= 1e3:
        return f'{sign}{amount / 1e3:.1f}K'
    return f'{sign}{amount:.1f}'


def render_summary_statistics_table(rows: list[dict[str, str]]) -> str:
    """Build an HTML table for summary statistics with centered numeric columns."""
    header = (
        '<thead><tr>'
        '<th>Metric</th>'
        + ''.join(f'<th class="fp-summary-num">{html.escape(name)}</th>' for name in SUMMARY_VALUE_COLUMNS)
        + '</tr></thead>'
    )
    body_rows = []
    for row in rows:
        cells = [f'<td>{html.escape(row["Metric"])}</td>']
        cells.extend(
            f'<td class="fp-summary-num">{html.escape(row[name])}</td>'
            for name in SUMMARY_VALUE_COLUMNS
        )
        body_rows.append(f'<tr>{"".join(cells)}</tr>')
    return f'<table class="fp-summary-table">{header}<tbody>{"".join(body_rows)}</tbody></table>'
