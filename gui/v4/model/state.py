# finproj - GUI v4 tour state (dataclasses, not Pydantic)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Goal = Literal["retire_when", "save_for_income", "heirs", "other"]
Legacy = Literal["use_it_all", "preserve_capital", "favor_heirs", "not_sure"]


@dataclass
class IntroState:
    goal: Goal | None = None
    legacy: Legacy | None = None
    target_income: str | None = None
    years_to_retire: int | None = None
    cash_buffer: str | None = None
    initial_capital: str | None = None


@dataclass
class FlowsState:
    contributions: str | None = None
    withdrawals: str | None = None


@dataclass
class MixState:
    money_market: float | None = None
    bonds: float | None = None
    stocks: float | None = None


@dataclass
class MarketPair:
    mu: float | None = None
    sigma: float | None = None


@dataclass
class MarketsState:
    money_market: MarketPair = field(default_factory=MarketPair)
    bonds: MarketPair = field(default_factory=MarketPair)
    stocks: MarketPair = field(default_factory=MarketPair)


@dataclass
class RunState:
    horizon: int | None = None
    nb_projections: int | None = None
    rng_seed: int | None = None


@dataclass
class TourState:
    intro: IntroState = field(default_factory=IntroState)
    flows: FlowsState = field(default_factory=FlowsState)
    mix: MixState = field(default_factory=MixState)
    markets: MarketsState = field(default_factory=MarketsState)
    run: RunState = field(default_factory=RunState)
