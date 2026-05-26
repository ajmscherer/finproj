# finproj - Stochastic Financial Projections to optimize asset management
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from inv_proj import (
    AuditObserver,
    CSV_Observer,
    Projection,
    Risk,
    StatisticalObserver,
    build_correlation_matrix,
    cholesky_decomposition,
    ps,
    rc,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'output'

DEFAULT_RISK_MIX_PRESETS: Dict[str, Dict[rc, float]] = {
    'safe': {rc.BOND: 80, rc.EQUITY: 20, rc.PMETAL: 1, rc.CRYPTO: 0, rc.REAL_ESTATE: 0},
    'moderate': {rc.BOND: 45, rc.EQUITY: 45, rc.PMETAL: 8, rc.CRYPTO: 2, rc.REAL_ESTATE: 0},
    'performance': {rc.BOND: 30, rc.EQUITY: 40, rc.PMETAL: 5, rc.CRYPTO: 5, rc.REAL_ESTATE: 20},
}

DEFAULT_RISK_PARAM = {
    rc.MONEY_MARKET: [{'from_year': 1, 'rv': 'norm', 'mu': 0.5, 'sigma': 4.0}],
    rc.BOND: [{'from_year': 1, 'rv': 'norm', 'mu': 2.0, 'sigma': 10.0}],
    rc.EQUITY: [{'from_year': 1, 'rv': 'norm', 'mu': 6.5, 'sigma': 20.0}],
    rc.CRYPTO: [{'from_year': 1, 'rv': 'norm', 'mu': 50.0, 'sigma': 100.0}],
    rc.PMETAL: [{'from_year': 1, 'rv': 'norm', 'mu': 1.0, 'sigma': 18.0}],
    rc.REAL_ESTATE: [{'from_year': 1, 'rv': 'norm', 'mu': 3.0, 'sigma': 15.0}],
}

DEFAULT_RISK_CORRELATION: Dict[Tuple[rc, rc], float] = {
    (rc.MONEY_MARKET, rc.BOND): 0.50,
    (rc.EQUITY, rc.BOND): -0.20,
    (rc.EQUITY, rc.REAL_ESTATE): 0.30,
    (rc.BOND, rc.REAL_ESTATE): 0.10,
    (rc.EQUITY, rc.PMETAL): 0.05,
    (rc.EQUITY, rc.CRYPTO): 0.15,
}

ALLOCATION_ASSET_CLASSES = [rc.BOND, rc.EQUITY, rc.PMETAL, rc.CRYPTO, rc.REAL_ESTATE]
CORRELATION_ASSET_CLASSES = list(DEFAULT_RISK_PARAM.keys())


@dataclass
class SimulationConfig:
    initial_capital: str = '1M'
    withdrawals: str = '40k'
    cash_buffer: str = '100k'
    max_year: int = 15
    nb_projections: int = 2000
    risk_mix: Dict[rc, float] = field(default_factory=lambda: copy.deepcopy(DEFAULT_RISK_MIX_PRESETS['performance']))
    risk_param: dict = field(default_factory=lambda: copy.deepcopy(DEFAULT_RISK_PARAM))
    risk_correlation: Dict[Tuple[rc, rc], float] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_RISK_CORRELATION)
    )
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)


@dataclass
class RunResult:
    nav_observers: Dict[str, StatisticalObserver]
    output_csv: Path
    audit_path: Path


def default_config() -> SimulationConfig:
    return SimulationConfig()


def validate_allocation(risk_mix: Dict[rc, float]) -> None:
    total = sum(risk_mix.values())
    if abs(total - 100) > 0.01:
        raise ValueError(f'Asset allocation must sum to 100%, got {total:.1f}%')


def validate_correlation(risk_param: dict, correlations: Dict[Tuple[rc, rc], float]) -> None:
    risk_classes = list(risk_param.keys())
    matrix = build_correlation_matrix(risk_classes, correlations)
    cholesky_decomposition(matrix)


def normalize_correlation_pair(left: rc, right: rc) -> Tuple[rc, rc]:
    if CORRELATION_ASSET_CLASSES.index(left) <= CORRELATION_ASSET_CLASSES.index(right):
        return left, right
    return right, left


def success_rate(observer: StatisticalObserver, threshold: float = 0.0) -> float:
    if not observer.values:
        return float('nan')
    successes = sum(1 for value in observer.values if value > threshold)
    return 100.0 * successes / len(observer.values)


def _define_observers(simulation: Projection, config: SimulationConfig) -> Dict[str, StatisticalObserver]:
    nav: Dict[str, StatisticalObserver] = {}
    nav_years = sorted({1, 5, config.max_year})

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
    validate_allocation(config.risk_mix)
    validate_correlation(config.risk_param, config.risk_correlation)

    config.output_dir.mkdir(exist_ok=True)

    distributions = Risk.buildRisks(config.risk_param, max_year=config.max_year)

    simulation = Projection(
        initial_capital=config.initial_capital,
        withdrawals=config.withdrawals,
        cashBuffer=config.cash_buffer,
        risk_mix=config.risk_mix,
        risk_distrib=distributions,
        nb_years=config.max_year,
        nb_projections=config.nb_projections,
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
