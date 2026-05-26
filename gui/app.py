# finproj - Stochastic Financial Projections to optimize asset management
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import copy
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'code'))

from asset_classes import AssetCatalog, default_asset_catalog  # noqa: E402
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
    run_simulation,
)


def _nav_key(year: int) -> str:
    return f'Net Asset Value @ year {year:>2}'


def _init_session_state() -> None:
    if 'asset_catalog' not in st.session_state:
        st.session_state.asset_catalog = default_asset_catalog()
    if 'allocation' not in st.session_state:
        st.session_state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance'])
    if 'mix_preset' not in st.session_state:
        st.session_state.mix_preset = 'performance'
    if 'result' not in st.session_state:
        st.session_state.result = None
    if 'correlation_values' not in st.session_state:
        st.session_state.correlation_values = _default_correlation_values(st.session_state.asset_catalog)


def _correlation_pairs(catalog: AssetCatalog) -> list[tuple[str, str]]:
    asset_order = return_model_asset_ids(catalog)
    pairs = []
    for i, left in enumerate(asset_order):
        for right in asset_order[i + 1:]:
            pairs.append((left, right))
    return pairs


def _correlation_from_inputs(values: dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    correlations: dict[tuple[str, str], float] = {}
    for pair, rho in values.items():
        if abs(rho) > 1e-12:
            correlations[pair] = rho
    return correlations


def _default_correlation_values(catalog: AssetCatalog) -> dict[tuple[str, str], float]:
    asset_order = return_model_asset_ids(catalog)
    values = {pair: 0.0 for pair in _correlation_pairs(catalog)}
    for pair, rho in DEFAULT_RISK_CORRELATION.items():
        left, right = pair
        canonical = normalize_correlation_pair(left, right, asset_order)
        if canonical in values:
            values[canonical] = rho
    return values


def _build_risk_param(catalog: AssetCatalog, mu_sigma: dict[str, tuple[float, float]]) -> dict:
    risk_param = {}
    for asset_id in return_model_asset_ids(catalog):
        defaults = DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0]
        mu, sigma = mu_sigma.get(asset_id, (defaults['mu'], defaults['sigma']))
        risk_param[asset_id] = [{'from_year': 1, 'rv': 'norm', 'mu': mu, 'sigma': sigma}]
    return risk_param


def _build_config(
    initial_capital: str,
    withdrawals: str,
    cash_buffer: str,
    max_year: int,
    nb_projections: int,
    catalog: AssetCatalog,
    allocation: dict[str, float],
    mu_sigma: dict[str, tuple[float, float]],
    correlation_values: dict[tuple[str, str], float],
    output_dir: Path,
) -> SimulationConfig:
    config = SimulationConfig(
        initial_capital=initial_capital,
        withdrawals=withdrawals,
        cash_buffer=cash_buffer,
        max_year=max_year,
        nb_projections=nb_projections,
        asset_catalog=catalog.copy(),
        risk_mix=copy.deepcopy(allocation),
        risk_param=_build_risk_param(catalog, mu_sigma),
        risk_correlation=_correlation_from_inputs(correlation_values),
        output_dir=output_dir,
    )
    sync_config_with_catalog(config)
    return config


def _render_asset_editor() -> AssetCatalog:
    catalog: AssetCatalog = st.session_state.asset_catalog.copy()

    st.caption(
        'Required assets: Cash (liquidity buffer), Money Market, Bonds, and Stocks. '
        'You can rename them, add optional classes, or remove optional classes.'
    )

    reset_col, _ = st.columns([1, 3])
    with reset_col:
        if st.button('Reset asset list to defaults'):
            st.session_state.asset_catalog = default_asset_catalog()
            st.session_state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance'])
            st.session_state.correlation_values = _default_correlation_values(st.session_state.asset_catalog)
            st.rerun()

    for asset in catalog.assets:
        cols = st.columns([2, 3, 1, 1])
        with cols[0]:
            st.text(asset.id)
        with cols[1]:
            new_name = st.text_input(
                'Name',
                value=asset.name,
                key=f'asset_name_{asset.id}',
                label_visibility='collapsed',
            )
            if new_name.strip() and new_name.strip() != asset.name:
                catalog.rename(asset.id, new_name)
        with cols[2]:
            st.write('Required' if asset.required else 'Optional')
        with cols[3]:
            if not asset.required and st.button('Delete', key=f'delete_{asset.id}'):
                try:
                    catalog.remove(asset.id)
                    st.session_state.asset_catalog = catalog
                    st.session_state.allocation.pop(asset.id, None)
                    st.session_state.correlation_values = _default_correlation_values(catalog)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    add_cols = st.columns([3, 1])
    with add_cols[0]:
        new_asset_name = st.text_input('New asset name', placeholder='e.g. Commodities')
    with add_cols[1]:
        st.write('')
        if st.button('Add asset'):
            if not new_asset_name.strip():
                st.error('Enter a name for the new asset.')
            else:
                try:
                    catalog.add(new_asset_name)
                    st.session_state.asset_catalog = catalog
                    st.session_state.correlation_values = _default_correlation_values(catalog)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    st.session_state.asset_catalog = catalog
    return catalog


