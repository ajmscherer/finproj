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


# from click_panel import ClickPanelRegistry
from section import SectionContentEditable, Section

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from assumptions import DEFAULT_ASSUMPTIONS_DIR, Assumptions  # noqa: E402
from asset_classes import AssetCatalog, default_asset_catalog, slugify  # noqa: E402
from inv_proj import cv  # noqa: E402
from theme import THEME, inject_theme, step1_edit_layout_css  # noqa: E402
from formatting import format_compact_amount, render_summary_statistics_table  # noqa: E402
from charts import (  # noqa: E402
    build_mu_sigma_range_figure,
    build_nav_distribution_figure,
    build_nav_fan_figure,
    build_pie_chart,
    extract_latest_projection_curve,
)
from inv_proj_runner import (  # noqa: E402
    DEFAULT_NEW_ASSET_RISK,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RISK_CORRELATION,
    DEFAULT_RISK_MIX_PRESETS,
    DEFAULT_RISK_PARAM,
    RunResult,
    investable_asset_ids,
    normalize_correlation_pair,
    return_model_asset_ids,
    success_rate,
    validate_allocation,
    validate_correlation,
    find_config_problems,
)
from viva_adapter import HAS_VIVA, default_viva_start_year  # noqa: E402
import inv_proj  # noqa: E402
import inv_proj_runner  # noqa: E402


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


def _investable_assets(catalog: AssetCatalog) -> list:
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
    "initial_capital": "1M",
    "contributions": "0k",
    "withdrawals": "50k",
    "cash_buffer": "150k",
    "max_year": 20,
    "nb_projections": 2000,
    "viva_source": "",
    "viva_start_year": default_viva_start_year(),
    "viva_probabilistic": False,
}

PORTFOLIO_FIELD_HELP = {
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
}

VIVA_FIELD_HELP = {
    "viva_source": (
        "Optional [Viva](https://github.com/ajmscherer/viva) DSL program describing "
        "portfolio contributions and withdrawals over time. When set, Viva schedules "
        "replace the flat annual amounts above. Positive amounts are contributions "
        "(e.g. `flow: insurance, 100k, upon death`); negative amounts are withdrawals."
    ),
    "viva_start_year": (
        "Calendar year for period 1 of the simulation when using a Viva model."
    ),
    "viva_probabilistic": (
        "Draw probabilistic life events from Viva on each Monte Carlo projection. "
        "Requires a Viva Pro license after the 30-day evaluation; deterministic "
        "flows are MIT-licensed."
    ),
}

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

PORTFOLIO_AMOUNT_FIELDS = (
    ("Initial capital", "portfolio_edit_initial_capital"),
    ("Annual contributions", "portfolio_edit_contributions"),
    ("Annual withdrawals", "portfolio_edit_withdrawals"),
    ("Cash buffer", "portfolio_edit_cash_buffer"),
)


def _validate_portfolio_amount_inputs() -> list[str]:
    errors: list[str] = []
    parsed: dict[str, float] = {}

    for label, key in PORTFOLIO_AMOUNT_FIELDS:
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

    capital = parsed.get("Initial capital")
    cash_buffer = parsed.get("Cash buffer")
    if capital is not None and cash_buffer is not None and cash_buffer >= capital:
        errors.append("Cash buffer must be less than initial capital.")

    return errors


def _simulation_projection_years() -> list[int]:
    max_year = max(1, int(st.session_state.get("portfolio_edit_max_year", 20)))
    return list(range(1, max_year + 1))


def _init_flow_period_edit_widgets(max_year: int) -> None:
    horizon = max(1, int(max_year))
    for slug in ("contributions", "withdrawals"):
        prefix = f"portfolio_edit_{slug}"
        st.session_state[f"{prefix}_from_period"] = 1
        st.session_state[f"{prefix}_to_period"] = horizon
        st.session_state[f"{prefix}_periods_initialized"] = True


