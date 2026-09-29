# finproj - Rust engine matches the Python projection engine
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from inv_proj_runner import default_config, run_simulation
from rust_engine import run_simulation_rust


def _close(left: float, right: float) -> bool:
    # Portfolio addition order in Python follows set iteration, so the same
    # seed can move the last bit when PYTHONHASHSEED changes. Stay well inside that.
    return abs(left - right) <= max(1e-6, 1e-9 * abs(left))


class RustEngineMatchTest(unittest.TestCase):
    def _compare(self, config) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            python_config = copy.deepcopy(config)
            python_config.output_dir = Path(tmp)
            python_result = run_simulation(python_config)
        rust_result = run_simulation_rust(copy.deepcopy(config))
        for year in range(1, config.max_year + 1):
            python_values = python_result.nav_fan.values_by_year[year]
            rust_values = rust_result.nav_fan.values_by_year[year]
            self.assertEqual(len(python_values), len(rust_values))
            for index, (left, right) in enumerate(zip(python_values, rust_values)):
                self.assertTrue(
                    _close(left, right),
                    msg=f"year {year} projection {index}: {left} vs {right}",
                )

    def test_default_schedule_matches_python(self) -> None:
        config = default_config()
        config.max_year = 6
        config.nb_projections = 8
        config.rng_seed = 1
        self._compare(config)

    def test_contributions_and_withdrawals_match_python(self) -> None:
        config = default_config()
        config.max_year = 6
        config.nb_projections = 5
        config.rng_seed = 7
        config.contributions = "40k"
        config.contributions_from_period = 2
        config.contributions_to_period = 4
        config.withdrawals = "10k"
        config.withdrawals_from_period = 1
        config.withdrawals_to_period = 3
        self._compare(config)

    def test_return_segments_match_python(self) -> None:
        config = default_config()
        config.max_year = 6
        config.nb_projections = 4
        config.rng_seed = 3
        config.risk_param["stocks"] = [
            {"from_year": 1, "rv": "norm", "mu": 6.5, "sigma": 20.0},
            {"from_year": 4, "rv": "norm", "mu": 1.0, "sigma": 5.0},
        ]
        self._compare(config)

    def test_custom_viva_source_matches_python(self) -> None:
        config = default_config()
        config.max_year = 5
        config.nb_projections = 4
        config.rng_seed = 4
        config.viva_source = "flow: bonus, 5k per year, from year 1, to year 3"
        self._compare(config)

    def test_rust_prefix_matches_longer_run(self) -> None:
        short = default_config()
        short.max_year = 4
        short.nb_projections = 4
        short.rng_seed = 9
        long = copy.deepcopy(short)
        long.nb_projections = 11
        short_result = run_simulation_rust(short)
        long_result = run_simulation_rust(long)
        for year, values in short_result.nav_fan.values_by_year.items():
            self.assertEqual(values, long_result.nav_fan.values_by_year[year][:4])


if __name__ == "__main__":
    unittest.main()
