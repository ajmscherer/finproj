# finproj - Stochastic Financial Projections to optimize asset management
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alternative licensing under a commercial license is available; see LICENSE
# and COMMERCIAL-LICENSE.md in the project root.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import copy
import html
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

# from click_panel import ClickPanelRegistry
from section import Section, SectionContentEditable

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "code"))

import viva_summary as _viva_summary_module
from asset_classes import AssetCatalog, AssetClass, default_asset_catalog, slugify
from charts import (
    build_mu_sigma_range_figure,
    build_nav_distribution_figure,
    build_nav_fan_figure,
    build_pie_chart,
    extract_latest_projection_curve,
)
from formatting import (
    format_compact_amount,
    render_summary_statistics_table,
)
from inv_proj import cv
from inv_proj_runner import (
    DEFAULT_NEW_ASSET_RISK,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RISK_CORRELATION,
    DEFAULT_RISK_MIX_PRESETS,
    DEFAULT_RISK_PARAM,
    RunResult,
    find_config_problems,
    investable_asset_ids,
    normalize_correlation_pair,
    return_model_asset_ids,
    success_rate,
    validate_allocation,
    validate_correlation,
)
from theme import THEME, inject_theme
from viva_adapter import HAS_VIVA

from assumptions import DEFAULT_ASSUMPTIONS_DIR, Assumptions

importlib.reload(_viva_summary_module)
try_summarize_viva_source = _viva_summary_module.try_summarize_viva_source
format_viva_program_summary_lines = (
    _viva_summary_module.format_viva_program_summary_lines
)
import inv_proj
import inv_proj_runner


def _nav_key(year: int) -> str:
    return f"Net Asset Value @ year {year:>2}"


def _chart_update_interval(nb_projections: int) -> int:
    return max(20, nb_projections // 100)


PRODUCT_ABOUT_HELP = (
    "finproj is a local Monte Carlo simulation tool for investment portfolios. "
    "Configure your starting capital, annual withdrawals, cash buffer, asset allocation, "
    "expected returns, volatility, and correlations — then run thousands of independent "
    "projections to explore how your net asset value might evolve. "
    "Use the summary statistics and charts to compare strategies and assess risks, such as "
    "projections ending with negative NAV or falling below your initial capital. "
    "Everything runs on your machine; your financial assumptions never leave your computer."
)


def _render_app_header() -> None:
    caption = (
        "Stochastic financial projections — runs locally on your machine — "
        "[Copyright © 2025–2026 Alex Scherer]"
        "(https://github.com/ajmscherer/finproj/blob/main/README.md)"
        "\n\n⚠️Demo only — do not enter real financial data or personal information."
    )

    with st.container(key="app_header"):
        with st.container(key="app_header_title"):
            st.title("finproj", help=PRODUCT_ABOUT_HELP)
        st.caption(caption)


def _correlation_pairs(catalog: AssetCatalog) -> list[tuple[str, str]]:
    asset_order = return_model_asset_ids(catalog)
    pairs = []
    for i, left in enumerate(asset_order):
        for right in asset_order[i + 1 :]:
            pairs.append((left, right))
    return pairs


def _investable_assets(catalog: AssetCatalog) -> list[AssetClass]:
    """Investable assets shown in section 2 (excludes Cash / liquidity buffer)."""
    liquidity_id = catalog.liquidity_id()
    return [
        asset
        for asset in catalog.assets
        if asset.id in investable_asset_ids(catalog) and asset.id != liquidity_id
    ]


def _default_correlation_values(catalog: AssetCatalog) -> dict[tuple[str, str], float]:
    asset_order = return_model_asset_ids(catalog)
    asset_ids = set(asset_order)
    values = {pair: 0.0 for pair in _correlation_pairs(catalog)}
    for pair, rho in DEFAULT_RISK_CORRELATION.items():
        left, right = pair
        if left not in asset_ids or right not in asset_ids:
            continue
        canonical = normalize_correlation_pair(left, right, asset_order)
        if canonical in values:
            values[canonical] = rho
    return values


def _init_mu_sigma_keys(catalog: AssetCatalog) -> None:
    for asset_id in return_model_asset_ids(catalog):
        defaults = DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0]
        st.session_state.setdefault(f"mu_{asset_id}", float(defaults["mu"]))
        st.session_state.setdefault(f"sigma_{asset_id}", float(defaults["sigma"]))


def _init_correlation_keys(catalog: AssetCatalog) -> None:
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(
            left, right, return_model_asset_ids(catalog)
        )
        key = f"corr_{canonical[0]}_{canonical[1]}"
        st.session_state.setdefault(
            key, float(st.session_state.correlation_values.get(canonical, 0.0))
        )


PORTFOLIO_FIELD_DEFAULTS = {
    "description": "",
    "initial_capital": "1M",
    "contributions": "0k",
    "withdrawals": "50k",
    "cash_buffer": "150k",
    "max_year": 20,
    "nb_projections": 2000,
    "viva_source": "",
    "contributions_from_period": 1,
    "contributions_to_period": 20,
    "withdrawals_from_period": 1,
    "withdrawals_to_period": 20,
}

PORTFOLIO_FIELD_HELP = {
    "description": (
        "Optional free-text description of this simulation scenario: "
        "what you are testing, who it is for, or notes for later reference."
    ),
    "initial_capital": (
        "Total portfolio value at the start of each simulation projection. "
        "The cash buffer is set aside first; the rest is invested per your allocation. "
        "Supports shorthand such as 1M, 40k, or 2.5B."
    ),
    "contributions": (
        "Amount contributed to the portfolio every year. "
        "Contributions are added to the initial capital. "
        "Supports shorthand such as 40k or 50k. Must be positive."
    ),
    "withdrawals": (
        "Amount withdrawn from the portfolio every year. "
        "Withdrawals are taken from the cash buffer first; any shortfall is covered by selling bonds. "
        "Supports shorthand such as 40k or 50k. Must be positive."
    ),
    "cash_buffer": (
        "Target cash reserve held in the liquidity asset (Cash). "
        "Annual withdrawals are drawn from here before other assets are touched. "
        "Must be less than initial capital. Supports shorthand such as 100k or 200k."
    ),
    "max_year": (
        "Number of years each Monte Carlo projection runs. "
        "Summary statistics and charts focus on net asset value at this horizon."
    ),
    "nb_projections": (
        "Number of simulation projections to run. "
        "More projections produce smoother statistics but take longer. "
        "Counts above 5,000 can take several minutes."
    ),
    "allocation": (
        "Target weights of investable assets at the start of each projection "
        "(and after rebalancing). Must sum to 100%. "
        "Cash (liquidity buffer) is held separately and is not part of this mix. "
        "Required classes: Money Market, Bonds, and Stocks; optional classes can be added."
    ),
}

VIVA_FIELD_HELP = {
    "viva_source": (
        "Optional [Viva](https://github.com/ajmscherer/viva) DSL program describing "
        "portfolio contributions and withdrawals. Positive amounts are contributions. "
        "Note: Probabilistic Viva features require a Viva Pro license after "
        "the 30-day evaluation period. Deterministic flows remain MIT-licensed. "
        "(e.g. `flow: insurance, 100k, upon death`); negative amounts are withdrawals."
    ),
}

VIVA_JULIAN_EXAMPLE = (
    "life: Julian, man, born 2000\n"
    "event: wedding, year 2030, probability 50%\n"
    "flow: party, -100k, upon wedding\n"
    "flow: insurance_premium, -2k per year, until Julian's death\n"
    "flow: insurance, 1 million, upon Julian's death\n"
)


def _clear_viva_syntax_result() -> None:
    st.session_state.pop("viva_syntax_result", None)
    st.session_state.pop("viva_syntax_checked_source", None)


def _load_viva_julian_example() -> None:
    st.session_state.portfolio_edit_viva_source = VIVA_JULIAN_EXAMPLE
    _clear_viva_syntax_result()


def _clear_viva_source() -> None:
    st.session_state.portfolio_edit_viva_source = ""
    _clear_viva_syntax_result()


def _test_viva_syntax() -> None:
    source = st.session_state.get("portfolio_edit_viva_source", "")
    st.session_state.viva_syntax_checked_source = source
    try:
        summary, error = try_summarize_viva_source(source)
    except Exception as _:
        summary, error = None, "Syntax error"
    if error or summary is None:
        st.session_state.viva_syntax_result = (
            "error",
            error or "Could not parse Viva program.",
        )
        return
    message = " · ".join(format_viva_program_summary_lines(summary))
    st.session_state.viva_syntax_result = ("success", message)


def _viva_syntax_result_for_display() -> tuple[str, str] | None:
    checked = st.session_state.get("viva_syntax_checked_source")
    current = st.session_state.get("portfolio_edit_viva_source", "")
    if checked != current:
        _clear_viva_syntax_result()
        return None
    result = st.session_state.get("viva_syntax_result")
    if not result:
        return None
    level, message = result
    return level, message


def _render_viva_program_summary(source: str) -> str:
    summary, error = try_summarize_viva_source(source)
    if error or summary is None:
        result = f"Viva syntax error: {error or 'Could not parse Viva program.'}"
    else:
        lines = format_viva_program_summary_lines(summary)
        result = " | ".join(html.escape(line) for line in lines)
    return result


RETURN_ASSUMPTION_HELP = {
    "mu": (
        "Expected annual return for this asset, in percent. "
        "Used as the mean (μ) of the normal return distribution in each simulation year."
    ),
    "sigma": (
        "Expected annual volatility (standard deviation of returns), in percent. "
        "Must be zero or positive. Higher values produce a wider range of outcomes."
    ),
}

PORTFOLIO_SETUP_AMOUNT_FIELDS = (
    ("Initial capital", "portfolio_edit_initial_capital"),
    ("Cash buffer", "portfolio_edit_cash_buffer"),
)
PORTFOLIO_FLOW_AMOUNT_FIELDS = (
    ("Annual contributions", "portfolio_edit_contributions"),
    ("Annual withdrawals", "portfolio_edit_withdrawals"),
)
PORTFOLIO_AMOUNT_FIELDS = (
    *PORTFOLIO_SETUP_AMOUNT_FIELDS,
    *PORTFOLIO_FLOW_AMOUNT_FIELDS,
)


