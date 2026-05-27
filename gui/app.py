# finproj - Stochastic Financial Projections to optimize asset management
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import copy
import html
import importlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'code'))

from assumptions import DEFAULT_ASSUMPTIONS_DIR, Assumptions  # noqa: E402
from asset_classes import AssetCatalog, default_asset_catalog  # noqa: E402
from inv_proj import cv  # noqa: E402
from theme import inject_theme  # noqa: E402
from formatting import format_compact_amount, render_summary_statistics_table  # noqa: E402
from charts import build_nav_distribution_figure, build_nav_percentile_figure  # noqa: E402
from inv_proj_runner import (  # noqa: E402
    DEFAULT_NEW_ASSET_RISK,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RISK_CORRELATION,
    DEFAULT_RISK_MIX_PRESETS,
    DEFAULT_RISK_PARAM,
    RunResult,
    SimulationConfig,
    investable_asset_ids,
    normalize_correlation_pair,
    return_model_asset_ids,
    success_rate,
    sync_config_with_catalog,
    validate_allocation,
    validate_correlation,
)
import inv_proj_runner  # noqa: E402


def _nav_key(year: int) -> str:
    return f'Net Asset Value @ year {year:>2}'


STANDARD_CHART_YEARS = (1, 5, 10, 15)


def _chart_year_options(max_year: int) -> list[int]:
    years = {year for year in STANDARD_CHART_YEARS if year <= max_year}
    if max_year not in years:
        years.add(max_year)
    return sorted(years)


def _correlation_pairs(catalog: AssetCatalog) -> list[tuple[str, str]]:
    asset_order = return_model_asset_ids(catalog)
    pairs = []
    for i, left in enumerate(asset_order):
        for right in asset_order[i + 1:]:
            pairs.append((left, right))
    return pairs


def _investable_assets(catalog: AssetCatalog) -> list:
    """Investable assets shown in section 2 (excludes Cash / liquidity buffer)."""
    liquidity_id = catalog.liquidity_id()
    return [
        asset for asset in catalog.assets
        if asset.id in investable_asset_ids(catalog) and asset.id != liquidity_id
    ]


def _correlation_from_inputs(values: dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    correlations: dict[tuple[str, str], float] = {}
    for pair, rho in values.items():
        if abs(rho) > 1e-12:
            correlations[pair] = rho
    return correlations


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
        st.session_state.setdefault(f'mu_{asset_id}', float(defaults['mu']))
        st.session_state.setdefault(f'sigma_{asset_id}', float(defaults['sigma']))


def _init_correlation_keys(catalog: AssetCatalog) -> None:
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, return_model_asset_ids(catalog))
        key = f'corr_{canonical[0]}_{canonical[1]}'
        st.session_state.setdefault(key, float(st.session_state.correlation_values.get(canonical, 0.0)))


PORTFOLIO_FIELD_DEFAULTS = {
    'initial_capital': '1M',
    'withdrawals': '40k',
    'cash_buffer': '100k',
    'max_year': 15,
    'nb_projections': 2000,
}

PORTFOLIO_FIELD_HELP = {
    'initial_capital': (
        'Total portfolio value at the start of each simulation path. '
        'The cash buffer is set aside first; the rest is invested per your allocation. '
        'Supports shorthand such as 1M, 40k, or 2.5B.'
    ),
    'withdrawals': (
        'Amount withdrawn from the portfolio every year. '
        'Withdrawals are taken from the cash buffer first; any shortfall is covered by selling bonds. '
        'Supports shorthand such as 40k or 50k.'
    ),
    'cash_buffer': (
        'Target cash reserve held in the liquidity asset (Cash). '
        'Annual withdrawals are drawn from here before other assets are touched. '
        'Must be less than initial capital. Supports shorthand such as 100k or 200k.'
    ),
    'max_year': (
        'Number of years each Monte Carlo path runs. '
        'Summary statistics and charts focus on net asset value at this horizon.'
    ),
    'nb_projections': (
        'Number of independent simulation paths to run. '
        'More paths produce smoother statistics but take longer. '
        'Counts above 5,000 can take several minutes.'
    ),
}

RETURN_ASSUMPTION_HELP = {
    'mu': (
        'Expected annual return for this asset, in percent. '
        'Used as the mean (μ) of the normal return distribution in each simulation year.'
    ),
    'sigma': (
        'Expected annual volatility (standard deviation of returns), in percent. '
        'Must be zero or positive. Higher values produce a wider range of outcomes.'
    ),
}

PORTFOLIO_AMOUNT_FIELDS = (
    ('Initial capital', 'portfolio_edit_initial_capital'),
    ('Annual withdrawals', 'portfolio_edit_withdrawals'),
    ('Cash buffer', 'portfolio_edit_cash_buffer'),
)


def _validate_portfolio_amount_inputs() -> list[str]:
    errors: list[str] = []
    parsed: dict[str, float] = {}

    for label, key in PORTFOLIO_AMOUNT_FIELDS:
        raw = str(st.session_state.get(key, '')).strip()
        if not raw:
            errors.append(f'{label}: enter an amount (e.g. 1M or 40k).')
            continue
        try:
            value = cv(raw)
        except ValueError:
            errors.append(
                f"{label}: could not understand '{raw}' as an amount. "
                'Use a number with optional k, M, or B suffix (e.g. 1M, 40k, 2.5B).'
            )
            continue
        if value < 0:
            errors.append(f'{label}: must be zero or positive.')
            continue
        parsed[label] = value

    capital = parsed.get('Initial capital')
    cash_buffer = parsed.get('Cash buffer')
    if capital is not None and cash_buffer is not None and cash_buffer >= capital:
        errors.append('Cash buffer must be less than initial capital.')

    return errors


def _init_portfolio_fields() -> None:
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = copy.deepcopy(PORTFOLIO_FIELD_DEFAULTS)


def _sync_portfolio_to_edit_widgets() -> None:
    portfolio = st.session_state.portfolio
    st.session_state.portfolio_edit_initial_capital = portfolio['initial_capital']
    st.session_state.portfolio_edit_withdrawals = portfolio['withdrawals']
    st.session_state.portfolio_edit_cash_buffer = portfolio['cash_buffer']
    st.session_state.portfolio_edit_max_year = int(portfolio['max_year'])
    st.session_state.portfolio_edit_nb_projections = int(portfolio['nb_projections'])


def _sync_edit_widgets_to_portfolio() -> None:
    portfolio = st.session_state.portfolio
    portfolio['initial_capital'] = st.session_state.portfolio_edit_initial_capital
    portfolio['withdrawals'] = st.session_state.portfolio_edit_withdrawals
    portfolio['cash_buffer'] = st.session_state.portfolio_edit_cash_buffer
    portfolio['max_year'] = int(st.session_state.portfolio_edit_max_year)
    portfolio['nb_projections'] = int(st.session_state.portfolio_edit_nb_projections)


def _read_portfolio_fields() -> dict:
    if st.session_state.get('portfolio_assumptions_editing'):
        if not _validate_portfolio_amount_inputs():
            _sync_edit_widgets_to_portfolio()
    return st.session_state.portfolio


def _init_session_state() -> None:
    st.session_state.setdefault('asset_catalog', default_asset_catalog())
    st.session_state.setdefault('allocation', copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance']))
    st.session_state.setdefault('mix_preset', 'performance')
    st.session_state.setdefault('result', None)
    _init_portfolio_fields()
    st.session_state.setdefault('output_dir', str(DEFAULT_OUTPUT_DIR))
    st.session_state.setdefault('assumptions_name', 'Untitled')
    st.session_state.setdefault('assumptions_file', '')
    st.session_state.setdefault('assumptions_save_as', 'my_scenario.json')
    st.session_state.setdefault('portfolio_assumptions_editing', False)
    if 'asset_allocation_editing' not in st.session_state:
        st.session_state.asset_allocation_editing = st.session_state.pop('asset_classes_editing', False)
    st.session_state.setdefault('asset_allocation_editing', False)
    st.session_state.setdefault('return_assumptions_editing', False)
    if 'correlation_values' not in st.session_state:
        st.session_state.correlation_values = _default_correlation_values(st.session_state.asset_catalog)
    _init_mu_sigma_keys(st.session_state.asset_catalog)
    _init_correlation_keys(st.session_state.asset_catalog)


def _read_mu_sigma(catalog: AssetCatalog) -> dict[str, tuple[float, float]]:
    if st.session_state.get('return_assumptions_editing'):
        _sync_edit_widgets_to_return_assumptions(catalog)
    mu_sigma: dict[str, tuple[float, float]] = {}
    for asset_id in return_model_asset_ids(catalog):
        mu_sigma[asset_id] = (
            float(st.session_state[f'mu_{asset_id}']),
            float(st.session_state[f'sigma_{asset_id}']),
        )
    return mu_sigma


def _read_correlation_values(catalog: AssetCatalog) -> dict[tuple[str, str], float]:
    if st.session_state.get('return_assumptions_editing'):
        _sync_edit_widgets_to_return_assumptions(catalog)
    asset_order = return_model_asset_ids(catalog)
    values: dict[tuple[str, str], float] = {}
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        key = f'corr_{canonical[0]}_{canonical[1]}'
        values[canonical] = float(st.session_state.get(key, 0.0))
    st.session_state.correlation_values = values
    return values


def _collect_assumptions() -> Assumptions:
    catalog: AssetCatalog = _read_asset_catalog()
    portfolio = _read_portfolio_fields()
    return Assumptions.from_gui_state(
        name=st.session_state.assumptions_name.strip() or 'Untitled',
        initial_capital=portfolio['initial_capital'],
        withdrawals=portfolio['withdrawals'],
        cash_buffer=portfolio['cash_buffer'],
        max_year=int(portfolio['max_year']),
        nb_projections=int(portfolio['nb_projections']),
        output_dir=st.session_state.output_dir,
        mix_preset=st.session_state.mix_preset,
        asset_catalog=catalog,
        allocation=dict(st.session_state.allocation),
        mu_sigma=_read_mu_sigma(catalog),
        correlation_values=_read_correlation_values(catalog),
    )


def _queue_assumptions_load(assumptions: Assumptions, file_path: Path | None = None) -> None:
    st.session_state['_pending_assumptions'] = assumptions.to_dict()
    st.session_state['_pending_assumptions_file'] = str(file_path) if file_path else ''


def _process_pending_assumptions() -> None:
    if '_pending_assumptions' not in st.session_state:
        return
    assumptions = Assumptions.from_dict(st.session_state['_pending_assumptions'])
    file_path = st.session_state.get('_pending_assumptions_file') or ''
    del st.session_state['_pending_assumptions']
    del st.session_state['_pending_assumptions_file']
    _apply_assumptions(assumptions, Path(file_path) if file_path else None)
    st.session_state['_assumptions_load_message'] = f'Loaded "{assumptions.name}".'


def _apply_assumptions(assumptions: Assumptions, file_path: Path | None = None) -> None:
    st.session_state.portfolio = {
        'initial_capital': assumptions.initial_capital,
        'withdrawals': assumptions.withdrawals,
        'cash_buffer': assumptions.cash_buffer,
        'max_year': assumptions.max_year,
        'nb_projections': assumptions.nb_projections,
    }
    st.session_state.output_dir = assumptions.output_dir
    st.session_state.mix_preset = assumptions.mix_preset
    st.session_state.assumptions_name = assumptions.name
    st.session_state.asset_catalog = assumptions.asset_catalog.copy()
    st.session_state.allocation = copy.deepcopy(assumptions.allocation)
    st.session_state.correlation_values = assumptions.correlation_values()
    st.session_state.assumptions_file = str(file_path) if file_path else ''
    st.session_state.result = None
    st.session_state.portfolio_assumptions_editing = False
    st.session_state.asset_allocation_editing = False
    st.session_state.return_assumptions_editing = False

    for asset in assumptions.asset_catalog.assets:
        st.session_state[f'asset_name_{asset.id}'] = asset.name

    for asset_id, weight in assumptions.allocation.items():
        st.session_state[f'alloc_{asset_id}'] = float(weight)

    for asset_id, (mu, sigma) in assumptions.mu_sigma_tuples().items():
        st.session_state[f'mu_{asset_id}'] = float(mu)
        st.session_state[f'sigma_{asset_id}'] = float(sigma)

    asset_order = assumptions.asset_catalog.return_model_ids()
    for key, rho in assumptions.correlations.items():
        left, right = key.split('|', 1)
        canonical = normalize_correlation_pair(left, right, asset_order)
        st.session_state[f'corr_{canonical[0]}_{canonical[1]}'] = float(rho)


def _build_risk_param(catalog: AssetCatalog, mu_sigma: dict[str, tuple[float, float]]) -> dict:
    risk_param = {}
    for asset_id in return_model_asset_ids(catalog):
        defaults = DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0]
        mu, sigma = mu_sigma.get(asset_id, (defaults['mu'], defaults['sigma']))
        risk_param[asset_id] = [{'from_year': 1, 'rv': 'norm', 'mu': mu, 'sigma': sigma}]
    return risk_param


def _build_config(
    catalog: AssetCatalog,
    allocation: dict[str, float],
    mu_sigma: dict[str, tuple[float, float]],
    correlation_values: dict[tuple[str, str], float],
) -> SimulationConfig:
    portfolio = _read_portfolio_fields()
    config = SimulationConfig(
        initial_capital=portfolio['initial_capital'],
        withdrawals=portfolio['withdrawals'],
        cash_buffer=portfolio['cash_buffer'],
        max_year=int(portfolio['max_year']),
        nb_projections=int(portfolio['nb_projections']),
        asset_catalog=catalog.copy(),
        risk_mix=copy.deepcopy(allocation),
        risk_param=_build_risk_param(catalog, mu_sigma),
        risk_correlation=_correlation_from_inputs(correlation_values),
        output_dir=Path(st.session_state.output_dir),
    )
    sync_config_with_catalog(config)
    return config


def _render_assumptions_file_controls() -> None:
    st.header('Assumptions file')
    st.text_input('Scenario name', key='assumptions_name')

    current_file = st.session_state.assumptions_file
    if current_file:
        st.caption(f'Current file: `{current_file}`')
    else:
        st.caption('No file saved yet — use **Save as** for the first save.')

    uploaded = st.file_uploader('Load from JSON file', type=['json'], key='assumptions_uploader')
    if st.button('Load', use_container_width=True):
        if uploaded is None:
            st.warning('Choose a JSON file first.')
        else:
            try:
                assumptions = Assumptions.from_json(uploaded.getvalue().decode('utf-8'))
                _queue_assumptions_load(assumptions)
                st.rerun()
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                st.error(f'Could not load file: {exc}')

    save_col, save_as_col = st.columns(2)
    with save_col:
        if st.button('Save', use_container_width=True):
            try:
                assumptions = _collect_assumptions()
                if st.session_state.assumptions_file:
                    path = Path(st.session_state.assumptions_file)
                else:
                    path = DEFAULT_ASSUMPTIONS_DIR / assumptions.safe_filename()
                    st.session_state.assumptions_file = str(path)
                assumptions.save(path)
                st.success(f'Saved to `{path}`.')
            except (ValueError, OSError) as exc:
                st.error(str(exc))

    with save_as_col:
        st.text_input(
            'Save as filename',
            key='assumptions_save_as',
            label_visibility='collapsed',
            placeholder='my_scenario.json',
        )

    if st.button('Save as', use_container_width=True):
        try:
            assumptions = _collect_assumptions()
            filename = st.session_state.assumptions_save_as.strip() or assumptions.safe_filename()
            if not filename.endswith('.json'):
                filename = f'{filename}.json'
            path = DEFAULT_ASSUMPTIONS_DIR / filename
            assumptions.save(path)
            st.session_state.assumptions_file = str(path)
            st.success(f'Saved to `{path}`.')
        except (ValueError, OSError) as exc:
            st.error(str(exc))

    try:
        download_payload = _collect_assumptions().to_json()
    except ValueError as exc:
        download_payload = None
        st.warning(f'Cannot export assumptions: {exc}')

    if download_payload:
        st.download_button(
            'Download JSON',
            data=download_payload,
            file_name=_collect_assumptions().safe_filename(),
            mime='application/json',
            use_container_width=True,
        )


def _sync_catalog_to_edit_widgets(catalog: AssetCatalog) -> None:
    for asset in _investable_assets(catalog):
        st.session_state[f'asset_name_{asset.id}'] = asset.name
    st.session_state.setdefault('asset_classes_edit_new_name', '')


def _sync_edit_widgets_to_catalog() -> None:
    catalog: AssetCatalog = st.session_state.asset_catalog.copy()
    for asset in _investable_assets(catalog):
        name_key = f'asset_name_{asset.id}'
        if name_key in st.session_state:
            new_name = str(st.session_state[name_key]).strip()
            if new_name and new_name != asset.name:
                catalog.rename(asset.id, new_name)
    st.session_state.asset_catalog = catalog


def _read_asset_catalog() -> AssetCatalog:
    if st.session_state.get('asset_allocation_editing'):
        _sync_edit_widgets_to_catalog()
    return st.session_state.asset_catalog


def _sync_allocation_to_edit_widgets(investable_ids: list[str]) -> None:
    for asset_id in investable_ids:
        st.session_state[f'alloc_{asset_id}'] = float(st.session_state.allocation.get(asset_id, 0.0))


def _apply_mix_preset(catalog: AssetCatalog, mix_preset: str) -> None:
    investable_ids = investable_asset_ids(catalog)
    preset = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS[mix_preset])
    st.session_state.allocation = {
        asset_id: preset.get(asset_id, 0.0)
        for asset_id in investable_ids
    }
    for asset_id, weight in st.session_state.allocation.items():
        st.session_state[f'alloc_{asset_id}'] = float(weight)
    st.session_state.mix_preset = mix_preset


def _show_allocation_total(allocation: dict[str, float]) -> None:
    alloc_total = sum(allocation.values())
    if abs(alloc_total - 100.0) > 0.01:
        st.error(f'Allocation must sum to 100%. Current total: {alloc_total:.1f}%')
    else:
        st.success(f'Allocation total: {alloc_total:.1f}%')


def _sync_return_assumptions_to_edit_widgets(catalog: AssetCatalog) -> None:
    for asset_id in return_model_asset_ids(catalog):
        st.session_state[f'return_edit_mu_{asset_id}'] = float(st.session_state[f'mu_{asset_id}'])
        st.session_state[f'return_edit_sigma_{asset_id}'] = float(st.session_state[f'sigma_{asset_id}'])
    asset_order = return_model_asset_ids(catalog)
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f'return_edit_corr_{canonical[0]}_{canonical[1]}'
        st.session_state[edit_key] = float(st.session_state.correlation_values.get(canonical, 0.0))


def _sync_edit_widgets_to_return_assumptions(catalog: AssetCatalog) -> None:
    for asset_id in return_model_asset_ids(catalog):
        mu_key = f'return_edit_mu_{asset_id}'
        sigma_key = f'return_edit_sigma_{asset_id}'
        if mu_key in st.session_state:
            st.session_state[f'mu_{asset_id}'] = float(st.session_state[mu_key])
        if sigma_key in st.session_state:
            st.session_state[f'sigma_{asset_id}'] = float(st.session_state[sigma_key])

    asset_order = return_model_asset_ids(catalog)
    values: dict[tuple[str, str], float] = {}
    for left, right in _correlation_pairs(catalog):
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f'return_edit_corr_{canonical[0]}_{canonical[1]}'
        rho = float(st.session_state.get(edit_key, 0.0))
        values[canonical] = rho
        st.session_state[f'corr_{canonical[0]}_{canonical[1]}'] = rho
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
            pairs.append(f'{catalog.name(left)}/{catalog.name(right)} {rho:.2f}')
    if not pairs:
        return 'Correlations: none set'
    return 'Correlations: ' + ', '.join(pairs)


def _render_return_assumptions_readonly(
    catalog: AssetCatalog,
    mu_sigma: dict[str, tuple[float, float]],
    correlation_values: dict[tuple[str, str], float],
) -> None:
    return_ids = return_model_asset_ids(catalog)
    with st.container(border=True):
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
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.caption(_format_correlation_summary(catalog, correlation_values))


def _render_return_assumptions_edit_form(
    catalog: AssetCatalog,
) -> tuple[dict[str, tuple[float, float]], dict[tuple[str, str], float]]:
    st.caption('Expected return (mu) and volatility (sigma) in percent.')

    header_cols = st.columns([3, 1.5, 1.5])
    with header_cols[0]:
        st.markdown('**Asset**')

    for asset_id in return_model_asset_ids(catalog):
        cols = st.columns([3, 1.5, 1.5])
        with cols[0]:
            st.markdown(catalog.name(asset_id))
        with cols[1]:
            st.number_input(
                'μ (%)',
                format='%.2f',
                key=f'return_edit_mu_{asset_id}',
                help=RETURN_ASSUMPTION_HELP['mu'],
            )
        with cols[2]:
            st.number_input(
                'σ (%)',
                min_value=0.0,
                format='%.2f',
                key=f'return_edit_sigma_{asset_id}',
                help=RETURN_ASSUMPTION_HELP['sigma'],
            )

    st.subheader('Pairwise correlations')
    asset_order = return_model_asset_ids(catalog)
    if st.button('Reset correlations to defaults', key='return_assumptions_reset_corr'):
        st.session_state.correlation_values = _default_correlation_values(catalog)
        for left, right in _correlation_pairs(catalog):
            canonical = normalize_correlation_pair(left, right, asset_order)
            edit_key = f'return_edit_corr_{canonical[0]}_{canonical[1]}'
            st.session_state[edit_key] = float(st.session_state.correlation_values.get(canonical, 0.0))
        st.rerun()

    corr_cols = st.columns(2)
    for idx, (left, right) in enumerate(_correlation_pairs(catalog)):
        label = f'{catalog.name(left)} / {catalog.name(right)}'
        canonical = normalize_correlation_pair(left, right, asset_order)
        edit_key = f'return_edit_corr_{canonical[0]}_{canonical[1]}'
        st.session_state.setdefault(
            edit_key,
            float(st.session_state.correlation_values.get(canonical, 0.0)),
        )
        with corr_cols[idx % 2]:
            st.number_input(
                label,
                min_value=-1.0,
                max_value=1.0,
                step=0.05,
                format='%.2f',
                key=edit_key,
            )

    _sync_edit_widgets_to_return_assumptions(catalog)
    return _read_mu_sigma(catalog), _read_correlation_values(catalog)


