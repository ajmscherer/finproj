# finproj - a zero sigma is exactly mu, in both engines
# Copyright (C) 2025-2026 Alex Scherer

"""Sigma 0 stores a return of exactly mu on every path and year.

The standard normal is still drawn, so a volatile peer keeps moving.
Rebalancing may still resize the dollar balance. This file checks the
stored return, not the year-end holding.
"""

from __future__ import annotations

import copy
import csv
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from inv_proj import CorrelatedReturns, Norm
from inv_proj_runner import default_config, run_simulation_python
from rust_engine import run_simulation_rust, rust_engine_available


HORIZON = 5
PATHS = 12
STOCKS_MU = 8.4
METAL_MU = -3.25


class _Fixed:
    def __init__(self, mu: float, sigma: float) -> None:
        self.distribution = {1: Norm(mu, sigma)}


def constant_config(tmp: str):
    config = default_config()
    config.max_year = HORIZON
    config.nb_projections = PATHS
    config.rng_seed = 11
    config.output_dir = Path(tmp)
    config.risk_param["stocks"][0]["mu"] = STOCKS_MU
    config.risk_param["stocks"][0]["sigma"] = 0.0
    config.risk_param["pmetal"][0]["mu"] = METAL_MU
    config.risk_param["pmetal"][0]["sigma"] = 0.0
    return config


def load_returns(path: Path) -> dict[str, list[float]]:
    series: dict[str, list[float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["variable"] != "returns":
                continue
            series.setdefault(row["risk"], []).append(float(row["value"]))
    return series


def returns_by_year(path: Path, name: str) -> dict[int, list[float]]:
    by_year: dict[int, list[float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["variable"] == "returns" and row["risk"] == name:
                by_year.setdefault(int(row["period"]), []).append(float(row["value"]))
    return by_year


def assert_constant(test: unittest.TestCase, values: list[float], mu_percent: float, label: str) -> None:
    expected = mu_percent / 100.0
    test.assertGreater(len(values), 0, msg=label)
    for index, value in enumerate(values):
        test.assertEqual(value, expected, msg=f"{label} sample {index}: {value} vs {expected}")


class ZeroSigmaDrawTest(unittest.TestCase):
    def test_draw_returns_mu_and_still_moves_the_peer(self) -> None:
        risks = {
            "stocks": _Fixed(STOCKS_MU, 0.0),
            "bonds": _Fixed(2.0, 10.0),
        }
        draws = CorrelatedReturns(
            risks,
            {("stocks", "bonds"): 0.85},
            ["stocks", "bonds"],
            rng=random.Random(3),
        )
        stocks = []
        bonds = []
        for _ in range(30):
            sample = draws.draw(1)
            stocks.append(sample["stocks"])
            bonds.append(sample["bonds"])
        self.assertTrue(all(value == STOCKS_MU for value in stocks))
        self.assertGreater(len(set(bonds)), 1)

    def test_norm_zero_sigma_is_mu_and_consumes_the_variate(self) -> None:
        used = random.Random(1)
        control = random.Random(1)
        norm = Norm(STOCKS_MU, 0.0)
        norm.rn = used
        self.assertEqual(norm.draw(), STOCKS_MU)
        control.gauss(STOCKS_MU, 0.0)
        self.assertEqual(used.gauss(0, 1), control.gauss(0, 1))


class ZeroSigmaEngineTest(unittest.TestCase):
    def test_python_stores_exactly_mu_while_bonds_disperse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_simulation_python(constant_config(tmp))
            series = load_returns(Path(tmp) / "output.csv")
        catalog = default_config().asset_catalog
        assert_constant(self, series[catalog.name("stocks")], STOCKS_MU, "stocks")
        assert_constant(self, series[catalog.name("pmetal")], METAL_MU, "precious metals")
        assert_constant(self, series[catalog.name("cash")], 0.0, "cash")
        self.assertEqual(len(series[catalog.name("stocks")]), PATHS * HORIZON)
        self.assertGreater(len(set(series[catalog.name("bonds")])), 1)

    def test_rust_matches_python_exactly(self) -> None:
        if not rust_engine_available():
            self.skipTest("libfinproj_engine is not available")
        with tempfile.TemporaryDirectory() as tmp:
            python_dir = Path(tmp) / "python"
            rust_dir = Path(tmp) / "rust"
            python_dir.mkdir()
            rust_dir.mkdir()
            run_simulation_python(constant_config(str(python_dir)))
            run_simulation_rust(constant_config(str(rust_dir)), write_outputs=True)
            python_returns = load_returns(python_dir / "output.csv")
            rust_returns = load_returns(rust_dir / "output.csv")
        catalog = default_config().asset_catalog
        for asset_id, mu in (("stocks", STOCKS_MU), ("pmetal", METAL_MU), ("cash", 0.0)):
            name = catalog.name(asset_id)
            assert_constant(self, rust_returns[name], mu, f"rust {name}")
            self.assertEqual(python_returns[name], rust_returns[name], msg=name)
        bonds = catalog.name("bonds")
        self.assertEqual(python_returns[bonds], rust_returns[bonds])

    def test_zero_sigma_is_per_year(self) -> None:
        config = default_config()
        config.max_year = 4
        config.nb_projections = 8
        config.rng_seed = 5
        config.risk_param["stocks"] = [
            {"from_year": 1, "rv": "norm", "mu": STOCKS_MU, "sigma": 0.0},
            {"from_year": 3, "rv": "norm", "mu": STOCKS_MU, "sigma": 15.0},
        ]
        name = config.asset_catalog.name("stocks")
        expected = STOCKS_MU / 100.0
        with tempfile.TemporaryDirectory() as tmp:
            config.output_dir = Path(tmp) / "python"
            config.output_dir.mkdir()
            run_simulation_python(config)
            by_year = returns_by_year(config.output_dir / "output.csv", name)
            if rust_engine_available():
                rust_config = copy.deepcopy(config)
                rust_config.output_dir = Path(tmp) / "rust"
                rust_config.output_dir.mkdir()
                run_simulation_rust(rust_config, write_outputs=True)
                rust_by_year = returns_by_year(rust_config.output_dir / "output.csv", name)
            else:
                rust_by_year = None
        for year in (1, 2):
            self.assertEqual(len(by_year[year]), 8)
            self.assertTrue(all(value == expected for value in by_year[year]), msg=f"year {year}")
        later = by_year[3] + by_year[4]
        self.assertTrue(any(value != expected for value in later))
        if rust_by_year is not None:
            self.assertEqual(rust_by_year, by_year)