def _validate_amount_fields(
    fields: tuple[tuple[str, str], ...],
    *,
    check_cash_vs_capital: bool = False,
) -> list[str]:
    errors: list[str] = []
    parsed: dict[str, float] = {}

    for label, key in fields:
        if key not in st.session_state:
            continue
        raw = str(st.session_state.get(key, "")).strip()
        if not raw:
            errors.append(f"{label}: enter an amount (e.g. 1M or 40k).")
            continue
        try:
            value = cv(raw)
        except ValueError:
            errors.append(
                f"{label}: could not understand '{raw}' as an amount. "
                "Use a number with optional k, M, or B suffix (e.g. 1M, 40k, 2.5B)."
            )
            continue
        if value < 0:
            errors.append(f"{label}: must be zero or positive.")
            continue
        parsed[label] = value

    if check_cash_vs_capital:
        capital = parsed.get("Initial capital")
        cash_buffer = parsed.get("Cash buffer")
        if capital is not None and cash_buffer is not None and cash_buffer >= capital:
            errors.append("Cash buffer must be less than initial capital.")

    return errors


def _validate_setup_amount_inputs() -> list[str]:
    return _validate_amount_fields(
        PORTFOLIO_SETUP_AMOUNT_FIELDS, check_cash_vs_capital=True
    )


def _validate_flow_amount_inputs() -> list[str]:
    return _validate_amount_fields(PORTFOLIO_FLOW_AMOUNT_FIELDS)


def _validate_portfolio_amount_inputs() -> list[str]:
    return _validate_amount_fields(PORTFOLIO_AMOUNT_FIELDS, check_cash_vs_capital=True)


def _simulation_projection_years() -> list[int]:
    max_year = max(1, int(st.session_state.get("portfolio_edit_max_year", 20)))
    return list(range(1, max_year + 1))


def _format_flow_amount_with_period(
    amount: str,
    from_period: int,
    to_period: int,
    horizon: int,
) -> tuple[str, str | None]:
    from_p = max(1, min(int(from_period), int(horizon)))
    to_p = max(from_p, min(int(to_period), int(horizon)))
    if from_p == 1 and to_p == horizon:
        return (f"{amount} per year", None)
    if from_p == 1:
        return (f"{amount} per year", f"thru Y{to_p}")
    if to_p == horizon:
        return (f"{amount} per year", f"from year {from_p}")
    return (f"{amount} per year", f"from Y{from_p} through Y{to_p}")


# Setup fields that remain in Step 4 (run section).
STEP_1_EDIT_KEYS = (
    "portfolio_edit_description",
    "portfolio_edit_max_year",
    "portfolio_edit_nb_projections",
)
# Capital / cash buffer live in Step 2 (Portfolio) with allocation editing.
PORTFOLIO_CAPITAL_EDIT_KEYS = (
    "portfolio_edit_initial_capital",
    "portfolio_edit_cash_buffer",
)
STEP_2_EDIT_KEYS = (
    "portfolio_edit_contributions",
    "portfolio_edit_withdrawals",
    "portfolio_edit_viva_source",
    "portfolio_edit_contributions_from_period",
    "portfolio_edit_contributions_to_period",
    "portfolio_edit_contributions_periods_initialized",
    "portfolio_edit_withdrawals_from_period",
    "portfolio_edit_withdrawals_to_period",
    "portfolio_edit_withdrawals_periods_initialized",
)


def _init_portfolio_fields() -> None:
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = copy.deepcopy(PORTFOLIO_FIELD_DEFAULTS)
    else:
        # Keep older sessions compatible with newly added portfolio fields.
        for key, value in PORTFOLIO_FIELD_DEFAULTS.items():
            st.session_state.portfolio.setdefault(key, value)


def _clear_edit_keys(keys: tuple[str, ...]) -> None:
    for key in keys:
        st.session_state.pop(key, None)


def _clear_portfolio_edit_widget_keys() -> None:
    """Drop setup / flows / capital edit keys (e.g. after loading assumptions)."""
    _clear_edit_keys(STEP_1_EDIT_KEYS)
    _clear_edit_keys(STEP_2_EDIT_KEYS)
    _clear_edit_keys(PORTFOLIO_CAPITAL_EDIT_KEYS)


def _commit_capital_edit_to_portfolio() -> None:
    """Copy initial capital / cash buffer widget keys into portfolio."""
    portfolio = st.session_state.portfolio
    if "portfolio_edit_initial_capital" in st.session_state:
        portfolio["initial_capital"] = st.session_state.portfolio_edit_initial_capital
    if "portfolio_edit_cash_buffer" in st.session_state:
        portfolio["cash_buffer"] = st.session_state.portfolio_edit_cash_buffer


def _seed_capital_edit_from_portfolio() -> None:
    """Force-load capital edit keys from portfolio (before Step 2 widgets exist)."""
    portfolio = st.session_state.portfolio
    st.session_state.portfolio_edit_initial_capital = portfolio["initial_capital"]
    st.session_state.portfolio_edit_cash_buffer = portfolio["cash_buffer"]


def _commit_step_1_edit_to_portfolio() -> None:
    """Copy Step 4 setup widget keys into portfolio (description / horizon / runs)."""
    portfolio = st.session_state.portfolio
    if "portfolio_edit_description" in st.session_state:
        portfolio["description"] = st.session_state.portfolio_edit_description
    if "portfolio_edit_max_year" in st.session_state:
        portfolio["max_year"] = int(st.session_state.portfolio_edit_max_year)
    if "portfolio_edit_nb_projections" in st.session_state:
        portfolio["nb_projections"] = int(
            st.session_state.portfolio_edit_nb_projections
        )


def _commit_step_2_edit_to_portfolio() -> None:
    """Copy step 2 widget keys into portfolio (safe in on_exit callbacks)."""
    portfolio = st.session_state.portfolio
    if "portfolio_edit_contributions" in st.session_state:
        portfolio["contributions"] = st.session_state.portfolio_edit_contributions
    if "portfolio_edit_withdrawals" in st.session_state:
        portfolio["withdrawals"] = st.session_state.portfolio_edit_withdrawals
    if "portfolio_edit_viva_source" in st.session_state:
        portfolio["viva_source"] = st.session_state.portfolio_edit_viva_source
    for slug in ("contributions", "withdrawals"):
        prefix = f"portfolio_edit_{slug}"
        from_key = f"{prefix}_from_period"
        to_key = f"{prefix}_to_period"
        if from_key in st.session_state and to_key in st.session_state:
            portfolio[f"{slug}_from_period"] = int(st.session_state[from_key])
            portfolio[f"{slug}_to_period"] = int(st.session_state[to_key])


def _seed_step_1_edit_from_portfolio() -> None:
    """Force-load Step 4 setup edit keys from portfolio (before widgets exist)."""
    portfolio = st.session_state.portfolio
    st.session_state.portfolio_edit_description = portfolio.get("description", "")
    st.session_state.portfolio_edit_max_year = int(portfolio["max_year"])
    st.session_state.portfolio_edit_nb_projections = int(portfolio["nb_projections"])


def _seed_step_2_edit_from_portfolio() -> None:
    """Force-load step 2 edit keys from portfolio (call only before widgets exist)."""
    portfolio = st.session_state.portfolio
    horizon = max(1, int(portfolio["max_year"]))
    st.session_state.portfolio_edit_contributions = portfolio["contributions"]
    st.session_state.portfolio_edit_withdrawals = portfolio["withdrawals"]
    st.session_state.portfolio_edit_viva_source = portfolio.get("viva_source", "")
    for slug in ("contributions", "withdrawals"):
        portfolio.setdefault(f"{slug}_from_period", 1)
        portfolio.setdefault(f"{slug}_to_period", horizon)
        prefix = f"portfolio_edit_{slug}"
        st.session_state[f"{prefix}_from_period"] = int(
            portfolio[f"{slug}_from_period"]
        )
        st.session_state[f"{prefix}_to_period"] = int(portfolio[f"{slug}_to_period"])
        st.session_state[f"{prefix}_periods_initialized"] = True


# Display Step 1 = flows (internal seed/commit helpers are still named *_step_2_*).
# Setup fields (description / horizon / projections) live always-on in Step 4 and
# use _seed_step_1_edit_from_portfolio / _ensure_setup_widgets_seeded instead.
def _on_enter_step_1_edit() -> None:
    _seed_step_2_edit_from_portfolio()


def _on_exit_step_1_edit() -> None:
    _commit_step_2_edit_to_portfolio()
    _clear_edit_keys(STEP_2_EDIT_KEYS)


def _ensure_flow_period_defaults(base_key: str, horizon: int) -> tuple[str, str]:
    """Return period widget keys; values must already be seeded on enter-edit."""
    from_key = f"{base_key}_from_period"
    to_key = f"{base_key}_to_period"
    horizon = max(1, int(horizon))
    # Defensive seed if enter-hook was skipped (should not happen in normal flow).
    if from_key not in st.session_state:
        st.session_state[from_key] = 1
    if to_key not in st.session_state:
        st.session_state[to_key] = horizon
    return from_key, to_key


def _sync_edit_widgets_to_portfolio() -> None:
    """Commit whichever portfolio-related edit keys are currently present."""
    _commit_step_1_edit_to_portfolio()
    _commit_capital_edit_to_portfolio()
    _commit_step_2_edit_to_portfolio()


def _section_is_editing(section_name: str) -> bool:
    slug = section_name.lower().replace(" ", "_")
    return bool(st.session_state.get(f"section_{slug}_editing", False))


def _read_portfolio_fields() -> dict[str, Any]:
    # Step 4 always mounts setup widgets (description / horizon / projections).
    setup_keys_present = "portfolio_edit_max_year" in st.session_state
    # Capital / cash live in Step 2 while that section is being edited.
    capital_keys_present = "portfolio_edit_initial_capital" in st.session_state
    editing_flows = _section_is_editing("Step 1")
    editing_portfolio = _section_is_editing("Step 2")
    if (
        setup_keys_present
        or capital_keys_present
        or editing_flows
        or editing_portfolio
        or st.session_state.get("portfolio_assumptions_editing")
    ):
        errors: list[str] = []
        if capital_keys_present or st.session_state.get(
            "portfolio_assumptions_editing"
        ):
            errors.extend(_validate_setup_amount_inputs())
        if editing_flows or st.session_state.get("portfolio_assumptions_editing"):
            errors.extend(_validate_flow_amount_inputs())
        if not errors:
            _sync_edit_widgets_to_portfolio()
    return st.session_state.portfolio


def _set_simulation_running(running: bool) -> None:
    st.session_state.simulation_running = running


def _simulation_running() -> bool:
    return bool(st.session_state.get("simulation_running", False))


def _force_close_all_section_edits() -> None:
    """Commit and close Steps 1–3 edit modes before a simulation run.

    Keeps the widget tree in a stable readonly layout while the long-running
    simulation executes (avoids empty/flickering section frames).
    """
    if _section_is_editing("Step 1"):
        _on_exit_step_1_edit()
        st.session_state["section_step_1_editing"] = False
    if _section_is_editing("Step 2"):
        _on_exit_step_2_edit()
        st.session_state["section_step_2_editing"] = False
    if _section_is_editing("Step 3"):
        _on_exit_step_3_edit()
        st.session_state["section_step_3_editing"] = False


def _request_simulation_run() -> None:
    """Queue a run and open the simulation overlay (live charts + results)."""
    _force_close_all_section_edits()
    st.session_state.run_simulation_requested = True
    st.session_state.sim_overlay_open = True
    _set_simulation_running(True)
    st.rerun()


def _close_sim_overlay() -> None:
    st.session_state.sim_overlay_open = False
    st.session_state.pop("sim_confirm_cancel", None)
    st.session_state.pop("sim_confirm_save", None)


def _sim_overlay_should_open() -> bool:
    return bool(
        st.session_state.get("sim_overlay_open")
        or st.session_state.get("run_simulation_requested")
        or _simulation_running()
        or _get_active_sim_job() is not None
    )


# Session-state key for the active SimulationJob. Must NOT be a module global:
# Streamlit re-executes app.py every run and would reset ``_active_sim_job = None``,
# dropping the job after the first batch (empty dialog / no progress).
_SIM_JOB_KEY = "_active_sim_job"


