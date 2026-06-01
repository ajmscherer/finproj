# finproj - Chart builders for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.

from __future__ import annotations

import math

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
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
) -> Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(
        values, bins=histogram_bins(len(values)), color="#4C78A8", edgecolor="white"
    )
    title = f"NAV distribution at year {chart_year}"
    if title_suffix:
        title += f" ({title_suffix})"
    ax.set_title(title)
    ax.set_xlabel("Net asset value")
    ax.set_ylabel("Number of projections")
    apply_compact_amount_axis(ax, axis="x")
    fig.tight_layout()
    return fig


def build_nav_percentile_figure(
    values: list[float],
    chart_year: int,
    *,
    title_suffix: str = "",
) -> Figure | None:
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


def extract_latest_projection_curve(nav_fan) -> list[float]:
    """End-of-year NAV for the most recently completed simulation projection."""
    years = nav_fan.years()
    values_by_year = nav_fan.values_by_year
    return [
        values_by_year[year][-1] if values_by_year.get(year) else float("nan")
        for year in years
    ]


def build_nav_fan_figure(
    nav_fan,
    *,
    projections_done: int | None = None,
    projections_total: int | None = None,
    latest_projection_curve: list[float] | None = None,
) -> Figure | None:
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

    if latest_projection_curve is not None:
        ax.plot(
            years,
            latest_projection_curve,
            linestyle="-",
            linewidth=1.5,
            color="#DC2626",
            zorder=5,
        )

    title = "NAV fan chart"
    if projections_done is not None and projections_total is not None:
        title += f" ({projections_done:,} / {projections_total:,} projections)"
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Net asset value")
    ax.set_xticks(years)
    apply_compact_amount_axis(ax, axis="y")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def build_pie_chart(
    allocation: dict[str, float],
    labels_by_id: dict[str, str],
    *,
    title: str = "Allocation",
) -> Figure | None:
    labels: list[str] = []
    values: list[float] = []
    for asset_id, weight in allocation.items():
        if weight <= 0:
            continue
        labels.append(labels_by_id.get(asset_id, asset_id))
        values.append(weight)
    if not values:
        return None

    fig, ax = plt.subplots(figsize=(4, 4))
    fig.patch.set_facecolor("none")
    ax.set_facecolor("none")
    ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
    )
    ax.set_title(title)
    fig.tight_layout()
    return fig


def _normal_pdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 1e-9:
        return 1.0 if abs(x - mu) <= 1e-9 else 0.0
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2.0 * math.pi))


def _linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step = (stop - start) / (count - 1)
    return [start + index * step for index in range(count)]


def build_mu_sigma_range_figure(
    mu_sigma: dict[str, tuple[float, float]],
    labels_by_id: dict[str, str],
    *,
    asset_order: list[str] | None = None,
    title: str = "",
    curve_points: int = 200,
    sigma_span: float = 4.0,
) -> Figure | None:
    order = asset_order or list(mu_sigma.keys())
    rows: list[tuple[str, float, float]] = []
    for asset_id in order:
        if asset_id not in mu_sigma:
            continue
        mu, sigma = mu_sigma[asset_id]
        rows.append((labels_by_id.get(asset_id, asset_id), mu, max(sigma, 0.0)))

    if not rows:
        return None

    fig_height = max(2.5, len(rows) * 0.65)
    fig, ax = plt.subplots(figsize=(5, fig_height))
    fig.patch.set_facecolor("none")
    ax.set_facecolor("none")

    x_min = min(mu - sigma_span * max(sigma, 1e-9) for _, mu, sigma in rows)
    x_max = max(mu + sigma_span * max(sigma, 1e-9) for _, mu, sigma in rows)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0

    for index, (_, mu, sigma) in enumerate(rows):
        if sigma <= 1e-9:
            ax.plot([mu, mu], [index - 0.35, index + 0.35], color="#4C78A8", linewidth=2)
            continue

        xs = _linspace(mu - sigma_span * sigma, mu + sigma_span * sigma, curve_points)
        pdf = [_normal_pdf(x, mu, sigma) for x in xs]
        peak = max(pdf)
        if peak <= 0:
            continue
        height = 0.45
        scaled = [value / peak * height for value in pdf]
        lower = [index - value for value in scaled]
        upper = [max(lower)] * len(scaled) #[index + value for value in scaled]
        ax.fill_between(xs, lower, upper, color="#4C78A8", alpha=0.35, linewidth=0)
        ax.plot(xs, upper, color="#4C78A8", linewidth=1.5)
        ax.plot(xs, lower, color="#4C78A8", linewidth=1.5)
        ax.plot(
            [mu, mu],
            [index - height, index],
            color="red",
            linewidth=2.5,
            solid_capstyle="butt",
            zorder=4,
        )
        ax.grid(True,  axis="x")
    ax.set_title("Return distribution")
    ax.set_yticks(list(range(len(rows))))
    ax.set_yticklabels([label for label, _, _ in rows])
    ax.set_xlabel("Return (%)")
    ax.set_xlim(x_min, x_max)
    if title:
        ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig
