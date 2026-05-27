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
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set


class AssetRole:
    LIQUIDITY = 'liquidity'
    INVESTABLE = 'investable'
    SHORTFALL = 'shortfall'
    REPLENISHMENT = 'replenishment'


REQUIRED_ASSET_IDS = frozenset({'cash', 'money_market', 'bonds', 'stocks'})


@dataclass(frozen=True)
class AssetClass:
    id: str
    name: str
    required: bool = False
    roles: frozenset[str] = frozenset()

    def has_role(self, role: str) -> bool:
        return role in self.roles


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', name.strip().lower())
    slug = slug.strip('_')
    if not slug:
        raise ValueError('Asset name must contain at least one letter or number.')
    if slug[0].isdigit():
        slug = f'asset_{slug}'
    return slug


@dataclass
class AssetCatalog:
    assets: List[AssetClass] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.assets:
            self.assets = default_asset_classes()

    @property
    def ids(self) -> List[str]:
        return [asset.id for asset in self.assets]

    def get(self, asset_id: str) -> AssetClass:
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        raise KeyError(f'Unknown asset id: {asset_id}')

    def name(self, asset_id: str) -> str:
        return self.get(asset_id).name

    def name_map(self) -> Dict[str, str]:
        return {asset.id: asset.name for asset in self.assets}

    def liquidity_id(self) -> str:
        return self._single_role_id(AssetRole.LIQUIDITY, 'liquidity buffer')

    def shortfall_id(self) -> str:
        return self._single_role_id(AssetRole.SHORTFALL, 'withdrawal shortfall source')

    def replenishment_id(self) -> str:
        return self._single_role_id(AssetRole.REPLENISHMENT, 'cash replenishment source')

    def investable_ids(self) -> List[str]:
        return [asset.id for asset in self.assets if asset.has_role(AssetRole.INVESTABLE)]

    def return_model_ids(self) -> List[str]:
        return self.ids[:]

    def required_ids(self) -> Set[str]:
        return {asset.id for asset in self.assets if asset.required}

    def _single_role_id(self, role: str, label: str) -> str:
        matches = [asset.id for asset in self.assets if asset.has_role(role)]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one asset with role {label}, found {len(matches)}.')
        return matches[0]

    def validate(self) -> None:
        present_required = self.required_ids()
        missing = REQUIRED_ASSET_IDS - present_required
        if missing:
            raise ValueError(f'Missing required asset ids: {", ".join(sorted(missing))}')

        for role in (AssetRole.LIQUIDITY, AssetRole.SHORTFALL, AssetRole.REPLENISHMENT):
            self._single_role_id(role, role)

        if not self.investable_ids():
            raise ValueError('At least one investable asset is required.')

        seen_ids: Set[str] = set()
        seen_names: Set[str] = set()
        for asset in self.assets:
            if asset.id in seen_ids:
                raise ValueError(f'Duplicate asset id: {asset.id}')
            normalized_name = asset.name.strip().casefold()
            if normalized_name in seen_names:
                raise ValueError(f'Duplicate asset name: {asset.name}')
            seen_ids.add(asset.id)
            seen_names.add(normalized_name)

    def rename(self, asset_id: str, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError('Asset name cannot be empty.')
        asset = self.get(asset_id)
        index = self.assets.index(asset)
        self.assets[index] = AssetClass(
            id=asset.id,
            name=name,
            required=asset.required,
            roles=asset.roles,
        )

    def add(self, name: str, roles: Optional[Iterable[str]] = None) -> AssetClass:
        name = name.strip()
        if not name:
            raise ValueError('Asset name cannot be empty.')
        base_id = slugify(name)
        asset_id = base_id
        suffix = 2
        existing_ids = set(self.ids)
        while asset_id in existing_ids:
            asset_id = f'{base_id}_{suffix}'
            suffix += 1
        asset = AssetClass(
            id=asset_id,
            name=name,
            required=False,
            roles=frozenset(roles or {AssetRole.INVESTABLE}),
        )
        self.assets.append(asset)
        return asset

    def remove(self, asset_id: str) -> None:
        asset = self.get(asset_id)
        if asset.required or asset.id in REQUIRED_ASSET_IDS:
            raise ValueError(f'Cannot remove required asset: {asset.name}')
        self.assets = [item for item in self.assets if item.id != asset_id]

    def copy(self) -> AssetCatalog:
        return AssetCatalog(assets=[copy.deepcopy(asset) for asset in self.assets])


def default_asset_classes() -> List[AssetClass]:
    return [
        AssetClass('cash', 'Cash', required=True, roles=frozenset({AssetRole.LIQUIDITY})),
        AssetClass('money_market', 'Money Market', required=True, roles=frozenset({AssetRole.INVESTABLE})),
        AssetClass(
            'bonds',
            'Bonds',
            required=True,
            roles=frozenset({AssetRole.INVESTABLE, AssetRole.SHORTFALL, AssetRole.REPLENISHMENT}),
        ),
        AssetClass('stocks', 'Stocks', required=True, roles=frozenset({AssetRole.INVESTABLE})),
        AssetClass('crypto', 'Crypto', roles=frozenset({AssetRole.INVESTABLE})),
        AssetClass('pmetal', 'Precious Metals', roles=frozenset({AssetRole.INVESTABLE})),
        AssetClass('real_estate', 'Real Estate', roles=frozenset({AssetRole.INVESTABLE})),
    ]


def default_asset_catalog() -> AssetCatalog:
    catalog = AssetCatalog()
    catalog.validate()
    return catalog