def _ensure_flow_period_defaults(base_key: str, horizon: int) -> tuple[str, str]:
    from_key = f"{base_key}_from_period"
    to_key = f"{base_key}_to_period"
    init_key = f"{base_key}_periods_initialized"
    horizon = max(1, int(horizon))
    if not st.session_state.get(init_key):
        st.session_state[from_key] = 1
        st.session_state[to_key] = horizon
        st.session_state[init_key] = True
    return from_key, to_key


def _init_portfolio_fields() -> None:
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = copy.deepcopy(PORTFOLIO_FIELD_DEFAULTS)


def _sync_portfolio_to_edit_widgets() -> None:
    portfolio = st.session_state.portfolio
    st.session_state.portfolio_edit_initial_capital = portfolio["initial_capital"]
    st.session_state.portfolio_edit_contributions = portfolio["contributions"]
    st.session_state.portfolio_edit_withdrawals = portfolio["withdrawals"]
    st.session_state.portfolio_edit_cash_buffer = portfolio["cash_buffer"]
    st.session_state.portfolio_edit_max_year = int(portfolio["max_year"])
    st.session_state.portfolio_edit_nb_projections = int(portfolio["nb_projections"])
    st.session_state.portfolio_edit_viva_source = portfolio.get("viva_source", "")
    st.session_state.portfolio_edit_viva_start_year = int(
        portfolio.get("viva_start_year", default_viva_start_year())
    )
    st.session_state.portfolio_edit_viva_probabilistic = bool(
        portfolio.get("viva_probabilistic", False)
    )
    _init_flow_period_edit_widgets(int(portfolio["max_year"]))


def _sync_edit_widgets_to_portfolio() -> None:
    portfolio = st.session_state.portfolio
    portfolio["initial_capital"] = st.session_state.portfolio_edit_initial_capital
    portfolio["contributions"] = st.session_state.portfolio_edit_contributions
    portfolio["withdrawals"] = st.session_state.portfolio_edit_withdrawals
    portfolio["cash_buffer"] = st.session_state.portfolio_edit_cash_buffer
    portfolio["max_year"] = int(st.session_state.portfolio_edit_max_year)
    portfolio["nb_projections"] = int(st.session_state.portfolio_edit_nb_projections)
    portfolio["viva_source"] = st.session_state.portfolio_edit_viva_source
    portfolio["viva_start_year"] = int(st.session_state.portfolio_edit_viva_start_year)
    portfolio["viva_probabilistic"] = bool(
        st.session_state.portfolio_edit_viva_probabilistic
    )


def _exit_portfolio_edit(*, force: bool = False) -> None:
    if not st.session_state.get("portfolio_assumptions_editing"):
        return
    if not _validate_portfolio_amount_inputs():
        _sync_edit_widgets_to_portfolio()
    elif not force:
        return
    st.session_state.portfolio_assumptions_editing = False


def _exit_asset_allocation_edit() -> None:
    if not st.session_state.get("asset_allocation_editing"):
        return
    _sync_edit_widgets_to_catalog()
    st.session_state.asset_allocation_editing = False


def _exit_return_assumptions_edit() -> None:
    if not st.session_state.get("return_assumptions_editing"):
        return
    _sync_edit_widgets_to_return_assumptions(st.session_state.asset_catalog)
    st.session_state.return_assumptions_editing = False


def _exit_other_section_edits(active: str) -> None:
    if active != "portfolio":
        _exit_portfolio_edit(force=True)
    if active != "asset_allocation":
        _exit_asset_allocation_edit()
    if active != "return_assumptions":
        _exit_return_assumptions_edit()


def _enter_return_assumptions_edit() -> None:
    _exit_other_section_edits("return_assumptions")
    catalog: AssetCatalog = st.session_state.asset_catalog
    _sync_return_assumptions_to_edit_widgets(catalog)
    st.session_state.return_assumptions_editing = True


def _finish_return_assumptions_edit() -> None:
    _exit_return_assumptions_edit()


def _read_portfolio_fields() -> dict:
    if st.session_state.get("portfolio_assumptions_editing"):
        if not _validate_portfolio_amount_inputs():
            _sync_edit_widgets_to_portfolio()
    return st.session_state.portfolio


def _set_simulation_running(running: bool) -> None:
    st.session_state.simulation_running = running


def _simulation_running() -> bool:
    return bool(st.session_state.get("simulation_running", False))


def _request_simulation_run() -> None:
    st.session_state.run_simulation_requested = True
    _set_simulation_running(True)
    st.rerun()


def _execute_simulation_run(live_charts_placeholder: Any) -> bool:
    """
    Run Monte Carlo simulation. Returns True on success.
    
    live_charts_placeholder: the placeholder for the live charts
    """

    live_charts_placeholder.empty()
    try:
        assumptions = _collect_assumptions()    
        config = assumptions.to_simulation_config()
        validate_allocation(config.risk_mix, config.asset_catalog)
        validate_correlation(config.risk_param, config.risk_correlation)
        live_distribution_year = config.max_year
        chart_update_interval = _chart_update_interval(config.nb_projections)

        progress = st.progress(0.0, text="Starting simulation...")
        status = st.empty()

        def progress_callback(
            current: int,
            total: int,
            nav_fan: Any | None = None,
        ) -> None:
            progress.progress(
                current / total,
                text=f"Running projection {current:,} of {total:,}...",
            )
            if nav_fan is None:
                return
            if current == 1 or (
                current != total and current % chart_update_interval == 0
            ):
                with live_charts_placeholder.container():
                    _render_live_charts(
                        nav_fan,
                        live_distribution_year,
                        projections_done=current,
                        projections_total=total,
                    )

        importlib.reload(inv_proj)
        importlib.reload(inv_proj_runner)
        result = inv_proj_runner.run_simulation(
            config,
            progress_callback=progress_callback,
        )

        live_charts_placeholder.empty()

        progress.progress(1.0, text="Simulation complete.")
        status.success(
            f"Finished {config.nb_projections:,} projections over {config.max_year} years."
        )
        st.session_state.result = result
        st.session_state.result_max_year = int(_read_portfolio_fields()["max_year"])
        return True
    except ValueError as exc:
        st.error(str(exc))
        return False
    except Exception as exc:
        st.error(f"Simulation failed: {exc}")
        return False


def _init_session_state() -> None:
    st.session_state.setdefault("asset_catalog", default_asset_catalog())
    st.session_state.setdefault(
        "allocation", copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
    )
    st.session_state.setdefault("mix_preset", "performance")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("simulation_running", False)
    st.session_state.setdefault("run_simulation_requested", False)
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
    if st.session_state.get("return_assumptions_editing"):
        _sync_edit_widgets_to_return_assumptions(catalog)
    mu_sigma: dict[str, tuple[float, float]] = {}
    for asset_id in return_model_asset_ids(catalog):
        mu_sigma[asset_id] = (
            float(st.session_state[f"mu_{asset_id}"]),
            float(st.session_state[f"sigma_{asset_id}"]),
        )
    return mu_sigma


def _read_correlation_values(catalog: AssetCatalog) -> dict[tuple[str, str], float]:
    if st.session_state.get("return_assumptions_editing"):
        _sync_edit_widgets_to_return_assumptions(catalog)
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
        viva_start_year=int(portfolio.get("viva_start_year", default_viva_start_year())),
        viva_probabilistic=bool(portfolio.get("viva_probabilistic", False)),
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
        "initial_capital": assumptions.initial_capital,
        "contributions": assumptions.contributions,
        "withdrawals": assumptions.withdrawals,
        "cash_buffer": assumptions.cash_buffer,
        "max_year": assumptions.max_year,
        "nb_projections": assumptions.nb_projections,
        "viva_source": assumptions.viva_source,
        "viva_start_year": assumptions.viva_start_year or default_viva_start_year(),
        "viva_probabilistic": assumptions.viva_probabilistic,
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
        try:
            assumptions = _collect_assumptions()
            if st.session_state.assumptions_file:
                path = Path(st.session_state.assumptions_file)
            else:
                path = DEFAULT_ASSUMPTIONS_DIR / assumptions.safe_filename()
                st.session_state.assumptions_file = str(path)
            assumptions.save(path)
            st.success(f"Saved to `{path}`.")
        except (ValueError, OSError) as exc:
            st.error(str(exc))

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


def _sync_catalog_to_edit_widgets(catalog: AssetCatalog) -> None:
    for asset in _investable_assets(catalog):
        st.session_state[f"asset_name_{asset.id}"] = asset.name
    st.session_state.setdefault("asset_classes_edit_new_name", "")


def _sync_edit_widgets_to_catalog() -> None:
    catalog: AssetCatalog = st.session_state.asset_catalog.copy()
    for asset in _investable_assets(catalog):
        name_key = f"asset_name_{asset.id}"
        if name_key in st.session_state:
            new_name = str(st.session_state[name_key]).strip()
            if new_name and new_name != asset.name:
                catalog.rename(asset.id, new_name)
    st.session_state.asset_catalog = catalog


def _read_asset_catalog() -> AssetCatalog:
    if st.session_state.get("asset_allocation_editing"):
        _sync_edit_widgets_to_catalog()
    return st.session_state.asset_catalog


def _sync_allocation_to_edit_widgets(investable_ids: list[str]) -> None:
    for asset_id in investable_ids:
        st.session_state[f"alloc_{asset_id}"] = float(
            st.session_state.allocation.get(asset_id, 0.0)
        )


def _request_allocation_widget_sync() -> None:
    st.session_state["_pending_allocation_widget_sync"] = True


def _reset_correlation_assumptions_to_defaults() -> None:
    catalog = st.session_state.asset_catalog
    st.session_state.correlation_values = _default_correlation_values(catalog)
    _sync_return_assumptions_to_edit_widgets(catalog)


def _sync_return_assumptions_to_edit_widgets(catalog: AssetCatalog) -> None:
    for asset_id in return_model_asset_ids(catalog):
        st.session_state[f"return_edit_mu_{asset_id}"] = float(
            st.session_state[f"mu_{asset_id}"]
        )
        st.session_state[f"return_edit_sigma_{asset_id}"] = float(
            st.session_state[f"sigma_{asset_id}"]
        )
    asset_order = return_model_asset_ids(catalog)
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
        st.session_state[edit_key] = float(
            st.session_state.correlation_values.get(canonical, 0.0)
        )


def _sync_edit_widgets_to_return_assumptions(catalog: AssetCatalog) -> None:
    for asset_id in return_model_asset_ids(catalog):
        mu_key = f"return_edit_mu_{asset_id}"
        sigma_key = f"return_edit_sigma_{asset_id}"
        if mu_key in st.session_state:
            st.session_state[f"mu_{asset_id}"] = float(st.session_state[mu_key])
        if sigma_key in st.session_state:
            st.session_state[f"sigma_{asset_id}"] = float(st.session_state[sigma_key])

    asset_order = return_model_asset_ids(catalog)
    values: dict[tuple[str, str], float] = {}
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
        rho = float(st.session_state.get(edit_key, 0.0))
        values[canonical] = rho
        st.session_state[f"corr_{canonical[0]}_{canonical[1]}"] = rho
    st.session_state.correlation_values = values


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


def _set_no_correlations() -> None:
    catalog = st.session_state.asset_catalog
    st.session_state.correlation_values = {
        (left, right): 0.0 for left, right in _correlation_pairs(catalog)
    }
    _sync_return_assumptions_to_edit_widgets(catalog)


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


def _render_step_1_readonly() -> None:
    portfolio = st.session_state.portfolio
    with st.container(border=False, key="portfolio_section2"):
        summary_cols = st.columns(6)
        summary_cols[0].metric(
            "Initial capital",
            portfolio["initial_capital"],
            help=PORTFOLIO_FIELD_HELP["initial_capital"],
        )
        summary_cols[1].metric(
            "Annual contributions",
            portfolio["contributions"],
            help=PORTFOLIO_FIELD_HELP["contributions"],
        )
        summary_cols[2].metric(
            "Annual withdrawals",
            portfolio["withdrawals"],
            help=PORTFOLIO_FIELD_HELP["withdrawals"],
        )
        summary_cols[3].metric(
            "Cash buffer",
            portfolio["cash_buffer"],
            help=PORTFOLIO_FIELD_HELP["cash_buffer"],
        )
        summary_cols[4].metric(
            "Horizon",
            f"{int(portfolio['max_year'])} yrs",
            help=PORTFOLIO_FIELD_HELP["max_year"],
        )
        summary_cols[5].metric(
            "Projections",
            f"{int(portfolio['nb_projections']):,}",
            help=PORTFOLIO_FIELD_HELP["nb_projections"],
        )
        if portfolio.get("viva_source", "").strip():
            st.caption(
                "Viva cash-flow model active — flat annual amounts are overridden "
                "by the Viva schedule (positive = contribution, negative = withdrawal)."
            )


def _render_step_1_edit() -> None:

    with st.container(border=False, key="portfolio_section2"):
        if "portfolio_edit_initial_capital" not in st.session_state:
            _sync_portfolio_to_edit_widgets()
        st.markdown(step1_edit_layout_css(), unsafe_allow_html=True)
        with st.container(horizontal=True, gap="small", key="portfolio_step1_layout"):
            left_side = st.container(
                width=int(THEME["step1_left_column_width_px"]),
                key="portfolio_step1_left",
            )
            right_side = st.container(width="stretch", key="portfolio_step1_right")

            with left_side:
                st.text_input(
                    "Initial capital",
                    key="portfolio_edit_initial_capital",
                    help=PORTFOLIO_FIELD_HELP["initial_capital"],
                )
                st.text_input(
                    "Cash buffer",
                    key="portfolio_edit_cash_buffer",
                    help=PORTFOLIO_FIELD_HELP["cash_buffer"],
                )
                st.number_input(
                    "Horizon (years)",
                    min_value=1,
                    max_value=50,
                    step=1,
                    key="portfolio_edit_max_year",
                    help=PORTFOLIO_FIELD_HELP["max_year"],
                )
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
                for message in _validate_portfolio_amount_inputs():
                    st.error(message)

            with right_side:

                def period_block(name: str, help: str, key: str | None = None) -> None:
                    slug = name.lower().replace(" ", "_")
                    if not key:
                        key = f"portfolio_edit_{slug}"
                    years = _simulation_projection_years()
                    horizon = years[-1]
                    from_key, to_key = _ensure_flow_period_defaults(key, horizon)
                    if int(st.session_state[from_key]) not in years:
                        st.session_state[from_key] = years[0]
                    if int(st.session_state[to_key]) not in years:
                        st.session_state[to_key] = horizon
                    from_period = int(st.session_state[from_key])
                    to_years = list(range(from_period, years[-1] + 1))
                    if int(st.session_state[to_key]) not in to_years:
                        st.session_state[to_key] = to_years[-1]
                    if int(st.session_state[to_key]) < from_period:
                        st.session_state[to_key] = from_period

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

                period_block("Contributions", PORTFOLIO_FIELD_HELP["contributions"])
                period_block("Withdrawals", PORTFOLIO_FIELD_HELP["withdrawals"])

                if not HAS_VIVA:
                    st.warning(
                        "Viva is not installed in this environment. "
                        "Re-run `./run_gui.sh` or `pip install -r requirements-gui.txt`."
                    )
                st.text_area(
                    "Viva program",
                    key="portfolio_edit_viva_source",
                    height=180,
                    help=VIVA_FIELD_HELP["viva_source"],
                    placeholder=(
                        "life: Julian, person, born 1980\n"
                        "event: death, at age 90\n"
                        "flow: insurance, 100k, upon death\n"
                        "flow: living_expenses, -50k per year, for 20 years"
                    ),
                )
                viva_col1, viva_col2 = st.columns(2)
                with viva_col1:
                    st.number_input(
                        "Viva start year",
                        min_value=1900,
                        max_value=2200,
                        step=1,
                        key="portfolio_edit_viva_start_year",
                        help=VIVA_FIELD_HELP["viva_start_year"],
                    )
                with viva_col2:
                    st.checkbox(
                        "Probabilistic life events",
                        key="portfolio_edit_viva_probabilistic",
                        help=VIVA_FIELD_HELP["viva_probabilistic"],
                    )
                if st.session_state.portfolio_edit_viva_probabilistic:
                    st.info(
                        "Probabilistic Viva features require a Viva Pro license after "
                        "the 30-day evaluation period. Deterministic flows remain MIT-licensed."
                    )

        _sync_edit_widgets_to_portfolio()


def _render_step_2_readonly() -> None:
    catalog = _read_asset_catalog()
    with st.container(border=False, key="portfolio_allocation_section_inner"):
        allocation = st.session_state.allocation
        assets = _investable_assets(catalog)
        summary_cols = st.columns(max(len(assets), 1))
        for idx, asset in enumerate(assets):
            weight = allocation.get(asset.id, 0.0)
            with summary_cols[idx]:
                st.metric(asset.name, f"{weight:.0f}%")
        # if total allocation is not 100%, show a warning
        alloc_total = sum(allocation.values())
        error = abs(alloc_total - 100.0) > 0.01
        if error:
            st.error(
                "Allocation must sum to 100%. Please edit and adjust the allocations to sum to 100%."
            )


def _render_step_2_edit() -> None:
    catalog = _read_asset_catalog()
    investable_ids = investable_asset_ids(catalog)
    investable = _investable_assets(catalog)

    if st.session_state.pop("_pending_allocation_widget_sync", False):
        _sync_allocation_to_edit_widgets(investable_ids)
    elif investable and f"asset_name_{investable[0].id}" not in st.session_state:
        _sync_catalog_to_edit_widgets(catalog)
        _sync_allocation_to_edit_widgets(investable_ids)

    catalog: AssetCatalog = st.session_state.asset_catalog.copy()

    show_border = False  # TODO: make this dynamic based on the section mode

    with st.container(border=False, key="portfolio_allocation_section", gap="small"):
        st.caption(
            "Define types of investable assets used in the projection and set corresponding allocation percentages. "
            "Required: Money Market, Bonds, and Stocks. Optional classes can be added or removed."
            "Note that cash is different money market. Cash have zero return and zero volatility. There are not considered an investable asset but merely a security liquidity buffer."
            "Note: The total allocation percentage must sum to 100% for investable assets."
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
                    st.session_state.setdefault(name_key, asset.name)

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
                    cp = st.session_state.allocation.get(asset.id, 0.0)
                    st.session_state.setdefault(alloc_key, cp)
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
                    if not asset.required:
                        if st.button(
                            "×", help="Remove asset", key=f"delete_{asset.id}"
                        ):
                            try:
                                catalog.remove(asset.id)
                                st.session_state.asset_catalog = catalog
                                st.session_state.allocation.pop(asset.id, None)
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

        with center_part:
            with st.container(
                border=show_border,
                key="portfolio_allocation_section_center_part",
                vertical_alignment="center",
                horizontal_alignment="center",
                height="stretch",
            ):
                if st.button("Add asset", width="stretch"):
                    new_asset_name = "new asset"
                    k = 0
                    while slugify(new_asset_name) in st.session_state.asset_catalog.ids:
                        k += 1
                        new_asset_name = f"new asset {k + 1}"
                    else:
                        try:
                            added = catalog.add(new_asset_name)
                            st.session_state.asset_catalog = catalog
                            st.session_state.allocation.setdefault(added.id, 0.0)
                            st.session_state.correlation_values = (
                                _default_correlation_values(catalog)
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

    # update session state
    st.session_state.asset_catalog = catalog
    st.session_state.allocation = allocation


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
                    f'<div class="fp-return-metric-value">σ {sigma:.1f}%</div>',
                    # f"</div>",
                    unsafe_allow_html=True,
                )
        st.caption(_format_correlation_summary(catalog, correlation_values))


def _render_step_3_edit() -> None:
    with st.container(border=False, key="assets_performance_and_vol"):
        catalog = st.session_state.asset_catalog
        return_ids = return_model_asset_ids(catalog)
        if return_ids and f"return_edit_mu_{return_ids[0]}" not in st.session_state:
            _sync_return_assumptions_to_edit_widgets(catalog)

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

        with left_part:
            with st.container(border=True, height="stretch"):
                colWidths = [3, 1.5, 1.5]
                header_cols = st.columns(colWidths)
                with header_cols[0]:
                    st.markdown(
                        "**Asset**",
                        help="Go to Portfolio Allocation section to add or remove assets.",
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
            return_ids = return_model_asset_ids(catalog)
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
        for idx, (left, right) in enumerate(_correlation_pairs(catalog)):
            label = f"{catalog.name(left)} \n\n {catalog.name(right)}"
            canonical = normalize_correlation_pair(left, right, asset_order)
            edit_key = f"return_edit_corr_{canonical[0]}_{canonical[1]}"
            st.session_state.setdefault(
                edit_key,
                float(st.session_state.correlation_values.get(canonical, 0.0)),
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

        _sync_edit_widgets_to_return_assumptions(catalog)


def _render_step_4_results(result: RunResult, result_year: int) -> None:
    _render_charts(result)
    _render_outcome_probability_metrics(result, result_year)
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


def _render_step_4_content() -> None:
    _check_config_validity()
    can_run = st.session_state.config_problems is None
    running = _simulation_running()
    has_result = _has_result()

    top_part, bottom_part = st.container(), st.container()

    with top_part:
        if running:
            st.info("Monte Carlo simulation is running…")
            charts_slot = st.empty()
            st.session_state["_step_4_live_charts_placeholder"] = charts_slot
        elif has_result:
            result: RunResult = st.session_state.result
            result_year = int(
                st.session_state.get(
                    "result_max_year",
                    _read_portfolio_fields()["max_year"],
                )
            )
            charts_slot = st.empty()
            with charts_slot.container():
                _render_step_4_results(result, result_year)
            with st.container(border=True, horizontal=True):
                if st.button(
                    "Refresh simulation",
                    width="stretch",
                    type="primary",
                    key="refresh_simulation",
                    on_click=_request_simulation_run,
                ):
                    _request_simulation_run()
                if st.button(
                    "Discard simulation",
                    width="stretch",
                ):
                    st.session_state.result = None
                    st.rerun()
        else:
            if can_run:
                st.info(
                    "Configuration is valid. Click the button below to run the simulation."
                )
            else:
                problems = st.session_state.config_problems
                msg = "\n".join([f"- {str(problem)}" for problem in problems])
                msg = f"Invalid configuration. Please check the assumptions and try again.\n{msg}"
                st.error(msg)
            if st.button(
                "Run simulation",
                key="run_simulation",
                type="primary",
                disabled=not can_run,
                width="stretch",
            ):
                _request_simulation_run()

    with bottom_part:
        _process_pending_simulation_run()

    return

  


section1 = SectionContentEditable(
    name="Step 1",
    title="Contributions, Withdrawals, and projection parameters",
    edit_form=_render_step_1_edit,
    readonly_form=_render_step_1_readonly,
)

section2 = SectionContentEditable(
    name="Step 2",
    title="Portfolio Allocation",
    edit_form=_render_step_2_edit,
    readonly_form=_render_step_2_readonly,
)

section3 = SectionContentEditable(
    name="Step 3",
    title="Assets Performance",
    edit_form=_render_step_3_edit,
    readonly_form=_render_step_3_readonly,
)

section4 = Section(
    name="Step 4",
    title="Run and review analysis",
    content_form=_render_step_4_content,
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


def _process_pending_simulation_run() -> None:
    """Run simulation queued by Step 4 (after that section has rendered)."""
    if not st.session_state.pop("run_simulation_requested", False):
        return
    charts_placeholder = st.session_state.get("_step_4_live_charts_placeholder")
    if charts_placeholder is None:
        _set_simulation_running(False)
        return
    try:
        if _execute_simulation_run(charts_placeholder):
            st.rerun()
    finally:
        _set_simulation_running(False)


def _render_workflow_sections() -> None:
    section1.render()
    section2.render()
    section3.render()
    section4.render()

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

    _render_app_header()
    _render_sidebar()
    _render_workflow_sections()


if __name__ == "__main__":
    main()
