# finproj - adapter between Viva cash-flow models and finproj projections
# Copyright (C) 2025-2026 Alex Scherer
#
# Viva (https://github.com/ajmscherer/viva) is an optional dependency installed
# via requirements-gui.txt. Deterministic flows are MIT-licensed; probabilistic
# features require a Viva Pro license after the 30-day evaluation period.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

try:
    import viva  # noqa: F401

    HAS_VIVA = True
except ImportError:
    HAS_VIVA = False


@dataclass(frozen=True)
class FlowSchedule:
    """Per-period contributions and withdrawals (period 1 = index 0)."""

    contributions: list[float]
    withdrawals: list[float]


def viva_flows_to_schedule(
    flows: list[dict],
    start_year: int,
    nb_years: int,
) -> FlowSchedule:
    """
    Convert Viva flow events into finproj period schedules.

    Sign convention when mapping Viva amounts to finproj:
      positive amount → contribution to the portfolio (e.g. insurance payout)
      negative amount → withdrawal from the portfolio
    """
    contributions = [0.0] * nb_years
    withdrawals = [0.0] * nb_years

    for flow in flows:
        flow_date = flow["date"]
        year = flow_date.year if hasattr(flow_date, "year") else int(flow_date)
        period = year - start_year + 1
        if period < 1 or period > nb_years:
            continue
        idx = period - 1
        amount = float(flow["amount"])
        if amount > 0:
            contributions[idx] += amount
        elif amount < 0:
            withdrawals[idx] += abs(amount)

    return FlowSchedule(contributions=contributions, withdrawals=withdrawals)


def resolve_viva_schedules(
    source: str,
    *,
    start_year: int,
    horizon_years: int,
    seed: Optional[int] = None,
    probabilistic: bool = False,
) -> FlowSchedule:
    """Parse Viva source and return per-period contribution/withdrawal schedules."""
    if not HAS_VIVA:
        raise ImportError(
            "viva is not installed. Install GUI dependencies with "
            "pip install -r requirements-gui.txt"
        )
    if not source.strip():
        raise ValueError("Viva source is empty")

    from viva import generateFlowEngine

    engine = generateFlowEngine(
        source,
        start_year=start_year,
        horizon_years=horizon_years,
    )
    if probabilistic:
        flows = engine.drawFlows(seed=seed)
    else:
        flows = engine.getFlows()

    return viva_flows_to_schedule(flows, start_year, horizon_years)


def default_viva_start_year() -> int:
    return date.today().year
