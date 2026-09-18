# finproj - Streamlit GUI v2 (guided wizard)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GUI_V1 = PROJECT_ROOT / "gui" / "v1"
sys.path.insert(0, str(GUI_V1))
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from asset_classes import default_asset_catalog
from charts import (
    build_nav_distribution_figure,
    build_nav_fan_figure,
)
from formatting import format_compact_amount
from inv_proj import cv
from inv_proj_runner import (
    DEFAULT_NEW_ASSET_RISK,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RISK_CORRELATION,
    DEFAULT_RISK_MIX_PRESETS,
    DEFAULT_RISK_PARAM,
    investable_asset_ids,
    rate_below,
    return_model_asset_ids,
    run_simulation,
    success_rate,
    validate_allocation,
)
from theme import inject_theme

from assumptions import Assumptions

STEPS = (
    {
        "short": "Today",
        "title": "Your wealth today",
        "intro": (
            "Let's Start with a snapshot of what you have now." 
        ),
    },
    {
        "short": "In & out",
        "title": "Money you add or take out",
        "intro": (
            "Each year, you may add savings or take money out to live on. "
            "Leave an amount at 0 if it does not apply."
        ),
    },
    {
        "short": "Mix",
        "title": "How your money is invested",
        "intro": (
            "Choose how the invested part of your wealth is split. "
            "The percentages must add up to 100%. "
            "Cash you keep as a safety reserve is set separately (previous step)."
        ),
    },
    {
        "short": "Markets",
        "title": "How markets may behave",
        "intro": (
            "These numbers describe a typical year: average growth, and how bumpy "
            "the ride can be. You can keep the suggested values if you are unsure."
        ),
    },
    {
        "short": "Run",
        "title": "Run the projection",
        "intro": (
            "We will simulate many possible futures (not one forecast) and show "
            "the range of outcomes. Longer horizons and more projections take longer."
        ),
    },
    {
        "short": "Results",
        "title": "Your range of outcomes",
        "intro": (
            "Each line is one possible future. The band shows where most outcomes "
            "fall. Use this to compare “what if” — not as a promise of results."
        ),
    },
)

ASSET_BLURB = {
    "money_market": "Very steady, cash-like savings. Small ups and downs.",
    "bonds": "Loans to governments or companies. Usually steadier than stocks.",
    "stocks": "Ownership in companies. Higher growth potential, more ups and downs.",
    "real_estate": "Property-like investments. Can move with the economy.",
    "pmetal": "Gold and similar metals. Often used as a diversifier.",
    "crypto": "Digital assets. Can swing a lot from year to year.",
}

WIZARD_CSS = """
<style>
.fp2-kicker { font-size: 0.8rem; letter-spacing: 0.12em; text-transform: uppercase;
    color: #2A7A62; font-weight: 600; margin-bottom: 0.15rem; }
.fp2-intro { font-size: 1.05rem; color: #374151; line-height: 1.45; margin: 0 0 0.75rem 0; }
.fp2-help { font-size: 0.92rem; color: #4b5563; margin: 0.15rem 0 0.45rem 0; line-height: 1.4; }
div[class*="st-key-v2_timeline"] button { width: 100%; }
div[class*="st-key-v2_step_card"] {
    background: #fbfaf7;
    border-radius: 0.75rem;
}
</style>
"""


def _default_allocation(catalog) -> dict[str, float]:
    mix = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
    for asset_id in investable_asset_ids(catalog):
        mix.setdefault(asset_id, 0.0)
    return mix


def _default_data(catalog) -> dict[str, Any]:
    """Same starting figures as GUI v1."""
    mu: dict[str, float] = {}
    sigma: dict[str, float] = {}
    for asset_id in return_model_asset_ids(catalog):
        defaults = DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0]
        mu[asset_id] = float(defaults["mu"])
        sigma[asset_id] = float(defaults["sigma"])
    return {
        "initial_capital": "1M",
        "cash_buffer": "150k",
        "contributions": "0k",
        "withdrawals": "50k",
        "max_year": 20,
        "nb_projections": 2000,
        "rng_seed": 1,
        "allocation": _default_allocation(catalog),
        "mu": mu,
        "sigma": sigma,
    }


def _init() -> None:
    catalog = default_asset_catalog()
    st.session_state.setdefault("v2_step", 0)
    st.session_state.setdefault("asset_catalog", catalog)
    st.session_state.setdefault("mix_preset", "performance")
    st.session_state.setdefault("output_dir", str(DEFAULT_OUTPUT_DIR))
    st.session_state.setdefault("assumptions_name", "Untitled")
    st.session_state.setdefault("result", None)
    if "v2" not in st.session_state:
        st.session_state.v2 = _default_data(catalog)


def _data() -> dict[str, Any]:
    return st.session_state.v2


def _commit_widgets() -> None:
    """Copy any mounted (or just-unmounted) widget keys into canonical v2 data."""
    data = _data()
    catalog = st.session_state.asset_catalog
    text_map = {
        "v2w_initial_capital": "initial_capital",
        "v2w_cash_buffer": "cash_buffer",
        "v2w_contributions": "contributions",
        "v2w_withdrawals": "withdrawals",
    }
    for wkey, ckey in text_map.items():
        if wkey in st.session_state:
            data[ckey] = str(st.session_state[wkey])
    if "v2w_max_year" in st.session_state:
        data["max_year"] = int(st.session_state.v2w_max_year)
    if "v2w_nb_projections" in st.session_state:
        data["nb_projections"] = int(st.session_state.v2w_nb_projections)
    alloc = dict(data["allocation"])
    for asset_id in investable_asset_ids(catalog):
        wkey = f"v2w_alloc_{asset_id}"
        if wkey in st.session_state:
            alloc[asset_id] = float(st.session_state[wkey])
    data["allocation"] = alloc
    mu = dict(data["mu"])
    sigma = dict(data["sigma"])
    for asset_id in return_model_asset_ids(catalog):
        if f"v2w_mu_{asset_id}" in st.session_state:
            mu[asset_id] = float(st.session_state[f"v2w_mu_{asset_id}"])
        if f"v2w_sigma_{asset_id}" in st.session_state:
            sigma[asset_id] = float(st.session_state[f"v2w_sigma_{asset_id}"])
    data["mu"] = mu
    data["sigma"] = sigma


def _seed_widgets_for_step(step: int) -> None:
    """Set widget keys from canonical data *before* those widgets mount."""
    data = _data()
    catalog = st.session_state.asset_catalog
    if step == 0:
        st.session_state.v2w_initial_capital = str(data["initial_capital"])
        st.session_state.v2w_cash_buffer = str(data["cash_buffer"])
    elif step == 1:
        st.session_state.v2w_contributions = str(data["contributions"])
        st.session_state.v2w_withdrawals = str(data["withdrawals"])
    elif step == 2:
        for asset_id in investable_asset_ids(catalog):
            st.session_state[f"v2w_alloc_{asset_id}"] = float(
                data["allocation"].get(asset_id, 0.0)
            )
    elif step == 3:
        for asset_id in investable_asset_ids(catalog):
            st.session_state[f"v2w_mu_{asset_id}"] = float(data["mu"].get(asset_id, 0.0))
            st.session_state[f"v2w_sigma_{asset_id}"] = float(
                data["sigma"].get(asset_id, 0.0)
            )
    elif step == 4:
        st.session_state.v2w_max_year = int(data["max_year"])
        st.session_state.v2w_nb_projections = int(data["nb_projections"])


def _goto(step: int) -> None:
    _commit_widgets()
    st.session_state.v2_step = max(0, min(int(step), len(STEPS) - 1))
    st.rerun()


def _help(text: str) -> None:
    st.markdown(f'<p class="fp2-help">{text}</p>', unsafe_allow_html=True)


def _render_timeline(current: int) -> None:
    n = len(STEPS)
    cols = st.columns(n, gap="small")
    has_result = st.session_state.result is not None
    for i, col in enumerate(cols):
        with col:
            label = f"{i + 1}  {STEPS[i]['short']}"
            disabled = i == n - 1 and not has_result
            clicked = st.button(
                label,
                key=f"v2_goto_{i}",
                type="primary" if i == current else "secondary",
                disabled=disabled,
                width="stretch",
            )
            if clicked and i != current:
                _goto(i)


def _collect() -> Assumptions:
    _commit_widgets()
    data = _data()
    catalog = st.session_state.asset_catalog
    horizon = int(data["max_year"])
    mu_sigma = {
        asset_id: (
            float(data["mu"].get(asset_id, 0.0)),
            float(data["sigma"].get(asset_id, 0.0)),
        )
        for asset_id in return_model_asset_ids(catalog)
    }
    return Assumptions.from_gui_state(
        name=str(st.session_state.assumptions_name or "Untitled"),
        initial_capital=str(data["initial_capital"]),
        contributions=str(data["contributions"]),
        withdrawals=str(data["withdrawals"]),
        cash_buffer=str(data["cash_buffer"]),
        max_year=horizon,
        nb_projections=int(data["nb_projections"]),
        output_dir=str(st.session_state.output_dir),
        mix_preset=str(st.session_state.mix_preset),
        asset_catalog=catalog,
        allocation=dict(data["allocation"]),
        mu_sigma=mu_sigma,
        correlation_values=dict(DEFAULT_RISK_CORRELATION),
        contributions_from_period=1,
        contributions_to_period=horizon,
        withdrawals_from_period=1,
        withdrawals_to_period=horizon,
        rng_seed=int(data["rng_seed"]),
    )


def _render_step_wealth() -> None:
    st.markdown("**Starting wealth**")
    _help(
        "The total value of your assets as of today. "
        "This is the amount we will project forward, year by year. "
        "Include everything you have in cash, stocks, bonds, real estate, and other assets. "
        "If you have a mortgage, or other debt, do not subtract the principal amount outstanding from your total assets. We will deal with debt later in the simulation. "
        "You can type 1M for one million, or 250k for 250,000."
    )
    st.text_input("Starting wealth", key="v2w_initial_capital", label_visibility="collapsed")

    st.markdown("**Cash you keep aside**")
    _help(
        "A rainy-day reserve that is not invested in the mix below. "
        "Yearly withdrawals are taken from here first. Must be less than starting wealth."
    )
    st.text_input("Cash reserve", key="v2w_cash_buffer", label_visibility="collapsed")


def _render_step_flows() -> None:
    st.markdown("**Added each year**")
    _help(
        "New savings put into the portfolio every year (for example from salary). "
        "Use 0k if you will not add money."
    )
    st.text_input("Yearly contributions", key="v2w_contributions", label_visibility="collapsed")

    st.markdown("**Taken out each year**")
    _help(
        "Spending paid from the portfolio every year (for example living costs in retirement). "
        "Use 0k if you will not take money out."
    )
    st.text_input("Yearly withdrawals", key="v2w_withdrawals", label_visibility="collapsed")


def _render_step_mix() -> None:
    catalog = st.session_state.asset_catalog
    required = {"money_market", "bonds", "stocks"}
    investable = [catalog.get(i) for i in investable_asset_ids(catalog)]
    for asset in investable:
        if asset.id not in required:
            continue
        st.markdown(f"**{asset.name}**")
        _help(ASSET_BLURB.get(asset.id, "Share of the invested portfolio."))
        st.number_input(
            f"{asset.name} %",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key=f"v2w_alloc_{asset.id}",
            label_visibility="collapsed",
        )

    with st.expander("Optional investments"):
        for asset in investable:
            if asset.id in required:
                continue
            st.markdown(f"**{asset.name}**")
            _help(ASSET_BLURB.get(asset.id, "Optional part of the mix."))
            st.number_input(
                f"{asset.name} %",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key=f"v2w_alloc_{asset.id}",
                label_visibility="collapsed",
            )

    _commit_widgets()
    total = sum(float(w) for w in _data()["allocation"].values())
    st.caption(f"Total invested mix: **{total:.0f}%** (needs to be 100%).")
    if abs(total - 100.0) > 0.01:
        st.warning("The percentages should add up to 100%.")
        if total > 0 and st.button("Balance to 100%", key="v2_normalize"):
            scaled = {
                k: v / total * 100.0 for k, v in _data()["allocation"].items()
            }
            _data()["allocation"] = scaled
            st.rerun()


def _render_step_markets() -> None:
    catalog = st.session_state.asset_catalog
    st.caption("Suggested values are typical long-run planning figures, not forecasts.")
    for asset_id in investable_asset_ids(catalog):
        asset = catalog.get(asset_id)
        st.markdown(f"**{asset.name}**")
        _help(ASSET_BLURB.get(asset.id, ""))
        c1, c2 = st.columns(2)
        with c1:
            st.number_input(
                "Typical yearly growth (%)",
                min_value=-20.0,
                max_value=80.0,
                step=0.5,
                key=f"v2w_mu_{asset.id}",
            )
        with c2:
            st.number_input(
                "How bumpy the ride is (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.5,
                key=f"v2w_sigma_{asset.id}",
            )


def _render_step_run() -> None:
    st.markdown("**How many years to look ahead**")
    _help("For example 20 years if you want to see two decades of possible paths.")
    st.number_input(
        "Horizon (years)",
        min_value=1,
        max_value=50,
        step=1,
        key="v2w_max_year",
        label_visibility="collapsed",
    )
    st.markdown("**How many possible futures to try**")
    _help(
        "More paths give a smoother picture. 2,000 is a good start. "
        "Above 5,000 can take several minutes."
    )
    st.number_input(
        "Number of projections",
        min_value=10,
        max_value=20000,
        step=10,
        key="v2w_nb_projections",
        label_visibility="collapsed",
    )
    try:
        assumptions = _collect()
        config = assumptions.to_simulation_config()
        validate_allocation(config.risk_mix, config.asset_catalog)
        problems: list[str] = []
    except (ValueError, TypeError, KeyError) as exc:
        problems = [str(exc)]
        config = None
    if problems:
        st.error("Please go back and fix: " + " ".join(problems))
        return
    if st.button("Run projection", type="primary", width="stretch", key="v2_run"):
        assert config is not None
        with st.spinner("Simulating many possible futures…"):
            result = run_simulation(config)
        st.session_state.result = result
        st.session_state.v2_step = len(STEPS) - 1
        st.rerun()


def _render_step_results() -> None:
    result = st.session_state.result
    if result is None:
        st.info("No projection yet. Go back to **Run** and start one.")
        return
    year = int(_data()["max_year"])
    fan = result.nav_fan
    values = fan.values_by_year.get(year, [])
    cols = st.columns(2)
    with cols[0]:
        fig = build_nav_fan_figure(fan)
        if fig is not None:
            st.pyplot(fig)
            plt.close(fig)
    with cols[1]:
        if values:
            hist = build_nav_distribution_figure(values, year)
            st.pyplot(hist)
            plt.close(hist)
    observer = result.nav_observers.get(f"Net Asset Value @ year {year:>2}")
    if observer is not None:
        initial = cv(str(_data()["initial_capital"]))
        m1, m2 = st.columns(2)
        m1.metric(
            "Chance of running out (NAV below 0)",
            f"{rate_below(observer, 0.0):.0f}%",
        )
        m2.metric(
            "Chance of ending above starting wealth",
            f"{success_rate(observer, initial):.0f}%",
        )
        st.markdown(
            f"At year {year}, typical outcome (median) is about "
            f"**{format_compact_amount(observer.quantile(0.50))}**. "
            f"Most paths fall between "
            f"{format_compact_amount(observer.quantile(0.10))} and "
            f"{format_compact_amount(observer.quantile(0.90))}."
        )
    st.caption(f"Seed {int(_data()['rng_seed'])} — same answers if you run again.")


def _render_nav_buttons(step: int) -> None:
    last_setup = len(STEPS) - 2
    back_col, next_col = st.columns(2)
    with back_col:
        if step > 0 and st.button("Back", width="stretch", key="v2_back"):
            _goto(step - 1)
    with next_col:
        if step < last_setup and st.button(
            "Continue", type="primary", width="stretch", key="v2_next"
        ):
            _goto(step + 1)
        if step == last_setup:
            st.caption("Use **Run projection** above when you are ready.")
        if step == len(STEPS) - 1 and st.button(
            "Start over", width="stretch", key="v2_restart"
        ):
            _goto(0)


def main() -> None:
    st.set_page_config(page_title="finproj", layout="centered")
    inject_theme()
    st.markdown(WIZARD_CSS, unsafe_allow_html=True)
    _init()
    _commit_widgets()

    st.markdown('<p class="fp2-kicker">Guided projection</p>', unsafe_allow_html=True)
    st.title("finproj")
    st.caption("One step at a time. You can jump using the timeline.")

    step = int(st.session_state.v2_step)
    step = max(0, min(step, len(STEPS) - 1))
    st.session_state.v2_step = step
    _seed_widgets_for_step(step)

    with st.container(key="v2_timeline"):
        _render_timeline(step)

    spec = STEPS[step]
    with st.container(border=True, key="v2_step_card"):
        st.markdown(f"### Step {step + 1} of {len(STEPS)}  ·  {spec['title']}")
        st.markdown(f'<p class="fp2-intro">{spec["intro"]}</p>', unsafe_allow_html=True)
        renderers = (
            _render_step_wealth,
            _render_step_flows,
            _render_step_mix,
            _render_step_markets,
            _render_step_run,
            _render_step_results,
        )
        renderers[step]()
        st.divider()
        _render_nav_buttons(step)


main()
