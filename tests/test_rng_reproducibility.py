# finproj - reproducible Monte Carlo seeds
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from inv_proj import STREAM_RETURNS, STREAM_VIVA, mix_seed
from inv_proj_runner import default_config, run_simulation


def _nav_snapshot(result) -> list[tuple[str, float, float, int]]:
    rows = []
    for name, observer in result.nav_observers.items():
        rows.append((name, observer.mean(), observer.std(), len(observer.values)))
    return rows


class MixSeedTest(unittest.TestCase):
    def test_stable_and_distinct_streams(self) -> None:
        a = mix_seed(1, STREAM_RETURNS, 1)
        b = mix_seed(1, STREAM_RETURNS, 1)
        self.assertEqual(a, b)
        self.assertNotEqual(mix_seed(1, STREAM_RETURNS, 1), mix_seed(1, STREAM_RETURNS, 2))
        self.assertNotEqual(mix_seed(1, STREAM_RETURNS, 1), mix_seed(1, STREAM_VIVA, 1))
        self.assertNotEqual(mix_seed(1, STREAM_RETURNS, 1), mix_seed(2, STREAM_RETURNS, 1))


class RunReproducibilityTest(unittest.TestCase):
    def _config(self, *, n: int, seed: int, tmp: str):
        config = default_config()
        config.nb_projections = n
        config.rng_seed = seed
        config.output_dir = Path(tmp)
        return config

    def test_same_seed_same_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            a = run_simulation(self._config(n=40, seed=1, tmp=tmp1))
            b = run_simulation(self._config(n=40, seed=1, tmp=tmp2))
        self.assertEqual(_nav_snapshot(a), _nav_snapshot(b))

    def test_different_seed_changes_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            a = run_simulation(self._config(n=40, seed=1, tmp=tmp1))
            b = run_simulation(self._config(n=40, seed=2, tmp=tmp2))
        self.assertNotEqual(_nav_snapshot(a), _nav_snapshot(b))

    def test_prefix_of_longer_run_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            short = run_simulation(self._config(n=10, seed=7, tmp=tmp1))
            long = run_simulation(self._config(n=25, seed=7, tmp=tmp2))
        for name in short.nav_observers:
            self.assertEqual(
                short.nav_observers[name].values,
                long.nav_observers[name].values[:10],
            )


if __name__ == "__main__":
    unittest.main()