def _render_return_assumptions_section(
    catalog: AssetCatalog,
) -> tuple[dict[str, tuple[float, float]], dict[tuple[str, str], float]]:
    editing = st.session_state.return_assumptions_editing
    return_ids = return_model_asset_ids(catalog)

    with st.container(
        horizontal=True,
        width='content',
        gap='small',
        vertical_alignment='center',
        key='return_assumptions_section_header',
    ):
        st.header('3. Return assumptions')
        if editing:
            if st.button('✓', help='Done editing', key='return_assumptions_done'):
                _sync_edit_widgets_to_return_assumptions(catalog)
                st.session_state.return_assumptions_editing = False
                st.rerun()
        elif st.button('✎', help='Edit return assumptions', key='return_assumptions_edit'):
            _sync_return_assumptions_to_edit_widgets(catalog)
            st.session_state.return_assumptions_editing = True
            st.rerun()

    if editing:
        if return_ids and f'return_edit_mu_{return_ids[0]}' not in st.session_state:
            _sync_return_assumptions_to_edit_widgets(catalog)
        return _render_return_assumptions_edit_form(catalog)

    mu_sigma = _read_mu_sigma(catalog)
    correlation_values = _read_correlation_values(catalog)
    _render_return_assumptions_readonly(catalog, mu_sigma, correlation_values)
    return mu_sigma, correlation_values


def _render_asset_allocation_readonly(catalog: AssetCatalog, allocation: dict[str, float]) -> None:
    assets = _investable_assets(catalog)
    with st.container(border=True):
        summary_cols = st.columns(max(len(assets), 1))
        for idx, asset in enumerate(assets):
            weight = allocation.get(asset.id, 0.0)
            with summary_cols[idx]:
                st.metric(asset.name, f'{weight:.0f}%')


def _render_asset_allocation_edit_form() -> AssetCatalog:

    catalog: AssetCatalog = st.session_state.asset_catalog.copy()

    st.caption(
        'Set weights for investable assets. '
        'Required: Money Market, Bonds, and Stocks. Optional classes can be added or removed.'
    )

    reset_col, preset_col, load_col = st.columns([1.4, 2, 1.2])
    with reset_col:
        if st.button('Reset asset list to defaults'):
            st.session_state.asset_catalog = default_asset_catalog()
            st.session_state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance'])
            st.session_state.correlation_values = _default_correlation_values(st.session_state.asset_catalog)
            _init_mu_sigma_keys(st.session_state.asset_catalog)
            _init_correlation_keys(st.session_state.asset_catalog)
            st.rerun()
    with preset_col:
        mix_preset = st.selectbox(
            'Preset mix',
            options=list(DEFAULT_RISK_MIX_PRESETS.keys()),
            index=list(DEFAULT_RISK_MIX_PRESETS.keys()).index(st.session_state.mix_preset),
        )
    with load_col:
        st.write('')
        if st.button('Load preset weights', key='asset_allocation_load_preset'):
            _apply_mix_preset(catalog, mix_preset)
            st.rerun()

    if mix_preset != st.session_state.mix_preset:
        _apply_mix_preset(catalog, mix_preset)

    header_cols = st.columns([4, 1.5, 0.5])
    with header_cols[0]:
        st.markdown('**Asset**')
    with header_cols[1]:
        st.markdown('**Weight %**')

    allocation: dict[str, float] = {}
    for asset in _investable_assets(catalog):
        cols = st.columns([4, 1.5, 0.5])
        with cols[0]:
            name_key = f'asset_name_{asset.id}'
            st.session_state.setdefault(name_key, asset.name)
            new_name = st.text_input(
                'Asset',
                key=name_key,
                label_visibility='collapsed',
            )
            if new_name.strip() and new_name.strip() != asset.name:
                catalog.rename(asset.id, new_name)
        with cols[1]:
            alloc_key = f'alloc_{asset.id}'
            st.session_state.setdefault(
                alloc_key,
                float(st.session_state.allocation.get(asset.id, 0.0)),
            )
            allocation[asset.id] = st.number_input(
                'Weight %',
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key=alloc_key,
                label_visibility='collapsed',
            )
        with cols[2]:
            if not asset.required:
                if st.button('×', help='Remove asset', key=f'delete_{asset.id}'):
                    try:
                        catalog.remove(asset.id)
                        st.session_state.asset_catalog = catalog
                        st.session_state.allocation.pop(asset.id, None)
                        st.session_state.correlation_values = _default_correlation_values(catalog)
                        _init_mu_sigma_keys(catalog)
                        _init_correlation_keys(catalog)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    add_cols = st.columns([4, 1.5, 0.5])
    with add_cols[0]:
        new_asset_name = st.text_input(
            'New asset name',
            placeholder='e.g. Commodities',
            key='asset_classes_edit_new_name',
        )
    with add_cols[2]:
        st.write('')
        if st.button('Add asset'):
            if not new_asset_name.strip():
                st.error('Enter a name for the new asset.')
            else:
                try:
                    added = catalog.add(new_asset_name)
                    st.session_state.asset_catalog = catalog
                    st.session_state.allocation.setdefault(added.id, 0.0)
                    st.session_state.correlation_values = _default_correlation_values(catalog)
                    _init_mu_sigma_keys(catalog)
                    _init_correlation_keys(catalog)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    st.session_state.asset_catalog = catalog
    st.session_state.allocation = allocation
    _show_allocation_total(allocation)
    return catalog


def _render_asset_allocation_section() -> tuple[AssetCatalog, dict[str, float]]:
    editing = st.session_state.asset_allocation_editing
    catalog: AssetCatalog = st.session_state.asset_catalog
    investable_ids = investable_asset_ids(catalog)

    with st.container(
        horizontal=True,
        width='content',
        gap='small',
        vertical_alignment='center',
        key='asset_allocation_section_header',
    ):
        st.header('2. Investable asset allocation')
        if editing:
            if st.button('✓', help='Done editing', key='asset_allocation_done'):
                _sync_edit_widgets_to_catalog()
                st.session_state.asset_allocation_editing = False
                st.rerun()
        elif st.button('✎', help='Edit investable asset allocation', key='asset_allocation_edit'):
            _sync_catalog_to_edit_widgets(catalog)
            _sync_allocation_to_edit_widgets(investable_ids)
            st.session_state.asset_allocation_editing = True
            st.rerun()

    if editing:
        investable = _investable_assets(catalog)
        if investable and f'asset_name_{investable[0].id}' not in st.session_state:
            _sync_catalog_to_edit_widgets(catalog)
            _sync_allocation_to_edit_widgets(investable_ids)
        catalog = _render_asset_allocation_edit_form()
    else:
        _render_asset_allocation_readonly(catalog, st.session_state.allocation)

    return catalog, dict(st.session_state.allocation)


def _render_summary(result: RunResult, max_year: int) -> None:
    st.subheader('Summary statistics')
    rows = []
    for label, observer in result.nav_observers.items():
        rows.append({
            'Metric': label,
            'Mean': format_compact_amount(observer.mean()),
            'Std Dev': format_compact_amount(observer.std()),
            'P10': format_compact_amount(observer.quantile(0.10)),
            'P50': format_compact_amount(observer.quantile(0.50)),
            'P90': format_compact_amount(observer.quantile(0.90)),
            'Min': format_compact_amount(observer.min()),
            'Max': format_compact_amount(observer.max()),
        })
    st.markdown(render_summary_statistics_table(rows), unsafe_allow_html=True)

    horizon_key = _nav_key(max_year)
    if horizon_key in result.nav_observers:
        initial_capital = cv(st.session_state.portfolio['initial_capital'])
        rate = success_rate(result.nav_observers[horizon_key], threshold=initial_capital)
        st.metric(
            f'Probability final NAV greater than initial capital ({format_compact_amount(initial_capital)}) at year {max_year}',
            f'{rate:.1f}%',
            help=(
                f'Share of simulation paths where net asset value at year {max_year} '
                f'exceeds initial capital ({format_compact_amount(initial_capital)}).'
            ),
        )


def _render_portfolio_assumptions_section() -> None:
    editing = st.session_state.portfolio_assumptions_editing
    portfolio = st.session_state.portfolio

    with st.container(
        horizontal=True,
        width='content',
        gap='small',
        vertical_alignment='center',
        key='portfolio_section_header',
    ):
        st.header('1. Portfolio assumptions')
        if editing:
            if st.button('✓', help='Done editing', key='portfolio_assumptions_done'):
                if _validate_portfolio_amount_inputs():
                    st.rerun()
                _sync_edit_widgets_to_portfolio()
                st.session_state.portfolio_assumptions_editing = False
                st.rerun()
        elif st.button('✎', help='Edit portfolio assumptions', key='portfolio_assumptions_edit'):
            _sync_portfolio_to_edit_widgets()
            st.session_state.portfolio_assumptions_editing = True
            st.rerun()

    if editing:
        if 'portfolio_edit_initial_capital' not in st.session_state:
            _sync_portfolio_to_edit_widgets()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input(
                'Initial capital',
                key='portfolio_edit_initial_capital',
                help=PORTFOLIO_FIELD_HELP['initial_capital'],
            )
            st.text_input(
                'Annual withdrawals',
                key='portfolio_edit_withdrawals',
                help=PORTFOLIO_FIELD_HELP['withdrawals'],
            )
        with col2:
            st.text_input(
                'Cash buffer',
                key='portfolio_edit_cash_buffer',
                help=PORTFOLIO_FIELD_HELP['cash_buffer'],
            )
            st.number_input(
                'Horizon (years)',
                min_value=1,
                max_value=50,
                step=1,
                key='portfolio_edit_max_year',
                help=PORTFOLIO_FIELD_HELP['max_year'],
            )
        with col3:
            st.number_input(
                'Number of projections',
                min_value=10,
                max_value=20000,
                step=10,
                key='portfolio_edit_nb_projections',
                help=PORTFOLIO_FIELD_HELP['nb_projections'],
            )
            if int(st.session_state.portfolio_edit_nb_projections) > 5000:
                st.warning('Large projection counts can take several minutes.')
        for message in _validate_portfolio_amount_inputs():
            st.error(message)
    else:
        with st.container(border=True):
            summary_cols = st.columns(5)
            summary_cols[0].metric(
                'Initial capital',
                portfolio['initial_capital'],
                help=PORTFOLIO_FIELD_HELP['initial_capital'],
            )
            summary_cols[1].metric(
                'Annual withdrawals',
                portfolio['withdrawals'],
                help=PORTFOLIO_FIELD_HELP['withdrawals'],
            )
            summary_cols[2].metric(
                'Cash buffer',
                portfolio['cash_buffer'],
                help=PORTFOLIO_FIELD_HELP['cash_buffer'],
            )
            summary_cols[3].metric(
                'Horizon',
                f"{int(portfolio['max_year'])} yrs",
                help=PORTFOLIO_FIELD_HELP['max_year'],
            )
            summary_cols[4].metric(
                'Projections',
                f"{int(portfolio['nb_projections']):,}",
                help=PORTFOLIO_FIELD_HELP['nb_projections'],
            )


def _render_charts(result: RunResult, chart_year: int) -> None:
    key = _nav_key(chart_year)
    if key not in result.nav_observers:
        st.warning(f'No results available for year {chart_year}.')
        return

    values = result.nav_observers[key].values
    if not values:
        return

    col_hist, col_pct = st.columns(2)
    with col_hist:
        hist_fig = build_nav_distribution_figure(values, chart_year)
        st.pyplot(hist_fig)
        plt.close(hist_fig)
    with col_pct:
        pct_fig = build_nav_percentile_figure(values, chart_year)
        if pct_fig is not None:
            st.pyplot(pct_fig)
            plt.close(pct_fig)


def main() -> None:
    st.set_page_config(page_title='finproj', layout='wide')
    inject_theme()
    _init_session_state()
    _process_pending_assumptions()

    st.title('finproj')
    st.caption('Stochastic financial projections — runs locally on your machine.')

    with st.sidebar:
        if st.session_state.get('_assumptions_load_message'):
            st.success(st.session_state.pop('_assumptions_load_message'))
        _render_assumptions_file_controls()
        st.divider()
        st.header('Output')
        st.text_input('Output directory', key='output_dir')
        st.info(
            'After running, refresh `output/finproj.xlsx` in Excel for deeper analysis '
            '(fan charts, scenario navigator).'
        )
        st.caption('Mac: open the output folder in Finder. Windows: open in File Explorer.')

    _render_portfolio_assumptions_section()

    catalog, allocation = _render_asset_allocation_section()

    mu_sigma, correlation_values = _render_return_assumptions_section(catalog)

    st.header('4. Run and results')
    run_clicked = st.button('Run simulation', type='primary')

    if run_clicked:
        try:
            config = _build_config(catalog, allocation, mu_sigma, correlation_values)
            validate_allocation(config.risk_mix, config.asset_catalog)
            validate_correlation(config.risk_param, config.risk_correlation)

            progress = st.progress(0.0, text='Starting simulation...')
            status = st.empty()

            def progress_callback(current: int, total: int) -> None:
                progress.progress(current / total, text=f'Running projection {current:,} of {total:,}...')

            importlib.reload(inv_proj_runner)
            result = inv_proj_runner.run_simulation(
                config,
                progress_callback=progress_callback,
            )

            progress.progress(1.0, text='Simulation complete.')
            status.success(
                f'Finished {config.nb_projections:,} projections over {config.max_year} years.'
            )
            st.session_state.result = result
            st.session_state.result_max_year = int(_read_portfolio_fields()['max_year'])
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f'Simulation failed: {exc}')

    if st.session_state.result is not None:
        result: RunResult = st.session_state.result
        result_year = st.session_state.get('result_max_year', int(_read_portfolio_fields()['max_year']))

        _render_summary(result, result_year)

        chart_year_options = _chart_year_options(result_year)
        chart_year = st.selectbox(
            'Chart year',
            options=chart_year_options,
            index=chart_year_options.index(result_year)
            if result_year in chart_year_options
            else len(chart_year_options) - 1,
        )
        _render_charts(result, chart_year)

        st.subheader('Export')
        if result.output_csv.exists():
            st.download_button(
                'Download output.csv',
                data=result.output_csv.read_bytes(),
                file_name='output.csv',
                mime='text/csv',
            )
        st.caption(f'CSV written to: {result.output_csv}')
        st.caption(f'Audit log written to: {result.audit_path}')


if __name__ == '__main__':
    main()
