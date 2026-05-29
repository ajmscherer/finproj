# finproj - Chart builders for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.

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
        return float("nan")
    ordered = sorted(values)
    length = len(values)
    index = round(length * pct * length / (length + 1))
    return ordered[index]


def _compact_amount_tick(value: float, _position: float) -> str:
    return format_compact_amount(value)


def apply_compact_amount_axis(ax, axis: str = "x") -> None:
    """Format monetary axis ticks with K, M, or B suffixes."""
    tick_axis = ax.xaxis if axis == "x" else ax.yaxis
    tick_axis.set_major_formatter(FuncFormatter(_compact_amount_tick))
    tick_axis.set_major_locator(MaxNLocator(nbins=6, prune="both"))


def build_nav_distribution_figure(
    values: list[float],
    chart_year: int,
    *,
    title_suffix: str = "",
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(
        values, bins=histogram_bins(len(values)), color="#4C78A8", edgecolor="white"
    )
    title = f"NAV distribution at year {chart_year}"
    if title_suffix:
        title += f" ({title_suffix})"
    ax.set_title(title)
    ax.set_xlabel("Net asset value")
    ax.set_ylabel("Number of paths")
    apply_compact_amount_axis(ax, axis="x")
    fig.tight_layout()
    return fig


def build_nav_percentile_figure(
    values: list[float],
    chart_year: int,
    *,
    title_suffix: str = "",
) -> plt.Figure | None:
    if not values:
        return None

    percentiles = {
        "P10": quantile(values, 0.10),
        "P50": quantile(values, 0.50),
        "P90": quantile(values, 0.90),
    }
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = list(percentiles.keys())
    heights = list(percentiles.values())
    ax.bar(labels, heights, color=["#F58518", "#54A24B", "#B279A2"])
    title = f"NAV percentiles at year {chart_year}"
    if title_suffix:
        title += f" ({title_suffix})"
    ax.set_title(title)
    ax.set_ylabel("Net asset value")
    apply_compact_amount_axis(ax, axis="y")
    fig.tight_layout()
    return fig


def _nav_fan_density_bands(band_count: int = 15) -> list[tuple[float, float]]:
    """Symmetric percentile pairs from wide (outer) to narrow (inner)."""
    step = 0.5 / (band_count + 1)
    tails = [round(step * i, 4) for i in range(1, band_count + 1)]
    return [(tail, round(1.0 - tail, 4)) for tail in tails]


def _nav_fan_band_style(band_index: int, band_count: int) -> tuple[str, float]:
    """Pale yellow outside, richer yellow toward the median."""
    if band_count <= 1:
        t = 1.0
    else:
        t = band_index / (band_count - 1)
    alpha = 0.07 + 0.50 * t
    return "#FACC15", alpha


def extract_latest_path_curve(nav_fan) -> list[float]:
    """End-of-year NAV for the most recently completed simulation path."""
    years = nav_fan.years()
    values_by_year = nav_fan.values_by_year
    return [
        values_by_year[year][-1] if values_by_year.get(year) else float("nan")
        for year in years
    ]


def build_nav_fan_figure(
    nav_fan,
    *,
    paths_done: int | None = None,
    paths_total: int | None = None,
    latest_path_curve: list[float] | None = None,
) -> plt.Figure | None:
    years = nav_fan.years()
    if not years or not nav_fan.values_by_year.get(years[0]):
        return None

    density_bands = _nav_fan_density_bands()
    p10 = nav_fan.quantile_curve(0.10)
    p50 = nav_fan.quantile_curve(0.50)
    p90 = nav_fan.quantile_curve(0.90)
    mean = nav_fan.mean_curve()

    fig, ax = plt.subplots(figsize=(6, 4))

    ax.plot(
        years,
        mean,
        linestyle="-",
        linewidth=2.5,
        color="#4C78A8",
        label="Mean",
        zorder=4,
    )

    band_count = len(density_bands)
    for index, (lower_pct, upper_pct) in enumerate(density_bands):
        lower = nav_fan.quantile_curve(lower_pct)
        upper = nav_fan.quantile_curve(upper_pct)
        color, alpha = _nav_fan_band_style(index, band_count)
        label = (
            "Probability density (darker = more likely)"
            if index == band_count - 1
            else None
        )
        ax.fill_between(
            years,
            lower,
            upper,
            color=color,
            alpha=alpha,
            label=label,
            zorder=1,
            linewidth=0,
        )

    ax.plot(
        years, p10, linestyle=":", linewidth=1.5, color="#F58518", label="First decile (P10)", zorder=2
    )
    ax.plot(
        years, p90, linestyle=":", linewidth=1.5, color="#54A24B", label="Last decile (P90)", zorder=2
    )
    ax.plot(
        years,
        p50,
        linestyle=":",
        linewidth=1.5,
        color="#4C78A8",
        label="Median (P50)",
        zorder=3,
    )

    if latest_path_curve is not None:
        ax.plot(
            years,
            latest_path_curve,
            linestyle="-",
            linewidth=1.5,
            color="#DC2626",
            zorder=5,
        )

    title = "NAV fan chart"
    if paths_done is not None and paths_total is not None:
        title += f" ({paths_done:,} / {paths_total:,} paths)"
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Net asset value")
    ax.set_xticks(years)
    apply_compact_amount_axis(ax, axis="y")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