def _sim_batch_size(nb_projections: int) -> int:
    """Projections per script run so the dialog × control stays responsive."""
    return max(10, min(40, int(nb_projections) // 50 or 10))


def _get_active_sim_job() -> Any | None:
    return st.session_state.get(_SIM_JOB_KEY)


def _set_active_sim_job(job: Any | None) -> None:
    if job is None:
        st.session_state.pop(_SIM_JOB_KEY, None)
    else:
        st.session_state[_SIM_JOB_KEY] = job


def _discard_active_sim_job() -> None:
    job = _get_active_sim_job()
    if job is not None:
        try:
            job.close()
        except Exception:
            pass
        _set_active_sim_job(None)


def _start_active_sim_job() -> Any:
    """Create a SimulationJob from current GUI assumptions."""
    _discard_active_sim_job()
    # Do not reload inv_proj modules mid-session: it breaks class identity for
    # any object still held in session_state and is unnecessary each Run click.
    assumptions = _collect_assumptions()
    config = assumptions.to_simulation_config()
    validate_allocation(config.risk_mix, config.asset_catalog)
    validate_correlation(config.risk_param, config.risk_correlation)
    job = inv_proj_runner.SimulationJob(config)
    _set_active_sim_job(job)
    return job


def _save_assumptions_to_file() -> tuple[bool, str]:
    """Save current assumptions JSON. Returns (ok, message)."""
    try:
        assumptions = _collect_assumptions()
        if st.session_state.assumptions_file:
            path = Path(st.session_state.assumptions_file)
        else:
            path = DEFAULT_ASSUMPTIONS_DIR / assumptions.safe_filename()
            st.session_state.assumptions_file = str(path)
        assumptions.save(path)
        return True, f"Saved to `{path}`."
    except (ValueError, OSError) as exc:
        return False, str(exc)


def _init_session_state() -> None:
    st.session_state.setdefault("asset_catalog", default_asset_catalog())
    st.session_state.setdefault(
        "allocation", copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
    )
    st.session_state.setdefault("mix_preset", "performance")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("simulation_running", False)
    st.session_state.setdefault("run_simulation_requested", False)
    st.session_state.setdefault("sim_overlay_open", False)
    st.session_state.setdefault("sim_confirm_cancel", False)
    st.session_state.setdefault("sim_confirm_save", False)
    _init_portfolio_fields()
    st.session_state.setdefault("output_dir", str(DEFAULT_OUTPUT_DIR))
    st.session_state.setdefault("assumptions_name", "Untitled")
    st.session_state.setdefault("assumptions_file", "")
    st.session_state.setdefault("portfolio_assumptions_editing", False)
    if "asset_allocation_editing" not in st.session_state:
        st.session_state.asset_allocation_editing = st.session_state.pop(
            "asset_classes_editing", False
        )
    st.session_state.setdefault("asset_allocation_editing", False)
    st.session_state.setdefault("return_assumptions_editing", False)
    if "correlation_values" not in st.session_state:
        st.session_state.correlation_values = _default_correlation_values(
            st.session_state.asset_catalog
        )
    _init_mu_sigma_keys(st.session_state.asset_catalog)
    _init_correlation_keys(st.session_state.asset_catalog)


def _read_mu_sigma(catalog: AssetCatalog) -> dict[str, tuple[float, float]]:
    if _section_is_editing("Step 3"):
        _commit_step_4_edit_to_session(catalog)
    mu_sigma: dict[str, tuple[float, float]] = {}
    for asset_id in return_model_asset_ids(catalog):
        mu_sigma[asset_id] = (
            float(st.session_state[f"mu_{asset_id}"]),
            float(st.session_state[f"sigma_{asset_id}"]),
        )
    return mu_sigma


def _read_correlation_values(catalog: AssetCatalog) -> dict[tuple[str, str], float]:
    if _section_is_editing("Step 3"):
        _commit_step_4_edit_to_session(catalog)
    asset_order = return_model_asset_ids(catalog)
    values: dict[tuple[str, str], float] = {}
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        key = f"corr_{canonical[0]}_{canonical[1]}"
        values[canonical] = float(st.session_state.get(key, 0.0))
    st.session_state.correlation_values = values
    return values


def _collect_assumptions() -> Assumptions:
    catalog: AssetCatalog = _read_asset_catalog()
    portfolio = _read_portfolio_fields()
    assumptions = Assumptions.from_gui_state(
        name=st.session_state.assumptions_name.strip() or "Untitled",
        description=str(portfolio.get("description", "") or ""),
        initial_capital=portfolio["initial_capital"],
        contributions=portfolio["contributions"],
        withdrawals=portfolio["withdrawals"],
        cash_buffer=portfolio["cash_buffer"],
        max_year=int(portfolio["max_year"]),
        nb_projections=int(portfolio["nb_projections"]),
        output_dir=st.session_state.output_dir,
        mix_preset=st.session_state.mix_preset,
        asset_catalog=catalog,
        allocation=dict(st.session_state.allocation),
        mu_sigma=_read_mu_sigma(catalog),
        correlation_values=_read_correlation_values(catalog),
        viva_source=portfolio.get("viva_source", ""),
        contributions_from_period=int(portfolio.get("contributions_from_period", 1)),
        contributions_to_period=int(
            portfolio.get("contributions_to_period", portfolio["max_year"])
        ),
        withdrawals_from_period=int(portfolio.get("withdrawals_from_period", 1)),
        withdrawals_to_period=int(
            portfolio.get("withdrawals_to_period", portfolio["max_year"])
        ),
    )
    return assumptions


def _queue_assumptions_load(
    assumptions: Assumptions, file_path: Path | None = None
) -> None:
    st.session_state["_pending_assumptions"] = assumptions.to_dict()
    st.session_state["_pending_assumptions_file"] = str(file_path) if file_path else ""


def _process_pending_assumptions() -> None:
    if "_pending_assumptions" not in st.session_state:
        return
    assumptions = Assumptions.from_dict(st.session_state["_pending_assumptions"])
    file_path = st.session_state.get("_pending_assumptions_file") or ""
    del st.session_state["_pending_assumptions"]
    del st.session_state["_pending_assumptions_file"]
    _apply_assumptions(assumptions, Path(file_path) if file_path else None)
    st.session_state["_assumptions_load_message"] = f'Loaded "{assumptions.name}".'


def _apply_assumptions(assumptions: Assumptions, file_path: Path | None = None) -> None:
    st.session_state.portfolio = {
        "description": assumptions.description,
        "initial_capital": assumptions.initial_capital,
        "contributions": assumptions.contributions,
        "withdrawals": assumptions.withdrawals,
        "cash_buffer": assumptions.cash_buffer,
        "max_year": assumptions.max_year,
        "nb_projections": assumptions.nb_projections,
        "viva_source": assumptions.viva_source,
        "contributions_from_period": assumptions.contributions_from_period,
        "contributions_to_period": assumptions.contributions_to_period,
        "withdrawals_from_period": assumptions.withdrawals_from_period,
        "withdrawals_to_period": assumptions.withdrawals_to_period,
    }
    st.session_state.output_dir = assumptions.output_dir
    st.session_state.mix_preset = assumptions.mix_preset
    st.session_state.assumptions_name = assumptions.name
    st.session_state.asset_catalog = assumptions.asset_catalog.copy()
    st.session_state.allocation = copy.deepcopy(assumptions.allocation)
    st.session_state.correlation_values = assumptions.correlation_values()
    st.session_state.assumptions_file = str(file_path) if file_path else ""
    st.session_state.result = None
    st.session_state.portfolio_assumptions_editing = False
    st.session_state.asset_allocation_editing = False
    st.session_state.return_assumptions_editing = False
    st.session_state.pop("section_step_1_editing", None)
    st.session_state.pop("section_step_2_editing", None)
    st.session_state.pop("section_step_3_editing", None)
    _clear_portfolio_edit_widget_keys()
    _clear_step_3_edit_keys(assumptions.asset_catalog)
    _clear_step_4_edit_keys(assumptions.asset_catalog)

    for asset in assumptions.asset_catalog.assets:
        st.session_state[f"asset_name_{asset.id}"] = asset.name

    for asset_id, weight in assumptions.allocation.items():
        st.session_state[f"alloc_{asset_id}"] = float(weight)

    for asset_id, (mu, sigma) in assumptions.mu_sigma_tuples().items():
        st.session_state[f"mu_{asset_id}"] = float(mu)
        st.session_state[f"sigma_{asset_id}"] = float(sigma)

    asset_order = assumptions.asset_catalog.return_model_ids()
    for key, rho in assumptions.correlations.items():
        left, right = key.split("|", 1)
        canonical = normalize_correlation_pair(left, right, asset_order)
        st.session_state[f"corr_{canonical[0]}_{canonical[1]}"] = float(rho)


def _render_assumptions_file_controls() -> None:
    st.header("Assumptions file")
    st.text_input("Scenario name", key="assumptions_name")

    current_file = st.session_state.assumptions_file
    if current_file:
        st.caption(f"Current file: `{current_file}`")
    else:
        st.caption("No file saved yet — use **Save** for the first save.")

    uploaded = st.file_uploader(
        "Load from JSON file", type=["json"], key="assumptions_uploader"
    )
    if st.button("Load", use_container_width=True):
        if uploaded is None:
            st.warning("Choose a JSON file first.")
        else:
            try:
                assumptions = Assumptions.from_json(uploaded.getvalue().decode("utf-8"))
                _queue_assumptions_load(assumptions)
                st.rerun()
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                st.error(f"Could not load file: {exc}")

    if st.button("Save", use_container_width=True):
        ok, message = _save_assumptions_to_file()
        if ok:
            st.success(message)
        else:
            st.error(message)

    try:
        download_payload = _collect_assumptions().to_json()
    except ValueError as exc:
        download_payload = None
        st.warning(f"Cannot export assumptions: {exc}")

    if download_payload:
        st.download_button(
            "Download JSON",
            data=download_payload,
            file_name=_collect_assumptions().safe_filename(),
            mime="application/json",
            use_container_width=True,
        )


def _step_3_edit_keys(catalog: AssetCatalog | None = None) -> list[str]:
    cat: AssetCatalog = (
        catalog if catalog is not None else st.session_state.asset_catalog
    )
    keys: list[str] = []
    for asset in _investable_assets(cat):
        keys.append(f"asset_name_{asset.id}")
        keys.append(f"alloc_{asset.id}")
    return keys


def _step_4_edit_keys(catalog: AssetCatalog | None = None) -> list[str]:
    cat: AssetCatalog = (
        catalog if catalog is not None else st.session_state.asset_catalog
    )
    keys: list[str] = []
    for asset_id in return_model_asset_ids(cat):
        keys.append(f"return_edit_mu_{asset_id}")
        keys.append(f"return_edit_sigma_{asset_id}")
    asset_order = return_model_asset_ids(cat)
    for left, right in _correlation_pairs(cat):
        canonical = normalize_correlation_pair(left, right, asset_order)
        keys.append(f"return_edit_corr_{canonical[0]}_{canonical[1]}")
    return keys


def _seed_step_3_edit_from_session() -> None:
    """Force-load Step 2 (Portfolio) edit keys before widgets exist."""
    catalog: AssetCatalog = st.session_state.asset_catalog
    allocation = st.session_state.allocation
    _seed_capital_edit_from_portfolio()
    for asset in _investable_assets(catalog):
        st.session_state[f"asset_name_{asset.id}"] = asset.name
        st.session_state[f"alloc_{asset.id}"] = float(allocation.get(asset.id, 0.0))


def _commit_step_3_edit_to_session() -> None:
    """Copy Step 2 (Portfolio) widget keys into portfolio + catalog + allocation.

    Skip while a normalize/reset widget sync is pending so stale ``alloc_*``
    values cannot clobber the freshly scaled ``session_state.allocation``.
    """
    if st.session_state.get("_pending_allocation_widget_sync"):
        return
    _commit_capital_edit_to_portfolio()
    catalog: AssetCatalog = st.session_state.asset_catalog.copy()
    allocation: dict[str, float] = {}
    for asset in list(_investable_assets(catalog)):
        name_key = f"asset_name_{asset.id}"
        alloc_key = f"alloc_{asset.id}"
        if name_key in st.session_state:
            new_name = str(st.session_state[name_key]).strip()
            if new_name and new_name != asset.name:
                try:
                    catalog.rename(asset.id, new_name)
                except ValueError:
                    pass
        if alloc_key in st.session_state:
            allocation[asset.id] = float(st.session_state[alloc_key])
        else:
            allocation[asset.id] = float(st.session_state.allocation.get(asset.id, 0.0))
    st.session_state.asset_catalog = catalog
    if allocation:
        st.session_state.allocation = allocation


def _clear_step_3_edit_keys(catalog: AssetCatalog | None = None) -> None:
    for key in _step_3_edit_keys(catalog):
        st.session_state.pop(key, None)
    _clear_edit_keys(PORTFOLIO_CAPITAL_EDIT_KEYS)
    # Also drop orphan alloc_/asset_name_ keys no longer in the catalog.
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(("asset_name_", "alloc_")):
            st.session_state.pop(key, None)


def _on_enter_step_2_edit() -> None:
    _seed_step_3_edit_from_session()


def _on_exit_step_2_edit() -> None:
    # Done must always commit even if a normalize/reset sync flag was left set.
    st.session_state.pop("_pending_allocation_widget_sync", None)
    _commit_step_3_edit_to_session()
    _clear_step_3_edit_keys()


def _read_asset_catalog() -> AssetCatalog:
    if _section_is_editing("Step 2"):
        _commit_step_3_edit_to_session()
    return st.session_state.asset_catalog


def _request_allocation_widget_sync() -> None:
    """After mid-edit normalize/reset, re-seed alloc widgets on next render."""
    st.session_state["_pending_allocation_widget_sync"] = True


def _apply_pending_allocation_widget_sync() -> None:
    """Re-seed ``alloc_*`` keys from canonical allocation before any commit.

    Must run early in the script (before the sidebar's ``_collect_assumptions``),
    otherwise stale widget values get committed over a just-normalized allocation
    and Normalize/Reset appear to do nothing.
    """
    if not st.session_state.pop("_pending_allocation_widget_sync", False):
        return
    _seed_step_3_edit_from_session()


def _seed_step_4_edit_from_session(catalog: AssetCatalog | None = None) -> None:
    """Force-load step 3 edit keys from mu/sigma/correlation canonical state."""
    cat: AssetCatalog = (
        catalog if catalog is not None else st.session_state.asset_catalog
    )
    for asset_id in return_model_asset_ids(cat):
        st.session_state[f"return_edit_mu_{asset_id}"] = float(
            st.session_state.get(
                f"mu_{asset_id}",
                float(
                    DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0]["mu"]
                ),
            )
        )
        st.session_state[f"return_edit_sigma_{asset_id}"] = float(
            st.session_state.get(
                f"sigma_{asset_id}",
                float(
                    DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0][
                        "sigma"
                    ]
                ),
            )
        )
    asset_order = return_model_asset_ids(cat)
    correlation_values = st.session_state.get("correlation_values") or {}
    for left, right in _correlation_pairs(cat):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
        st.session_state[edit_key] = float(correlation_values.get(canonical, 0.0))


def _commit_step_4_edit_to_session(catalog: AssetCatalog | None = None) -> None:
    """Copy step 3 widget keys into mu/sigma/correlation canonical state."""
    cat: AssetCatalog = (
        catalog if catalog is not None else st.session_state.asset_catalog
    )
    for asset_id in return_model_asset_ids(cat):
        mu_key = f"return_edit_mu_{asset_id}"
        sigma_key = f"return_edit_sigma_{asset_id}"
        if mu_key in st.session_state:
            st.session_state[f"mu_{asset_id}"] = float(st.session_state[mu_key])
        if sigma_key in st.session_state:
            st.session_state[f"sigma_{asset_id}"] = float(st.session_state[sigma_key])

    asset_order = return_model_asset_ids(cat)
    values: dict[tuple[str, str], float] = {}
    for left, right in _correlation_pairs(cat):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
        if edit_key in st.session_state:
            rho = float(st.session_state[edit_key])
        else:
            rho = float(st.session_state.correlation_values.get(canonical, 0.0))
        values[canonical] = rho
        st.session_state[f"corr_{canonical[0]}_{canonical[1]}"] = rho
    st.session_state.correlation_values = values


def _clear_step_4_edit_keys(catalog: AssetCatalog | None = None) -> None:
    for key in _step_4_edit_keys(catalog):
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("return_edit_"):
            st.session_state.pop(key, None)


def _on_enter_step_3_edit() -> None:
    _seed_step_4_edit_from_session()


def _on_exit_step_3_edit() -> None:
    _commit_step_4_edit_to_session()
    _clear_step_4_edit_keys()


def _reset_correlation_assumptions_to_defaults() -> None:
    catalog = st.session_state.asset_catalog
    st.session_state.correlation_values = _default_correlation_values(catalog)
    # Re-seed only correlation edit keys (callback runs before widgets this run).
    asset_order = return_model_asset_ids(catalog)
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
        st.session_state[edit_key] = float(
            st.session_state.correlation_values.get(canonical, 0.0)
        )


