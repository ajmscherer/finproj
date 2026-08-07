# finproj - adapter between Viva cash-flow models and finproj projections
# Copyright (C) 2025-2026 Alex Scherer
#
# Viva (https://github.com/ajmscherer/viva) is an optional dependency installed
# via requirements-gui.txt. Deterministic flows are MIT-licensed; probabilistic
# features require a Viva Pro license after the 30-day evaluation period.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

try:
    import viva

    HAS_VIVA = True
except ImportError:
    HAS_VIVA = False


@dataclass(frozen=True)
class FlowStructure:
    flows: list[float]
    audit: dict[str, list[float]]
    start_year: int
    horizon_years: int
    seed: int


class FlowEngine:
    def __init__(self, start_year: int, horizon_years: int):
        self.start_year = start_year
        self.horizon_years = horizon_years

    @staticmethod
    def build(source: str, start_year: int, horizon_years: int) -> FlowEngine:
        raise NotImplementedError("Not implemented")

    def draw_flows(self, seed: int) -> FlowStructure:
        raise NotImplementedError("Not implemented")


class VivaFlowEngine(FlowEngine):
    def __init__(
        self, viva_engine: viva.FlowEngine, start_year: int, horizon_years: int
    ):
        super().__init__(start_year, horizon_years)
        self.viva_engine = viva_engine

    @staticmethod
    def build(source: str, start_year: int, horizon_years: int) -> FlowEngine:
        if not HAS_VIVA:
            raise ImportError(
                "viva is not installed. Install GUI dependencies with "
                "pip install -r requirements-gui.txt"
            )
        from viva import generateFlowEngine

        engine = generateFlowEngine(
            source, start_year=start_year, horizon_years=horizon_years
        )
        result = VivaFlowEngine(engine, start_year, horizon_years)
        return result

    def draw_flows(self, seed: int) -> FlowStructure:

        vflows = self.viva_engine.drawFlows(seed=seed)

        amoount_key = "amount"
        date_key = "date"
        name_key = "name"
        currency_key = "currency"
        currency = {flow[currency_key] for flow in vflows}
        if len(currency) > 1:
            raise ValueError("Multiple currencies are not supported")

        flows = []
        for year in range(self.horizon_years):
            year_flows = [
                flow[amoount_key]
                for flow in vflows
                if flow[date_key].year == self.start_year + year
            ]
            flows.append(sum(year_flows))

        audit = {}
        for name in {flow[name_key] for flow in vflows}:
            audit[name] = []
            for year in range(self.horizon_years):
                year_flows = [
                    flow[amoount_key]
                    for flow in vflows
                    if flow[date_key].year == self.start_year + year
                    and flow[name_key] == name
                ]
                audit[name].append(sum(year_flows))

        flow_structure = FlowStructure(
            flows=flows,
            audit=audit,
            start_year=self.start_year,
            horizon_years=self.horizon_years,
            seed=seed,
        )

        return flow_structure


def default_viva_start_year() -> int:
    return datetime.now().astimezone().year
