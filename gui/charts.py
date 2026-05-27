# finproj - Chart builders for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

from formatting import format_compact_amount


def histogram_bins(count: int) -> int:
    if count <= 0:
        return 1
    return min(40, max(5, count // 2))


def quantile(values: list[float], pct: float) -> float:
    if not values:
        return float('nan')
    ordered = sorted(values)
    length = len(values)
    index = round(length * pct * length / (length + 1))
    return ordered[index]


def _compact_amount_tick(value: float, _position: float) -> str:
    return format_compact_amount(value)


def apply_compact_amount_axis(ax, axis: str = 'x') -> None:
    """Format monetary axis ticks with K, M, or B suffixes."""
    tick_axis = ax.xaxis if axis == 'x' else ax.yaxis
    tick_axis.set_major_formatter(FuncFormatter(_compact_amount_tick))
    tick_axis.set_major_locator(MaxNLocator(nbins=6, prune='both'))


def build_nav_distribution_figure(
    values: list[float],
    chart_year: int,
    *,
    title_suffix: str = '',
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(values, bins=histogram_bins(len(values)), color='#4C78A8', edgecolor='white')
    title = f'NAV distribution at year {chart_year}'
    if title_suffix:
        title += f' ({title_suffix})'
    ax.set_title(title)
    ax.set_xlabel('Net asset value')
    ax.set_ylabel('Number of paths')
    apply_compact_amount_axis(ax, axis='x')
    fig.tight_layout()
    return fig


def build_nav_percentile_figure(
    values: list[float],
    chart_year: int,
    *,
    title_suffix: str = '',
) -> plt.Figure | None:
    if not values:
        return None

    percentiles = {
        'P10': quantile(values, 0.10),
        'P50': quantile(values, 0.50),
        'P90': quantile(values, 0.90),
    }
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = list(percentiles.keys())
    heights = list(percentiles.values())
    ax.bar(labels, heights, color=['#F58518', '#54A24B', '#B279A2'])
    title = f'NAV percentiles at year {chart_year}'
    if title_suffix:
        title += f' ({title_suffix})'
    ax.set_title(title)
    ax.set_ylabel('Net asset value')
    apply_compact_amount_axis(ax, axis='y')
    fig.tight_layout()
    return fig