def _set_no_correlations() -> None:
    catalog = st.session_state.asset_catalog
    st.session_state.correlation_values = {
        (left, right): 0.0 for left, right in _correlation_pairs(catalog)
    }
    asset_order = return_model_asset_ids(catalog)
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
        st.session_state[edit_key] = 0.0
        st.session_state[f"corr_{canonical[0]}_{canonical[1]}"] = 0.0


def _format_correlation_summary(
    catalog: AssetCatalog,
    correlation_values: dict[tuple[str, str], float],
) -> str:
    asset_order = return_model_asset_ids(catalog)
    pairs = []
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        rho = correlation_values.get(canonical, 0.0)
        if abs(rho) > 1e-12:
            pairs.append(f"{catalog.name(left)}/{catalog.name(right)} {rho:.2f}")
    if not pairs:
        return "Correlations: none set"
    return "Correlations: " + ", ".join(pairs)


def _install_section_click_handlers() -> None:
    """Forward section panel clicks to enter or exit edit mode."""
    # Re-bind on every rerun: Streamlit reruns replace DOM nodes and a one-shot
    # iframe listener would otherwise stop firing after the first mode switch.
    st.html(
        """
        <div style="display:none" aria-hidden="true">
        <script>
        (function () {
            const doc = document;
            const bindings = [
                ['portfolio_section', 'portfolio_assumptions_edit', 'portfolio_assumptions_done'],
                ['portfolio_allocation_section', 'asset_allocation_edit', 'asset_allocation_done'],
                ['assets_performance_and_vol', 'return_assumptions_edit', 'return_assumptions_done'],
            ];

            function isDataEntryTarget(target) {
                if (target.closest('input, textarea, select, [contenteditable="true"]')) {
                    return true;
                }
                if (target.closest('[data-baseweb="select"], [data-baseweb="input"], [data-baseweb="textarea"]')) {
                    return true;
                }
                if (target.closest('[data-baseweb="popover"], [role="listbox"], [role="option"]')) {
                    return true;
                }
                if (target.closest('[data-testid="stNumberInput"] button')) {
                    return true;
                }
                return false;
            }

            function actionButton(section, actionKey) {
                const wrap = section.querySelector('.st-key-' + actionKey);
                if (!wrap) return null;
                return wrap.querySelector('button');
            }

            function handler(event) {
                if (event.target.closest('button')) return;
                if (event.target.closest('[data-testid="stTooltipIcon"]')) return;
                if (isDataEntryTarget(event.target)) return;

                for (const [sectionKey, editKey, doneKey] of bindings) {
                    const section = event.target.closest('.st-key-' + sectionKey);
                    if (!section) continue;

                    const doneBtn = actionButton(section, doneKey);
                    if (doneBtn && !doneBtn.contains(event.target)) {
                        doneBtn.click();
                        return;
                    }

                    const editBtn = actionButton(section, editKey);
                    if (editBtn && !editBtn.contains(event.target)) {
                        editBtn.click();
                        return;
                    }
                }
            }

            if (window.__fpSectionClickHandler) {
                doc.removeEventListener('click', window.__fpSectionClickHandler);
            }
            window.__fpSectionClickHandler = handler;
            doc.addEventListener('click', handler);
        })();
        </script>
        </div>
        """,
        unsafe_allow_javascript=True,
        width=1,
    )


def _render_outcome_probability_metrics(result: RunResult, max_year: int) -> None:
    horizon_key = _nav_key(max_year)
    if horizon_key not in result.nav_observers:
        return

    horizon_observer = result.nav_observers[horizon_key]
    initial_capital = cv(st.session_state.portfolio["initial_capital"])
    values = horizon_observer.values
    negative_rate = (
        100.0 * sum(1 for value in values if value < 0) / len(values)
        if values
        else float("nan")
    )
    above_initial_rate = success_rate(horizon_observer, threshold=initial_capital)

    with st.container(border=True):
        metric_cols = st.columns(2)
        with metric_cols[0]:
            st.metric(
                f"Probability final NAV\n\nat year {max_year} is negative",
                f"{negative_rate:.1f}%",
                help=(
                    f"Share of simulation projections where net asset value at year {max_year} "
                    f"is below zero. I.e. probability of portfolio failure."
                ),
            )
        with metric_cols[1]:
            st.metric(
                f"Probability final NAV\n\n at year {max_year} is greater than initial capital ({format_compact_amount(initial_capital)})",
                f"{above_initial_rate:.1f}%",
                help=(
                    f"Share of simulation projections where net asset value at year {max_year} "
                    f"exceeds initial capital ({format_compact_amount(initial_capital)})."
                ),
            )


def _render_summary(result: RunResult) -> None:
    st.subheader("Summary statistics")
    rows = []
    for label, observer in result.nav_observers.items():
        rows.append(
            {
                "Metric": label,
                "Mean": format_compact_amount(observer.mean()),
                "Std Dev": format_compact_amount(observer.std()),
                "P10": format_compact_amount(observer.quantile(0.10)),
                "P50": format_compact_amount(observer.quantile(0.50)),
                "P90": format_compact_amount(observer.quantile(0.90)),
                "Min": format_compact_amount(observer.min()),
                "Max": format_compact_amount(observer.max()),
            }
        )
    st.markdown(render_summary_statistics_table(rows), unsafe_allow_html=True)


def _render_nav_distribution_chart(
    values: list[float],
    chart_year: int,
    *,
    projections_done: int | None = None,
    projections_total: int | None = None,
) -> None:
    if not values:
        return
    suffix = ""
    if projections_done is not None and projections_total is not None:
        suffix = f"{projections_done:,} / {projections_total:,} projections"
    hist_fig = build_nav_distribution_figure(values, chart_year, title_suffix=suffix)
    st.pyplot(hist_fig)
    plt.close(hist_fig)


def _render_nav_fan_chart(
    nav_fan,
    *,
    projections_done: int | None = None,
    projections_total: int | None = None,
    show_latest_projection: bool = False,
) -> None:
    latest_projection_curve = (
        extract_latest_projection_curve(nav_fan) if show_latest_projection else None
    )
    fan_fig = build_nav_fan_figure(
        nav_fan,
        projections_done=projections_done,
        projections_total=projections_total,
        latest_projection_curve=latest_projection_curve,
    )
    if fan_fig is not None:
        st.pyplot(fan_fig)
        plt.close(fan_fig)


def _render_charts(
    result: RunResult,
    *,
    projections_done: int | None = None,
    projections_total: int | None = None,
) -> None:
    distribution_year = result.nav_fan.max_year
    values = result.nav_fan.values_by_year.get(distribution_year, [])
    col_hist, col_fan = st.columns(2)
    with col_hist:
        _render_nav_distribution_chart(
            values,
            distribution_year,
            projections_done=projections_done,
            projections_total=projections_total,
        )
    with col_fan:
        _render_nav_fan_chart(
            result.nav_fan,
            projections_done=projections_done,
            projections_total=projections_total,
        )


def _render_live_charts(
    nav_fan,
    distribution_year: int,
    *,
    projections_done: int,
    projections_total: int,
) -> None:
    col_hist, col_fan = st.columns(2)
    with col_hist:
        _render_nav_distribution_chart(
            nav_fan.values_by_year.get(distribution_year, []),
            distribution_year,
            projections_done=projections_done,
            projections_total=projections_total,
        )
    with col_fan:
        _render_nav_fan_chart(
            nav_fan,
            projections_done=projections_done,
            projections_total=projections_total,
            show_latest_projection=True,
        )


def _ensure_setup_widgets_seeded() -> None:
    """Seed Step 4 setup edit keys from portfolio if they are not already mounted."""
    if "portfolio_edit_max_year" not in st.session_state:
        _seed_step_1_edit_from_portfolio()


def _render_setup_fields() -> None:
    """Editable simulation setup fields (idle only)."""
    _ensure_setup_widgets_seeded()
    st.text_area(
        "Description",
        key="portfolio_edit_description",
        height=100,
        help=PORTFOLIO_FIELD_HELP["description"],
        placeholder="Describe what this simulation is about…",
    )
    cols = st.columns(2)
    with cols[0]:
        st.number_input(
            "Horizon (years)",
            min_value=1,
            max_value=50,
            step=1,
            key="portfolio_edit_max_year",
            help=PORTFOLIO_FIELD_HELP["max_year"],
        )
    with cols[1]:
        st.number_input(
            "Number of projections",
            min_value=10,
            max_value=20000,
            step=10,
            key="portfolio_edit_nb_projections",
            help=PORTFOLIO_FIELD_HELP["nb_projections"],
        )
    if int(st.session_state.portfolio_edit_nb_projections) > 5000:
        st.warning("Large projection counts can take several minutes.")
    _commit_step_1_edit_to_portfolio()


def _render_flow_period_block(name: str, help: str, key: str | None = None) -> None:
    slug = name.lower().replace(" ", "_")
    if not key:
        key = f"portfolio_edit_{slug}"
    years = _simulation_projection_years()
    horizon = years[-1]
    from_key, to_key = _ensure_flow_period_defaults(key, horizon)

    # Clamp period keys to the current horizon *before* creating widgets.
    from_period = int(st.session_state[from_key])
    to_period = int(st.session_state[to_key])
    if from_period not in years:
        from_period = years[0]
        st.session_state[from_key] = from_period
    to_years = list(range(from_period, years[-1] + 1))
    if to_period not in to_years:
        to_period = to_years[-1]
        st.session_state[to_key] = to_period

    container = st.container(
        border=True,
        horizontal=True,
        key=f"{key}_block",
    )
    with container:
        st.text_input(
            name,
            key=key,
            help=help,
        )
        st.selectbox(
            label="From period",
            options=years,
            key=from_key,
            label_visibility="visible",
        )
        st.selectbox(
            label="To period",
            options=to_years,
            key=to_key,
            label_visibility="visible",
        )


def _render_step_1_readonly() -> None:
    _clear_viva_syntax_result()
    portfolio = st.session_state.portfolio
    horizon = int(portfolio["max_year"])
    with st.container(
        border=False, 
        key="portfolio_section_1", 
        horizontal=True, width="stretch"):
        # summary_cols = st.columns(2)
        with st.container(border=False, gap=None, width=175):
            line1, line2 = _format_flow_amount_with_period(
                portfolio["contributions"],
                portfolio.get("contributions_from_period", 1),
                portfolio.get("contributions_to_period", horizon),
                horizon,
            )
            st.metric(
                "Contributions",
                line1,
                help=PORTFOLIO_FIELD_HELP["contributions"],
            )
            if line2:
                st.caption(line2)
        with st.container(border=False, gap=None, width=175):
            line1, line2 = _format_flow_amount_with_period(
                portfolio["withdrawals"],
                portfolio.get("withdrawals_from_period", 1),
                portfolio.get("withdrawals_to_period", horizon),
                horizon,
            )
            st.metric(
                "Withdrawals",
                line1,
                help=PORTFOLIO_FIELD_HELP["withdrawals"],
            )
            if line2:
                st.caption(line2)
        viva_source = portfolio.get("viva_source", "").strip()
        with st.container(border=False, gap=None):
            if viva_source:
                result = _render_viva_program_summary(viva_source)
                
            else:
                result = "No additional Viva flows configured."
            st.metric("Additional flows", result, help=VIVA_FIELD_HELP["viva_source"])

def _render_step_1_edit() -> None:
    # Edit keys are force-seeded in on_enter_edit before this form runs.
    with st.container(border=False, key="portfolio_section_1"):
        _render_flow_period_block(
            "Contributions", PORTFOLIO_FIELD_HELP["contributions"]
        )
        _render_flow_period_block("Withdrawals", PORTFOLIO_FIELD_HELP["withdrawals"])

        if not HAS_VIVA:
            st.warning(
                "Viva is not installed in this environment. "
                "Re-run `./run_gui.sh` or `pip install -r requirements-gui.txt`."
            )
        with st.container(border=True, horizontal=True):
            st.text_area(
                "Additional flows",
                key="portfolio_edit_viva_source",
                height=180,
                help=VIVA_FIELD_HELP["viva_source"],
                placeholder=(
                    "Enter your additional flows here. "
                    "Click the 'load example' button to load a sample program."
                ),
            )
            with st.container(
                border=False,
                horizontal=False,
                width=150,
                height="stretch",
                vertical_alignment="bottom",
            ):
                st.button(
                    "clear",
                    width="stretch",
                    key="viva_clear",
                    on_click=_clear_viva_source,
                )
                st.button(
                    "load example",
                    width="stretch",
                    key="viva_load_example",
                    on_click=_load_viva_julian_example,
                )
                st.button(
                    "test syntax",
                    width="stretch",
                    key="viva_test_syntax",
                    on_click=_test_viva_syntax,
                )
        syntax_result = _viva_syntax_result_for_display()
        if syntax_result:
            level, message = syntax_result
            if level == "error":
                st.error(message)
            else:
                st.success(message)

        for message in _validate_flow_amount_inputs():
            st.error(message)
        # Keep portfolio in sync on every rerun while editing (blur/change).
        _commit_step_2_edit_to_portfolio()


def _render_step_2_readonly() -> None:
    catalog = _read_asset_catalog()
    portfolio = st.session_state.portfolio
    with st.container(border=False, key="portfolio_allocation_section_inner"):
        with st.container(border=False, horizontal=True, width="content"):
            st.metric(
            "Initial capital",
            portfolio["initial_capital"],
            help=PORTFOLIO_FIELD_HELP["initial_capital"],
            )
            st.metric(
            "Cash buffer",
            portfolio["cash_buffer"],
            help=PORTFOLIO_FIELD_HELP["cash_buffer"],
            )
            assets = _investable_assets(catalog)
            allocation = st.session_state.allocation
            allocation_str = " ‣ ".join([f"{asset.name}={allocation.get(asset.id, 0.0):.0f}%" for asset in assets])
            st.metric(
                label="Allocation",
                value=allocation_str,
                help=PORTFOLIO_FIELD_HELP["allocation"],
            )
        
        alloc_total = sum(allocation.values())
        error = abs(alloc_total - 100.0) > 0.01
        if error:
            st.error(
                "Allocation must sum to 100%. Please edit and adjust the allocations to sum to 100%."
            )


def _render_step_2_edit() -> None:
    # Pending normalize/reset sync is applied early in main(); keep a late
    # fallback in case this form is rendered without going through main().
    _apply_pending_allocation_widget_sync()

    catalog: AssetCatalog = st.session_state.asset_catalog.copy()
    show_border = False  # TODO: make this dynamic based on the section mode

    with st.container(border=False, key="portfolio_allocation_section", gap="small"):
        capital_cols = st.columns(2)
        with capital_cols[0]:
            st.text_input(
                "Initial capital",
                key="portfolio_edit_initial_capital",
                help=PORTFOLIO_FIELD_HELP["initial_capital"],
            )
        with capital_cols[1]:
            st.text_input(
                "Cash buffer",
                key="portfolio_edit_cash_buffer",
                help=PORTFOLIO_FIELD_HELP["cash_buffer"],
            )
        for message in _validate_setup_amount_inputs():
            st.error(message)

        st.caption(
            "Define types of investable assets used in the projection and set corresponding allocation percentages. "
            "Required: Money Market, Bonds, and Stocks. Optional classes can be added or removed. "
            "Cash (liquidity buffer) is separate from Money Market: cash has zero return and zero volatility. "
            "The total allocation percentage must sum to 100% for investable assets."
        )

        left_part, center_part, right_part = st.columns([3, 1, 2], gap="small")

        with left_part:
            col_size = [5, 3, 1]

            def render_header():
                header_cols = st.columns(
                    col_size,
                )
                with header_cols[0]:
                    st.markdown("**Asset**")
                with header_cols[1]:
                    st.markdown("**Allocation %**")

            allocation: dict[str, float] = {}

            def render_asset_line(asset):
                cols = st.columns(col_size)

                with cols[0]:
                    name_key = f"asset_name_{asset.id}"
                    if name_key not in st.session_state:
                        st.session_state[name_key] = asset.name

                    new_name = st.text_input(
                        "Asset",
                        key=name_key,
                        label_visibility="collapsed",
                        disabled=asset.required,
                        width="stretch",
                    )
                    if new_name.strip() and new_name.strip() != asset.name:
                        catalog.rename(asset.id, new_name)

                with cols[1]:
                    alloc_key = f"alloc_{asset.id}"
                    if alloc_key not in st.session_state:
                        st.session_state[alloc_key] = float(
                            st.session_state.allocation.get(asset.id, 0.0)
                        )
                    allocation[asset.id] = st.number_input(
                        "Allocation %",
                        min_value=0.0,
                        max_value=100.0,
                        step=1.0,
                        format="%.1f",
                        key=alloc_key,
                        label_visibility="collapsed",
                    )
                with cols[2]:
                    if not asset.required and st.button(
                        "×", help="Remove asset", key=f"delete_{asset.id}"
                    ):
                        try:
                            catalog.remove(asset.id)
                            st.session_state.asset_catalog = catalog
                            st.session_state.allocation.pop(asset.id, None)
                            st.session_state.pop(f"asset_name_{asset.id}", None)
                            st.session_state.pop(f"alloc_{asset.id}", None)
                            st.session_state.correlation_values = (
                                _default_correlation_values(catalog)
                            )
                            _init_mu_sigma_keys(catalog)
                            _init_correlation_keys(catalog)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))

            # render table with headers and assets
            with st.container(
                border=True,
                key="portfolio_allocation_section_table",
                vertical_alignment="center",
                horizontal_alignment="center",
                height="stretch",
            ):
                render_header()
                for k, asset in enumerate(_investable_assets(catalog)):
                    render_asset_line(asset)

                c1, c2, _ = st.columns(col_size)

                alloc_total = sum(allocation.values())
                error = abs(alloc_total - 100.0) > 0.01
                divider_style = "margin: 0.5rem 0; border: none; border-top: 1px solid #e5e7eb;"  # TODO: make this dynamic
                with c1:
                    st.markdown(
                        f'<hr style="{divider_style}" />',
                        unsafe_allow_html=True,
                    )
                    if error:
                        st.error("Allocation must sum to 100%")
                    else:
                        st.success("Total")
                with c2:
                    st.markdown(
                        f'<hr style="{divider_style}" />',
                        unsafe_allow_html=True,
                    )
                    if error:
                        st.error(f"{alloc_total:.1f}%")
                    else:
                        st.success(f"{alloc_total:.1f}%")

        with (
            center_part,
            st.container(
                border=show_border,
                key="portfolio_allocation_section_center_part",
                vertical_alignment="center",
                horizontal_alignment="center",
                height="stretch",
            ),
        ):
            if st.button("Add asset", width="stretch"):
                new_asset_name = "new asset"
                k = 0
                while slugify(new_asset_name) in st.session_state.asset_catalog.ids:
                    k += 1
                    new_asset_name = f"new asset {k + 1}"
                try:
                    added = catalog.add(new_asset_name)
                    st.session_state.asset_catalog = catalog
                    st.session_state.allocation.setdefault(added.id, 0.0)
                    st.session_state[f"asset_name_{added.id}"] = added.name
                    st.session_state[f"alloc_{added.id}"] = 0.0
                    st.session_state.correlation_values = _default_correlation_values(
                        catalog
                    )
                    _init_mu_sigma_keys(catalog)
                    _init_correlation_keys(catalog)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            if st.button(
                "Normalize",
                width="stretch",
                help="Modify the allocation percentages proportionally to sum to 100%",
            ):
                total = sum(allocation.values())
                if total > 0:
                    st.session_state.allocation = {
                        asset_id: weight / total * 100.0
                        for asset_id, weight in allocation.items()
                    }
                    _request_allocation_widget_sync()
                    st.rerun()
            if st.button(
                "Reset",
                width="stretch",
                help="Reset the allocation percentages to the defaults",
            ):
                fresh_catalog = default_asset_catalog()
                st.session_state.asset_catalog = fresh_catalog
                preset = st.session_state.get("mix_preset", "performance")
                defaults = DEFAULT_RISK_MIX_PRESETS.get(
                    preset, DEFAULT_RISK_MIX_PRESETS.get("performance", {})
                )
                st.session_state.allocation = {
                    asset.id: float(defaults.get(asset.id, 0.0))
                    for asset in _investable_assets(fresh_catalog)
                }
                _init_mu_sigma_keys(fresh_catalog)
                _init_correlation_keys(fresh_catalog)
                _clear_step_3_edit_keys(fresh_catalog)
                _request_allocation_widget_sync()
                st.rerun()
        with right_part:
            # render here a pie chart of the allocation
            pie_fig = build_pie_chart(
                allocation,
                {asset.id: asset.name for asset in _investable_assets(catalog)},
            )
            if pie_fig is not None:
                with st.container(
                    border=True,
                    key="portfolio_allocation_section_inner_pie",
                    height="stretch",
                    vertical_alignment="center",
                    horizontal_alignment="center",
                ):
                    st.pyplot(pie_fig, transparent=True)

    # Keep canonical session state in sync while editing. Skip when a
    # normalize/reset is pending so we do not overwrite the scaled allocation
    # if script execution continues past st.rerun()'s yield point.
    if not st.session_state.get("_pending_allocation_widget_sync"):
        st.session_state.asset_catalog = catalog
        st.session_state.allocation = allocation
        _commit_step_3_edit_to_session()