def _render_summary(result: RunResult, max_year: int) -> None:
    st.subheader('Summary statistics')
    rows = []
    for label, observer in result.nav_observers.items():
        rows.append({
            'Metric': label,
            'Mean': observer.mean(),
            'Std Dev': observer.std(),
            'P10': observer.quantile(0.10),
            'P50': observer.quantile(0.50),
            'P90': observer.quantile(0.90),
            'Min': observer.min(),
            'Max': observer.max(),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    horizon_key = _nav_key(max_year)
    if horizon_key in result.nav_observers:
        rate = success_rate(result.nav_observers[horizon_key])
        st.metric(
            f'Paths with positive NAV at year {max_year}',
            f'{rate:.1f}%',
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
    observer = result.nav_observers[key]

    with col_hist:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(values, bins=40, color='#4C78A8', edgecolor='white')
        ax.set_title(f'NAV distribution at year {chart_year}')
        ax.set_xlabel('Net asset value')
        ax.set_ylabel('Number of paths')
        ax.ticklabel_format(style='plain', axis='x')
        st.pyplot(fig)
        plt.close(fig)

    with col_pct:
        percentiles = {
            'P10': observer.quantile(0.10),
            'P50': observer.quantile(0.50),
            'P90': observer.quantile(0.90),
        }
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = list(percentiles.keys())
        heights = list(percentiles.values())
        ax.bar(labels, heights, color=['#F58518', '#54A24B', '#B279A2'])
        ax.set_title(f'NAV percentiles at year {chart_year}')
        ax.set_ylabel('Net asset value')
        ax.ticklabel_format(style='plain', axis='y')
        st.pyplot(fig)
        plt.close(fig)


def main() -> None:
    st.set_page_config(page_title='finproj', layout='wide')
    _init_session_state()

    st.title('finproj')
    st.caption('Stochastic financial projections — runs locally on your machine.')

    with st.sidebar:
        st.header('Output')
        output_dir = st.text_input('Output directory', value=str(DEFAULT_OUTPUT_DIR))
        st.info(
            'After running, refresh `output/finproj.xlsx` in Excel for deeper analysis '
            '(fan charts, scenario navigator).'
        )
        st.caption('Mac: open the output folder in Finder. Windows: open in File Explorer.')

    st.header('1. Portfolio assumptions')
    col1, col2, col3 = st.columns(3)
    with col1:
        initial_capital = st.text_input('Initial capital', value='1M', help='Supports shorthand such as 1M or 40k.')
        withdrawals = st.text_input('Annual withdrawals', value='40k')
    with col2:
        cash_buffer = st.text_input('Cash buffer', value='100k')
        max_year = st.number_input('Horizon (years)', min_value=1, max_value=50, value=15, step=1)
    with col3:
        nb_projections = st.number_input('Number of projections', min_value=10, max_value=20000, value=2000, step=10)
        if nb_projections > 5000:
            st.warning('Large projection counts can take several minutes.')

    st.header('2. Investable asset classes')
    catalog = _render_asset_editor()
    investable_ids = investable_asset_ids(catalog)
    return_ids = return_model_asset_ids(catalog)

    st.header('3. Asset allocation')
    preset_col, reset_col = st.columns([3, 1])
    with preset_col:
        mix_preset = st.selectbox(
            'Preset mix',
            options=list(DEFAULT_RISK_MIX_PRESETS.keys()),
            index=list(DEFAULT_RISK_MIX_PRESETS.keys()).index(st.session_state.mix_preset),
        )
    with reset_col:
        st.write('')
        if st.button('Load preset weights'):
            preset = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS[mix_preset])
            st.session_state.allocation = {
                asset_id: preset.get(asset_id, 0.0)
                for asset_id in investable_ids
            }
            st.session_state.mix_preset = mix_preset
            st.rerun()

    if mix_preset != st.session_state.mix_preset:
        preset = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS[mix_preset])
        st.session_state.allocation = {
            asset_id: preset.get(asset_id, 0.0)
            for asset_id in investable_ids
        }
        st.session_state.mix_preset = mix_preset

    alloc_cols = st.columns(max(len(investable_ids), 1))
    allocation: dict[str, float] = {}
    for idx, asset_id in enumerate(investable_ids):
        with alloc_cols[idx]:
            allocation[asset_id] = st.number_input(
                catalog.name(asset_id),
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.allocation.get(asset_id, 0.0)),
                step=1.0,
                key=f'alloc_{asset_id}',
            )
    st.session_state.allocation = allocation

    alloc_total = sum(allocation.values())
    if abs(alloc_total - 100.0) > 0.01:
        st.error(f'Allocation must sum to 100%. Current total: {alloc_total:.1f}%')
    else:
        st.success(f'Allocation total: {alloc_total:.1f}%')

    st.header('4. Return assumptions')
    st.caption('Expected return (mu) and volatility (sigma) in percent.')
    mu_sigma: dict[str, tuple[float, float]] = {}
    return_cols = st.columns(max(len(return_ids), 1))
    for idx, asset_id in enumerate(return_ids):
        defaults = DEFAULT_RISK_PARAM.get(asset_id, [DEFAULT_NEW_ASSET_RISK])[0]
        with return_cols[idx]:
            st.markdown(f'**{catalog.name(asset_id)}**')
            mu = st.number_input(
                'mu (%)',
                value=float(defaults['mu']),
                format='%.2f',
                key=f'mu_{asset_id}',
            )
            sigma = st.number_input(
                'sigma (%)',
                min_value=0.0,
                value=float(defaults['sigma']),
                format='%.2f',
                key=f'sigma_{asset_id}',
            )
            mu_sigma[asset_id] = (mu, sigma)

    with st.expander('Pairwise correlations', expanded=False):
        asset_order = return_model_asset_ids(catalog)
        if st.button('Reset correlations to defaults'):
            st.session_state.correlation_values = _default_correlation_values(catalog)
            st.rerun()

        correlation_values = st.session_state.correlation_values.copy()
        corr_cols = st.columns(2)
        for idx, (left, right) in enumerate(_correlation_pairs(catalog)):
            label = f'{catalog.name(left)} / {catalog.name(right)}'
            canonical = normalize_correlation_pair(left, right, asset_order)
            with corr_cols[idx % 2]:
                correlation_values[canonical] = st.number_input(
                    label,
                    min_value=-1.0,
                    max_value=1.0,
                    value=float(correlation_values.get(canonical, 0.0)),
                    step=0.05,
                    format='%.2f',
                    key=f'corr_{left}_{right}',
                )
        st.session_state.correlation_values = correlation_values

    st.header('5. Run and results')
    run_clicked = st.button('Run simulation', type='primary')

    if run_clicked:
        try:
            config = _build_config(
                initial_capital=initial_capital,
                withdrawals=withdrawals,
                cash_buffer=cash_buffer,
                max_year=int(max_year),
                nb_projections=int(nb_projections),
                catalog=catalog,
                allocation=allocation,
                mu_sigma=mu_sigma,
                correlation_values=st.session_state.correlation_values,
                output_dir=Path(output_dir),
            )
            validate_allocation(config.risk_mix, config.asset_catalog)
            validate_correlation(config.risk_param, config.risk_correlation)

            progress = st.progress(0.0, text='Starting simulation...')
            status = st.empty()

            def progress_callback(current: int, total: int) -> None:
                progress.progress(current / total, text=f'Running projection {current:,} of {total:,}...')

            with st.spinner('Running Monte Carlo simulation...'):
                result = run_simulation(config, progress_callback=progress_callback)

            progress.progress(1.0, text='Simulation complete.')
            status.success(
                f'Finished {config.nb_projections:,} projections over {config.max_year} years.'
            )
            st.session_state.result = result
            st.session_state.result_max_year = int(max_year)
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f'Simulation failed: {exc}')

    if st.session_state.result is not None:
        result: RunResult = st.session_state.result
        result_year = st.session_state.get('result_max_year', int(max_year))

        _render_summary(result, result_year)

        chart_year = st.selectbox(
            'Chart year',
            options=sorted({1, 5, result_year}),
            index=sorted({1, 5, result_year}).index(result_year),
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
