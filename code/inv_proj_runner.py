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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from asset_classes import AssetCatalog, default_asset_catalog
from inv_proj import (
    AuditObserver,
    CSV_Observer,
    Projection,
    Risk,
    StatisticalObserver,
    build_correlation_matrix,
    cholesky_decomposition,
    ps,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'output'

DEFAULT_RISK_MIX_PRESETS: Dict[str, Dict[str, float]] = {
    'safe': {'bonds': 80, 'stocks': 20, 'pmetal': 1, 'crypto': 0, 'real_estate': 0},
    'moderate': {'bonds': 45, 'stocks': 45, 'pmetal': 8, 'crypto': 2, 'real_estate': 0},
    'performance': {'bonds': 30, 'stocks': 40, 'pmetal': 5, 'crypto': 5, 'real_estate': 20},
}

DEFAULT_RISK_PARAM = {
    'cash': [{'from_year': 1, 'rv': 'norm', 'mu': 0.0, 'sigma': 0.0}],
    'money_market': [{'from_year': 1, 'rv': 'norm', 'mu': 0.5, 'sigma': 4.0}],
    'bonds': [{'from_year': 1, 'rv': 'norm', 'mu': 2.0, 'sigma': 10.0}],
    'stocks': [{'from_year': 1, 'rv': 'norm', 'mu': 6.5, 'sigma': 20.0}],
    'crypto': [{'from_year': 1, 'rv': 'norm', 'mu': 50.0, 'sigma': 100.0}],
    'pmetal': [{'from_year': 1, 'rv': 'norm', 'mu': 1.0, 'sigma': 18.0}],
    'real_estate': [{'from_year': 1, 'rv': 'norm', 'mu': 3.0, 'sigma': 15.0}],
}

DEFAULT_RISK_CORRELATION: Dict[Tuple[str, str], float] = {
    ('money_market', 'bonds'): 0.50,
    ('stocks', 'bonds'): -0.20,
    ('stocks', 'real_estate'): 0.30,
    ('bonds', 'real_estate'): 0.10,
    ('stocks', 'pmetal'): 0.05,
    ('stocks', 'crypto'): 0.15,
}

DEFAULT_NEW_ASSET_RISK = {'from_year': 1, 'rv': 'norm', 'mu': 5.0, 'sigma': 15.0}


@dataclass
class SimulationConfig:
    initial_capital: str = '1M'
    withdrawals: str = '40k'
    cash_buffer: str = '100k'
    max_year: int = 15
    nb_projections: int = 2000
    asset_catalog: AssetCatalog = field(default_factory=default_asset_catalog)
    risk_mix: Dict[str, float] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance'])
    )
    risk_param: dict = field(default_factory=lambda: copy.deepcopy(DEFAULT_RISK_PARAM))
    risk_correlation: Dict[Tuple[str, str], float] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_RISK_CORRELATION)
    )
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)


@dataclass
class RunResult:
    nav_observers: Dict[str, StatisticalObserver]
    output_csv: Path
    audit_path: Path


def default_config() -> SimulationConfig:
    config = SimulationConfig()
    sync_config_with_catalog(config)
    return config


def investable_asset_ids(catalog: AssetCatalog) -> List[str]:
    return catalog.investable_ids()


def return_model_asset_ids(catalog: AssetCatalog) -> List[str]:
    return catalog.return_model_ids()


def normalize_correlation_pair(left: str, right: str, asset_order: List[str]) -> Tuple[str, str]:
    if asset_order.index(left) <= asset_order.index(right):
        return left, right
    return right, left


def sync_config_with_catalog(config: SimulationConfig) -> None:
    catalog = config.asset_catalog
    catalog.validate()

    valid_investable = set(catalog.investable_ids())
    config.risk_mix = {
        asset_id: weight
        for asset_id, weight in config.risk_mix.items()
        if asset_id in valid_investable
    }

    for asset_id in catalog.return_model_ids():
        if asset_id not in config.risk_param:
            config.risk_param[asset_id] = [copy.deepcopy(DEFAULT_NEW_ASSET_RISK)]

    for asset_id in list(config.risk_param.keys()):
        if asset_id not in catalog.ids:
            del config.risk_param[asset_id]

    asset_order = catalog.return_model_ids()
    valid_pairs = {
        normalize_correlation_pair(left, right, asset_order)
        for i, left in enumerate(asset_order)
        for right in asset_order[i + 1:]
    }
    config.risk_correlation = {
        normalize_correlation_pair(left, right, asset_order): rho
        for (left, right), rho in config.risk_correlation.items()
        if left in catalog.ids and right in catalog.ids
        and normalize_correlation_pair(left, right, asset_order) in valid_pairs
    }