def _render_step_3_readonly() -> None:
    with st.container(border=False, key="assets_performance_and_vol", gap="small"):
        catalog = st.session_state.asset_catalog
        mu_sigma = _read_mu_sigma(catalog)
        correlation_values = _read_correlation_values(catalog)
        return_ids = return_model_asset_ids(catalog)
        summary_cols = st.columns(max(len(return_ids), 1))
        for idx, asset_id in enumerate(return_ids):
            mu, sigma = mu_sigma[asset_id]
            with summary_cols[idx]:
                name = html.escape(catalog.name(asset_id))
                st.markdown(
                    f'<div class="fp-return-metric-stack">'
                    f'<div class="fp-return-metric-label">{name}</div>'
                    f'<div class="fp-return-metric-value">μ {mu:.1f}%</div>'
                    f'<div class="fp-return-metric-value">σ {sigma:.1f}%</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        st.caption(_format_correlation_summary(catalog, correlation_values))


def _render_step_3_edit() -> None:
    # Edit keys are force-seeded in on_enter_edit before this form runs.
    with st.container(border=False, key="assets_performance_and_vol"):
        catalog = st.session_state.asset_catalog
        return_ids = return_model_asset_ids(catalog)

        with st.container(border=False):
            st.markdown(
                '⚠️<span style="color: orange;">It is the user sole responsibility to select appropriate values for each asset.</span>',
                help='For help, the user may turn to an investment professional or try, at his own peril, to use an AI agent with a prompt like, for example : "Please provide historic average and standard deviation ofannual return and stock index X in the last Y years, net of investment expenses."',
                unsafe_allow_html=True,
            )

        st.subheader(
            "Returns",
            help="Expected return (mu) and volatility (sigma) in percent. Returns are understood to be net of any and all applicable expenses and deductions.",
        )

        left_part, right_part = st.columns(2, gap="small")

        with left_part, st.container(border=True, height="stretch"):
            colWidths = [3, 1.5, 1.5]
            header_cols = st.columns(colWidths)
            with header_cols[0]:
                st.markdown(
                    "**Asset**",
                    help="Go to the Portfolio section to add or remove assets.",
                )
            with header_cols[1]:
                st.markdown(
                    "**μ (%)**",
                    help="Expected return in percent. Returns are understood to be net of any and all applicable expenses and deductions.",
                )
            with header_cols[2]:
                st.markdown(
                    "**σ (%)**",
                    help="Volatility in percent. Volatility is a measure of the risk of the asset. It is calculated as the standard deviation of the asset's returns.",
                )

            for asset_id in return_model_asset_ids(catalog):
                cols = st.columns(colWidths)
                with cols[0]:
                    st.markdown(catalog.name(asset_id))
                with cols[1]:
                    st.number_input(
                        "μ (%)",
                        label_visibility="collapsed",
                        format="%.1f",
                        step=1.0,
                        key=f"return_edit_mu_{asset_id}",
                        help=RETURN_ASSUMPTION_HELP["mu"],
                    )
                with cols[2]:
                    st.number_input(
                        "σ (%)",
                        min_value=0.0,
                        label_visibility="collapsed",
                        format="%.1f",
                        step=1.0,
                        key=f"return_edit_sigma_{asset_id}",
                        help=RETURN_ASSUMPTION_HELP["sigma"],
                    )
        with right_part:
            mu_sigma_chart = {
                asset_id: (
                    float(st.session_state.get(f"return_edit_mu_{asset_id}", 0.0)),
                    float(st.session_state.get(f"return_edit_sigma_{asset_id}", 0.0)),
                )
                for asset_id in return_ids
            }
            range_fig = build_mu_sigma_range_figure(
                mu_sigma_chart,
                {asset_id: catalog.name(asset_id) for asset_id in return_ids},
                asset_order=return_ids,
            )
            with st.container(border=True, height="stretch"):
                if range_fig is not None:
                    st.pyplot(range_fig, transparent=True, width="content")

        st.subheader(
            "Pairwise correlations",
            help="Correlation between the returns of two assets. A value of 1 means the assets move perfectly together, a value of -1 means they move perfectly opposite, and a value of 0 means they are uncorrelated.",
        )
        asset_order = return_model_asset_ids(catalog)

        ccor0 = st.container(border=True, horizontal=True)
        with ccor0:
            ccor1 = st.container(border=False, horizontal=True)
            ccor2 = st.container(border=False, width=150)
        for left, right in _correlation_pairs(catalog):
            label = f"{catalog.name(left)} \n\n {catalog.name(right)}"
            canonical = normalize_correlation_pair(left, right, asset_order)
            edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = float(
                    st.session_state.correlation_values.get(canonical, 0.0)
                )
            with ccor1:
                st.number_input(
                    label,
                    min_value=-1.0,
                    max_value=1.0,
                    step=0.05,
                    format="%.2f",
                    key=edit_key,
                    width=130,
                )
        with ccor2:
            st.button(
                "Reset correlations to defaults",
                key="return_assumptions_reset_corr",
                width=130,
                on_click=_reset_correlation_assumptions_to_defaults,
            )
            st.button(
                "Set no correlations",
                help="Reset the correlation between all assets to zero",
                key="return_assumptions_reset_all",
                width=130,
                on_click=_set_no_correlations,
            )

        _commit_step_4_edit_to_session(catalog)


def _render_step_5_results(
    result: RunResult,
    result_year: int,
    *,
    include_summary: bool = True,
) -> None:
    """Render post-run charts, metrics, optional summary table, and export links."""
    _render_charts(result)
    _render_outcome_probability_metrics(result, result_year)
    if include_summary:
        _render_summary(result)
    st.subheader("Export")
    if result.output_csv.exists():
        st.download_button(
            "Download output.csv",
            data=result.output_csv.read_bytes(),
            file_name="output.csv",
            mime="text/csv",
        )
    st.caption(f"CSV written to: {result.output_csv}")
    st.caption(f"Audit trail written to: {result.audit_path}")


def _check_config_validity() -> None:
    config = _collect_assumptions().to_simulation_config()
    problems = find_config_problems(config)
    if problems:
        st.session_state.config_problems = problems
    else:
        st.session_state.config_problems = None


def _has_result() -> bool:
    return st.session_state.result is not None


def _config_can_run() -> bool:
    """True when the last validation found no config problems."""
    return st.session_state.get("config_problems") is None


def _render_setup_summary_readonly() -> None:
    """Readonly setup metrics while a simulation is running (no widget keys)."""
    portfolio = st.session_state.portfolio
    st.subheader("Simulation setup")
    cols = st.columns(4)
    cols[0].metric("Initial capital", portfolio["initial_capital"])
    cols[1].metric("Cash buffer", portfolio["cash_buffer"])
    cols[2].metric("Horizon", f"{int(portfolio['max_year'])} yrs")
    cols[3].metric("Projections", f"{int(portfolio['nb_projections']):,}")
    desc = str(portfolio.get("description", "") or "").strip()
    if desc:
        st.caption(desc)


def _result_year() -> int:
    return int(
        st.session_state.get(
            "result_max_year",
            _read_portfolio_fields()["max_year"],
        )
    )


def _on_sim_dialog_dismiss() -> None:
    """Handle native dialog dismiss (header ✕, Esc, or click outside).

    Re-opens the overlay into a confirmation view so dismiss is never a silent
    hard-close while a job is active or results still need a save prompt.
    """
    # Already on a confirmation screen.
    if st.session_state.get("sim_confirm_cancel"):
        # Dismiss cancel prompt → keep running (same as "No, keep running").
        st.session_state.sim_confirm_cancel = False
        st.session_state.sim_overlay_open = True
        return
    if st.session_state.get("sim_confirm_save"):
        # Dismiss save prompt → close without saving.
        st.session_state.sim_confirm_save = False
        st.session_state.sim_overlay_open = False
        return

    job = _get_active_sim_job()
    if job is not None and int(job.completed) < int(job.nb_projections):
        # Running: ask before aborting.
        st.session_state.sim_confirm_cancel = True
        st.session_state.sim_confirm_save = False
        st.session_state.sim_overlay_open = True
        return

    # Completed (or error with no job): ask about saving assumptions.
    st.session_state.sim_confirm_save = True
    st.session_state.sim_confirm_cancel = False
    st.session_state.sim_overlay_open = True


@st.dialog(
    "Monte Carlo simulation",
    width="large",
    dismissible=True,
    on_dismiss=_on_sim_dialog_dismiss,
)
def _simulation_overlay() -> None:
    """Overlay: live progress/charts while running, then final results.

    Uses short projection batches + ``st.rerun()`` so the native dismiss control
    stays usable. Dismiss while running → cancel confirmation; after complete →
    save yes/no. Job lives in ``st.session_state`` so batches survive reruns.
    """
    pending = bool(st.session_state.get("run_simulation_requested"))
    job = _get_active_sim_job()

    # --- Confirmations (same dialog body after native dismiss reopens us) ---
    if st.session_state.get("sim_confirm_cancel"):
        st.warning("Cancel the simulation?")
        st.caption("Progress so far will be discarded. Previous results are kept.")
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button(
                "Yes, cancel",
                key="sim_confirm_cancel_yes",
                type="primary",
                width="stretch",
            ):
                _discard_active_sim_job()
                _set_simulation_running(False)
                st.session_state.run_simulation_requested = False
                st.session_state.sim_confirm_cancel = False
                _close_sim_overlay()
                st.rerun()
        with no_col:
            if st.button(
                "No, keep running",
                key="sim_confirm_cancel_no",
                width="stretch",
            ):
                st.session_state.sim_confirm_cancel = False
                st.rerun()
        return

    if st.session_state.get("sim_confirm_save"):
        st.info("Save scenario assumptions before closing?")
        yes_col, no_col = st.columns(2)
        with yes_col:
            if st.button(
                "Yes, save",
                key="sim_confirm_save_yes",
                type="primary",
                width="stretch",
            ):
                ok, message = _save_assumptions_to_file()
                if ok:
                    st.session_state.sim_confirm_save = False
                    st.session_state["_assumptions_load_message"] = message
                    _close_sim_overlay()
                    st.rerun()
                st.error(message)
        with no_col:
            if st.button(
                "No, just close",
                key="sim_confirm_save_no",
                width="stretch",
            ):
                st.session_state.sim_confirm_save = False
                _close_sim_overlay()
                st.rerun()
        return

    # Start a new job when Run was just requested.
    if pending and job is None:
        st.session_state.run_simulation_requested = False
        try:
            job = _start_active_sim_job()
        except ValueError as exc:
            st.error(str(exc))
            _set_simulation_running(False)
            st.caption("Dismiss this dialog when ready.")
            return
        except (RuntimeError, OSError, ImportError, TypeError, KeyError) as exc:
            st.error(f"Simulation failed: {exc}")
            _set_simulation_running(False)
            st.caption("Dismiss this dialog when ready.")
            return

    # --- In-progress run (batched) ---
    if job is not None and int(job.completed) < int(job.nb_projections):
        total = max(1, int(job.nb_projections))
        current = int(job.completed)
        st.caption("Live progress — charts update as projections complete.")
        st.progress(
            current / total,
            text=(
                f"Running projection {current:,} of {total:,}..."
                if current < total
                else f"Finished {total:,} projections."
            ),
        )
        if current > 0:
            _render_live_charts(
                job.nav_fan,
                int(job.config.max_year),
                projections_done=current,
                projections_total=total,
            )

        # Advance after painting UI so native dismiss can be used between batches.
        batch = _sim_batch_size(total)
        try:
            status = job.run_batch(batch)
        except (RuntimeError, OSError, ValueError, TypeError, KeyError) as exc:
            st.error(f"Simulation failed: {exc}")
            _discard_active_sim_job()
            _set_simulation_running(False)
            st.caption("Dismiss this dialog when ready.")
            return

        if status == "done":
            st.session_state.result = job.result()
            st.session_state.result_max_year = int(job.config.max_year)
            _discard_active_sim_job()
            _set_simulation_running(False)
            st.session_state.sim_overlay_open = True
            st.rerun()
        else:
            st.rerun()
        return

    # Edge: job finished but still referenced
    if job is not None:
        st.session_state.result = job.result()
        st.session_state.result_max_year = int(job.config.max_year)
        _discard_active_sim_job()
        _set_simulation_running(False)
        st.session_state.sim_overlay_open = True
        st.rerun()
        return

    # --- Completed results view (dismiss via native dialog ✕) ---
    if _has_result():
        st.success("Simulation complete.")
        _render_step_5_results(
            st.session_state.result,
            _result_year(),
            include_summary=False,
        )
    else:
        st.info("No simulation result to display.")
        st.caption("Dismiss this dialog when ready.")


def _render_step_4_panel_content() -> None:
    """Step 4 panel: setup + status/controls; charts live in the overlay (option A).

    Stable three-slot skeleton so Streamlit does not remap widgets into Steps 1–3
    when switching idle ↔ running.
    """
    running = _simulation_running()
    has_result = _has_result()

    # --- Slot 1: setup (always present) ---
    with st.container(key="sim_slot_setup_v5"):
        if running:
            _render_setup_summary_readonly()
        else:
            _render_setup_fields()
            _check_config_validity()


    # --- Slot 2: status / persistent results (no live charts — those are overlay) ---
    with st.container(key="sim_slot_status_v5"):
        if running:
            st.info(
                "Simulation is running in the overlay window. "
                "Live charts and progress appear there."
            )
        elif has_result:
            # Persistent record on the main page after the run finishes.
            _render_step_5_results(st.session_state.result, _result_year())
        elif not _config_can_run():
            problems = st.session_state.config_problems or []
            details = "\n".join(f"- {problem!s}" for problem in problems)
            st.error(
                "Invalid configuration. Please check the assumptions and try again.\n"
                f"{details}"
            )
        # Valid idle config: no status message — Run simulation is enough.


    # --- Slot 3: run controls ---
    with st.container(key="sim_slot_controls_v5"):
        config_ok = _config_can_run()
        # Hide Run when configuration is invalid; show (disabled) while running.
        if config_ok or running:
            run_label = "Refresh simulation" if has_result else "Run simulation"
            st.button(
                run_label,
                key="sim_run_btn_v5",
                type="primary",
                disabled=running or not config_ok,
                width="stretch",
                on_click=_request_simulation_run,
            )
        if (has_result or running) and st.button(
            "Discard simulation",
            key="sim_discard_btn_v5",
            width="stretch",
            disabled=running,
        ) and not running:
            st.session_state.result = None
            _close_sim_overlay()
            st.rerun()


def _render_simulation_section() -> None:
    """Render Step 4 with fixed-width step label and stretched content column."""
    left_w = int(THEME.get("section_left_column_width", 100))
    with st.container(
        horizontal=True,
        width="stretch",
        gap="small",
        vertical_alignment="center",
        key="section_step_4_row_v5",
    ):
        with st.container(
            width=left_w,
            border=False,
            key="step_4_left_col_v5",
        ):
            st.markdown(
                '<p class="fp-section-title">Step 4</p>',
                unsafe_allow_html=True,
            )
        with st.container(
            width="stretch",
            border=False,
            key="step_4_right_col_v5",
        ):
            st.header("Simulation")
            with st.container(
                width="stretch",
                border=True,
                key="sim_section_panel_v5",
            ):
                _render_step_4_panel_content()


# Section numbering (display):
#   Step 1 = flows (internal step_2 helpers)
#   Step 2 = allocation (internal step_3 helpers)
#   Step 3 = returns (internal step_4 helpers)
#   Step 4 = setup + run (via _render_simulation_section); charts in overlay
section1 = SectionContentEditable(
    name="Step 1",
    title="Contributions, withdrawals, and additional flows",
    edit_form=_render_step_1_edit,
    readonly_form=_render_step_1_readonly,
    on_enter_edit=_on_enter_step_1_edit,
    on_exit_edit=_on_exit_step_1_edit,
)

section2 = SectionContentEditable(
    name="Step 2",
    title="Portfolio",
    edit_form=_render_step_2_edit,
    readonly_form=_render_step_2_readonly,
    on_enter_edit=_on_enter_step_2_edit,
    on_exit_edit=_on_exit_step_2_edit,
)

section3 = SectionContentEditable(
    name="Step 3",
    title="Assets Performance",
    edit_form=_render_step_3_edit,
    readonly_form=_render_step_3_readonly,
    on_enter_edit=_on_enter_step_3_edit,
    on_exit_edit=_on_exit_step_3_edit,
)

# Kept for tests / API compatibility (name/title only).
section4 = Section(
    name="Step 4",
    title="Simulation",
    content_form=_render_step_4_panel_content,
    panel_key="sim_section_panel_v5",
)


def _render_sidebar() -> None:
    with st.sidebar:
        if st.session_state.get("_assumptions_load_message"):
            st.success(st.session_state.pop("_assumptions_load_message"))
        _render_assumptions_file_controls()
        st.divider()
        st.header("Output")
        st.text_input("Output directory", key="output_dir")
        st.info(
            "After running, refresh `output/finproj.xlsx` in Excel for deeper analysis "
            "(fan charts, scenario navigator)."
        )
        st.caption(
            "Mac: open the output folder in Finder. Windows: open in File Explorer."
        )


def _render_workflow_sections() -> None:
    from click_panel import ClickPanelRegistry

    ClickPanelRegistry.reset()

    section1.render()
    section2.render()
    section3.render()
    _render_simulation_section()

    # Option A: live charts + final results open in a modal overlay.
    # The Monte Carlo work runs inside the dialog so progress widgets stay there.
    if _sim_overlay_should_open():
        st.session_state.sim_overlay_open = True
        _simulation_overlay()

    SectionContentEditable.install_click_handlers()


def main() -> None:
    st.set_page_config(
        page_title="finproj",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_theme()
    _init_session_state()
    _process_pending_assumptions()
    # Before sidebar/_collect_assumptions can commit stale alloc_* widgets.
    _apply_pending_allocation_widget_sync()

    _render_app_header()
    _render_sidebar()
    _render_workflow_sections()


if __name__ == "__main__":
    main()
