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
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from asset_classes import AssetCatalog, AssetClass, default_asset_catalog
from inv_proj_runner import (
    DEFAULT_OUTPUT_DIR,
    SimulationConfig,
    normalize_correlation_pair,
    sync_config_with_catalog,
)

ASSUMPTIONS_FORMAT_VERSION = 1
DEFAULT_ASSUMPTIONS_DIR = Path(__file__).resolve().parent.parent / 'assumptions'


def catalog_to_dict(catalog: AssetCatalog) -> List[dict]:
    return [
        {
            'id': asset.id,
            'name': asset.name,
            'required': asset.required,
            'roles': sorted(asset.roles),
        }
        for asset in catalog.assets
    ]


def catalog_from_dict(items: List[dict]) -> AssetCatalog:
    assets = [
        AssetClass(
            id=item['id'],
            name=item['name'],
            required=bool(item.get('required', False)),
            roles=frozenset(item.get('roles', [])),
        )
        for item in items
    ]
    catalog = AssetCatalog(assets=assets)
    catalog.validate()
    return catalog


def _correlation_key(left: str, right: str) -> str:
    return f'{left}|{right}'


def _correlation_from_key(key: str) -> Tuple[str, str]:
    left, right = key.split('|', 1)
    return left, right


@dataclass
class Assumptions:
    name: str = 'Untitled'
    initial_capital: str = '1M'
    contributions: str = '40k'  
    withdrawals: str = '10k'
    cash_buffer: str = '100k'
    max_year: int = 15
    nb_projections: int = 2000
    output_dir: str = field(default_factory=lambda: str(DEFAULT_OUTPUT_DIR))
    mix_preset: str = 'performance'
    asset_catalog: AssetCatalog = field(default_factory=default_asset_catalog)
    allocation: Dict[str, float] = field(default_factory=dict)
    mu_sigma: Dict[str, Dict[str, float]] = field(default_factory=dict)
    correlations: Dict[str, float] = field(default_factory=dict)
    format_version: int = ASSUMPTIONS_FORMAT_VERSION

    def __post_init__(self) -> None:
        if not self.allocation:
            self.allocation = {}
        if not self.mu_sigma:
            self.mu_sigma = {}
        if not self.correlations:
            self.correlations = {}

    @classmethod
    def from_gui_state(
        cls,
        *,
        name: str,
        initial_capital: str,   
        contributions: str,
        withdrawals: str,
        cash_buffer: str,
        max_year: int,
        nb_projections: int,
        output_dir: str,
        mix_preset: str,
        asset_catalog: AssetCatalog,
        allocation: Dict[str, float],
        mu_sigma: Dict[str, Tuple[float, float]],
        correlation_values: Dict[Tuple[str, str], float],
    ) -> Assumptions:
        asset_order = asset_catalog.return_model_ids()
        correlations = {}
        for (left, right), rho in correlation_values.items():
            canonical = normalize_correlation_pair(left, right, asset_order)
            correlations[_correlation_key(*canonical)] = rho

        return cls(
            name=name,
            initial_capital=initial_capital,
            contributions=contributions,
            withdrawals=withdrawals,
            cash_buffer=cash_buffer,
            max_year=int(max_year),
            nb_projections=int(nb_projections),
            output_dir=output_dir,
            mix_preset=mix_preset,
            asset_catalog=asset_catalog.copy(),
            allocation=copy.deepcopy(allocation),
            mu_sigma={
                asset_id: {'mu': mu, 'sigma': sigma}
                for asset_id, (mu, sigma) in mu_sigma.items()
            },
            correlations=correlations,
        )

    def correlation_values(self) -> Dict[Tuple[str, str], float]:
        asset_order = self.asset_catalog.return_model_ids()
        values: Dict[Tuple[str, str], float] = {}
        for key, rho in self.correlations.items():
            left, right = _correlation_from_key(key)
            canonical = normalize_correlation_pair(left, right, asset_order)
            values[canonical] = rho
        return values

    def mu_sigma_tuples(self) -> Dict[str, Tuple[float, float]]:
        return {
            asset_id: (params['mu'], params['sigma'])
            for asset_id, params in self.mu_sigma.items()
        }

    def to_simulation_config(self) -> SimulationConfig:
        risk_param = {
            asset_id: [{
                'from_year': 1,
                'rv': 'norm',
                'mu': params['mu'],
                'sigma': params['sigma'],
            }]
            for asset_id, params in self.mu_sigma.items()
        }
        config = SimulationConfig(
            initial_capital=self.initial_capital,
            contributions=self.contributions,
            withdrawals=self.withdrawals,
            cash_buffer=self.cash_buffer,
            max_year=self.max_year,
            nb_projections=self.nb_projections,
            asset_catalog=self.asset_catalog.copy(),
            risk_mix=copy.deepcopy(self.allocation),
            risk_param=risk_param,
            risk_correlation=self.correlation_values(),
            output_dir=Path(self.output_dir),
        )
        sync_config_with_catalog(config)
        return config

    def to_dict(self) -> dict:
        return {
            'format_version': self.format_version,
            'name': self.name,
            'initial_capital': self.initial_capital,
            'contributions': self.contributions,
            'withdrawals': self.withdrawals,
            'cash_buffer': self.cash_buffer,
            'max_year': self.max_year,
            'nb_projections': self.nb_projections,
            'output_dir': self.output_dir,
            'mix_preset': self.mix_preset,
            'asset_catalog': catalog_to_dict(self.asset_catalog),
            'allocation': copy.deepcopy(self.allocation),
            'mu_sigma': copy.deepcopy(self.mu_sigma),
            'correlations': copy.deepcopy(self.correlations),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Assumptions:
        version = data.get('format_version', 1)
        if version != ASSUMPTIONS_FORMAT_VERSION:
            raise ValueError(
                f'Unsupported assumptions format version: {version} '
                f'(expected {ASSUMPTIONS_FORMAT_VERSION}).'
            )

        assumptions = cls(
            format_version=version,
            name=data.get('name', 'Untitled'),
            initial_capital=data['initial_capital'],
            contributions=data['contributions'],
            withdrawals=data['withdrawals'],
            cash_buffer=data['cash_buffer'],
            max_year=int(data['max_year']),
            nb_projections=int(data['nb_projections']),
            output_dir=data.get('output_dir', str(DEFAULT_OUTPUT_DIR)),
            mix_preset=data.get('mix_preset', 'performance'),
            asset_catalog=catalog_from_dict(data['asset_catalog']),
            allocation={k: float(v) for k, v in data['allocation'].items()},
            mu_sigma={
                asset_id: {'mu': float(params['mu']), 'sigma': float(params['sigma'])}
                for asset_id, params in data['mu_sigma'].items()
            },
            correlations={k: float(v) for k, v in data.get('correlations', {}).items()},
        )
        assumptions.asset_catalog.validate()
        return assumptions

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> Assumptions:
        return cls.from_dict(json.loads(text))

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding='utf-8')

    @classmethod
    def load(cls, path: Path) -> Assumptions:
        return cls.from_json(Path(path).read_text(encoding='utf-8'))

    def safe_filename(self) -> str:
        stem = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in self.name.strip())
        stem = stem.strip('_') or 'assumptions'
        return f'{stem}.json'