def validate_allocation(risk_mix: Dict[str, float], catalog: AssetCatalog) -> None:
    investable = set(catalog.investable_ids())
    unknown = set(risk_mix.keys()) - investable
    if unknown:
        raise ValueError(f'Allocation includes unknown or non-investable assets: {", ".join(sorted(unknown))}')
    total = sum(risk_mix.values())
    if abs(total - 100) > 0.01:
        raise ValueError(f'Asset allocation must sum to 100%, got {total:.1f}%')


def validate_correlation(risk_param: dict, correlations: Dict[Tuple[str, str], float]) -> None:
    risk_classes = list(risk_param.keys())
    matrix = build_correlation_matrix(risk_classes, correlations)
    cholesky_decomposition(matrix)


def success_rate(observer: StatisticalObserver, threshold: float = 0.0) -> float:
    if not observer.values:
        return float('nan')
    successes = sum(1 for value in observer.values if value > threshold)
    return 100.0 * successes / len(observer.values)


def rate_below(observer: StatisticalObserver, threshold: float = 0.0) -> float:
    if not observer.values:
        return float('nan')
    matches = sum(1 for value in observer.values if value < threshold)
    return 100.0 * matches / len(observer.values)


STANDARD_CHART_YEARS = (1, 5, 10, 15)


def nav_observer_years(max_year: int) -> list[int]:
    years = {year for year in STANDARD_CHART_YEARS if year <= max_year}
    if max_year not in years:
        years.add(max_year)
    return sorted(years)


def _define_observers(simulation: Projection, config: SimulationConfig) -> Dict[str, StatisticalObserver]:
    nav: Dict[str, StatisticalObserver] = {}
    nav_years = nav_observer_years(config.max_year)

    for year in nav_years:
        nav_observer = StatisticalObserver(
            quantity=lambda projection, **param: projection.ptf_eop.total_value(),
            condition=lambda projection, step, y=year, **params: (projection.period == y) & (step == ps.EOP),
        )
        nav[f'Net Asset Value @ year {year:>2}'] = nav_observer
        simulation.registerObserver(nav_observer)

    audit_path = config.output_dir / 'audit.txt'
    audit_observer = AuditObserver(out=open(audit_path, mode='w'))
    simulation.registerObserver(audit_observer)

    csv_observer = CSV_Observer(str(config.output_dir / 'output.csv'))
    simulation.registerObserver(csv_observer)

    return nav


def run_simulation(
    config: SimulationConfig,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> RunResult:
    sync_config_with_catalog(config)
    config.asset_catalog.validate()
    validate_allocation(config.risk_mix, config.asset_catalog)
    validate_correlation(config.risk_param, config.risk_correlation)

    config.output_dir.mkdir(exist_ok=True)

    distributions = Risk.buildRisks(
        config.risk_param,
        max_year=config.max_year,
        asset_names=config.asset_catalog.name_map(),
    )

    simulation = Projection(
        initial_capital=config.initial_capital,
        withdrawals=config.withdrawals,
        cashBuffer=config.cash_buffer,
        risk_mix=config.risk_mix,
        risk_distrib=distributions,
        nb_years=config.max_year,
        nb_projections=config.nb_projections,
        asset_catalog=config.asset_catalog,
        correlations=config.risk_correlation,
    )

    nav = _define_observers(simulation, config)

    for i in range(config.nb_projections):
        simulation.run(i + 1)
        if progress_callback is not None:
            progress_callback(i + 1, config.nb_projections)

    return RunResult(
        nav_observers=nav,
        output_csv=config.output_dir / 'output.csv',
        audit_path=config.output_dir / 'audit.txt',
    )
