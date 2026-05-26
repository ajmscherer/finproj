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

from inv_proj import rc  # noqa: E402
from inv_proj_runner import (  # noqa: E402
    ALLOCATION_ASSET_CLASSES,
    CORRELATION_ASSET_CLASSES,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RISK_CORRELATION,
    DEFAULT_RISK_MIX_PRESETS,
    DEFAULT_RISK_PARAM,
    RunResult,
    SimulationConfig,
    normalize_correlation_pair,
    success_rate,
    validate_allocation,
    validate_correlation,
    run_simulation,
)


def _asset_label(asset_class: rc) -> str:
    return asset_class.getDescription()


def _nav_key(year: int) -> str:
    return f'Net Asset Value @ year {year:>2}'


def _init_session_state() -> None:
    defaults = {
        'allocation': copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance']),
        'mix_preset': 'performance',
        'result': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _correlation_pairs() -> list[tuple[rc, rc]]:
    pairs = []
    classes = CORRELATION_ASSET_CLASSES
    for i, left in enumerate(classes):
        for right in classes[i + 1:]:
            pairs.append((left, right))
    return pairs


def _correlation_from_inputs(values: dict[tuple[rc, rc], float]) -> dict[tuple[rc, rc], float]:
    correlations: dict[tuple[rc, rc], float] = {}
    for pair, rho in values.items():
        if abs(rho) > 1e-12:
            correlations[pair] = rho
    return correlations


def _default_correlation_values() -> dict[tuple[rc, rc], float]:
    values = {pair: 0.0 for pair in _correlation_pairs()}
    for pair, rho in DEFAULT_RISK_CORRELATION.items():
        left, right = pair
        canonical = normalize_correlation_pair(left, right)
        if canonical in values:
            values[canonical] = rho
    return values


def _build_risk_param(mu_sigma: dict[rc, tuple[float, float]]) -> dict:
    risk_param = copy.deepcopy(DEFAULT_RISK_PARAM)
    for asset_class, (mu, sigma) in mu_sigma.items():
        risk_param[asset_class] = [{'from_year': 1, 'rv': 'norm', 'mu': mu, 'sigma': sigma}]
    return risk_param


def _build_config(
    initial_capital: str,
    withdrawals: str,
    cash_buffer: str,
    max_year: int,
    nb_projections: int,
    allocation: dict[rc, float],
    mu_sigma: dict[rc, tuple[float, float]],
    correlation_values: dict[tuple[rc, rc], float],
    output_dir: Path,
) -> SimulationConfig:
    return SimulationConfig(
        initial_capital=initial_capital,
        withdrawals=withdrawals,
        cash_buffer=cash_buffer,
        max_year=max_year,
        nb_projections=nb_projections,
        risk_mix=copy.deepcopy(allocation),
        risk_param=_build_risk_param(mu_sigma),
        risk_correlation=_correlation_from_inputs(correlation_values),
        output_dir=output_dir,
    )


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

    st.header('2. Asset allocation')
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
            st.session_state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS[mix_preset])
            st.session_state.mix_preset = mix_preset
            st.rerun()

    if mix_preset != st.session_state.mix_preset:
        st.session_state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS[mix_preset])
        st.session_state.mix_preset = mix_preset

    alloc_cols = st.columns(len(ALLOCATION_ASSET_CLASSES))
    allocation: dict[rc, float] = {}
    for idx, asset_class in enumerate(ALLOCATION_ASSET_CLASSES):
        with alloc_cols[idx]:
            allocation[asset_class] = st.number_input(
                _asset_label(asset_class),
                min_value=0.0,
                max_value=100.0,
                value=float(st.session_state.allocation.get(asset_class, 0.0)),
                step=1.0,
                key=f'alloc_{asset_class.name}',
            )
    st.session_state.allocation = allocation

    alloc_total = sum(allocation.values())
    if abs(alloc_total - 100.0) > 0.01:
        st.error(f'Allocation must sum to 100%. Current total: {alloc_total:.1f}%')
    else:
        st.success(f'Allocation total: {alloc_total:.1f}%')

    st.header('3. Return assumptions')
    st.caption('Expected return (mu) and volatility (sigma) in percent.')
    mu_sigma: dict[rc, tuple[float, float]] = {}
    return_cols = st.columns(len(CORRELATION_ASSET_CLASSES))
    for idx, asset_class in enumerate(CORRELATION_ASSET_CLASSES):
        defaults = DEFAULT_RISK_PARAM[asset_class][0]
        with return_cols[idx]:
            st.markdown(f'**{_asset_label(asset_class)}**')
            mu = st.number_input(
                'mu (%)',
                value=float(defaults['mu']),
                format='%.2f',
                key=f'mu_{asset_class.name}',
            )
            sigma = st.number_input(
                'sigma (%)',
                min_value=0.0,
                value=float(defaults['sigma']),
                format='%.2f',
                key=f'sigma_{asset_class.name}',
            )
            mu_sigma[asset_class] = (mu, sigma)

    with st.expander('Pairwise correlations', expanded=False):
        if st.button('Reset correlations to defaults'):
            st.session_state.correlation_values = _default_correlation_values()
            st.rerun()

        if 'correlation_values' not in st.session_state:
            st.session_state.correlation_values = _default_correlation_values()

        correlation_values = st.session_state.correlation_values.copy()
        corr_cols = st.columns(2)
        for idx, (left, right) in enumerate(_correlation_pairs()):
            label = f'{_asset_label(left)} / {_asset_label(right)}'
            with corr_cols[idx % 2]:
                correlation_values[(left, right)] = st.number_input(
                    label,
                    min_value=-1.0,
                    max_value=1.0,
                    value=float(correlation_values.get((left, right), 0.0)),
                    step=0.05,
                    format='%.2f',
                    key=f'corr_{left.name}_{right.name}',
                )
        st.session_state.correlation_values = correlation_values

    st.header('4. Run and results')
    run_clicked = st.button('Run simulation', type='primary')

    if run_clicked:
        try:
            config = _build_config(
                initial_capital=initial_capital,
                withdrawals=withdrawals,
                cash_buffer=cash_buffer,
                max_year=int(max_year),
                nb_projections=int(nb_projections),
                allocation=allocation,
                mu_sigma=mu_sigma,
                correlation_values=st.session_state.correlation_values,
                output_dir=Path(output_dir),
            )
            validate_allocation(config.risk_mix)
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
