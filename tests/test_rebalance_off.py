# finproj - a holding with rebalance off compounds on its own
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import csv
import math
import random
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from asset_classes import AssetRole
from inv_proj_runner import default_config
from rust_engine import run_simulation_rust, rust_engine_available


HORIZON = 8
PATHS = 10
GROWTH = 1.01
MU_PCT = 1.0
REL_TOL = 1e-9
ABS_TOL = 1e-6


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def eligible_ids(config) -> list[str]:
    return [
        asset_id
        for asset_id, weight in config.risk_mix.items()
        if weight > 0 and config.asset_catalog.get(asset_id).has_role(AssetRole.INVESTABLE)
    ]


def config_for(frozen_id: str, rebalance_frozen: bool, tmp: str):
    config = default_config()
    config.max_year = HORIZON
    config.nb_projections = PATHS
    config.rng_seed = 7
    config.initial_capital = "1M"
    config.cash_buffer = "0"
    config.contributions = "0"
    config.withdrawals = "0"
    config.contributions_to_period = HORIZON
    config.withdrawals_to_period = HORIZON
    config.viva_source = None
    config.risk_correlation = {}
    config.output_dir = Path(tmp)
    config.asset_catalog.set_rebalance(frozen_id, rebalance_frozen)
    for asset_id, segments in config.risk_param.items():
        for segment in segments:
            if asset_id == frozen_id:
                segment["mu"] = MU_PCT
                segment["sigma"] = 0.0
            elif config.asset_catalog.get(asset_id).has_role(AssetRole.INVESTABLE):
                segment["sigma"] = 25.0
    return config


def load_series(csv_path: Path, name: str, variable: str) -> dict[int, dict[int, float]]:
    series: dict[int, dict[int, float]] = defaultdict(dict)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["variable"] == variable and row["risk"] == name:
                series[int(row["simulation"])][int(row["period"])] = float(row["value"])
    return series


class RebalanceOffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not rust_engine_available():
            raise unittest.SkipTest("libfinproj_engine is not available")
        catalog = default_config().asset_catalog
        ids = eligible_ids(default_config())
        cls.frozen_id = random.choice(ids)
        cls.frozen_name = catalog.name(cls.frozen_id)
        cls.peer_id = next(asset_id for asset_id in ids if asset_id != cls.frozen_id)
        cls.peer_name = catalog.name(cls.peer_id)
        cls.work = tempfile.TemporaryDirectory(prefix="finproj-rebalance-")
        off = config_for(cls.frozen_id, False, str(Path(cls.work.name) / "off"))
        on = config_for(cls.frozen_id, True, str(Path(cls.work.name) / "on"))
        Path(off.output_dir).mkdir(parents=True, exist_ok=True)
        Path(on.output_dir).mkdir(parents=True, exist_ok=True)
        run_simulation_rust(off, write_outputs=True)
        run_simulation_rust(on, write_outputs=True)
        cls.off_csv = Path(off.output_dir) / "output.csv"
        cls.on_csv = Path(on.output_dir) / "output.csv"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def test_random_frozen_sleeve_grows_one_percent_on_ten_paths(self) -> None:
        print(f"frozen asset: {self.frozen_id} ({self.frozen_name})", flush=True)
        eop = load_series(self.off_csv, self.frozen_name, "ptf_eop")
        bop = load_series(self.off_csv, self.frozen_name, "ptf_bop")
        ptf1 = load_series(self.off_csv, self.frozen_name, "ptf1")
        ptf2 = load_series(self.off_csv, self.frozen_name, "ptf2")
        ptf3 = load_series(self.off_csv, self.frozen_name, "ptf3")
        ptf5 = load_series(self.off_csv, self.frozen_name, "ptf5")
        returns = load_series(self.off_csv, self.frozen_name, "returns")
        peer_eop = load_series(self.off_csv, self.peer_name, "ptf_eop")

        self.assertEqual(sorted(eop), list(range(1, PATHS + 1)))
        starts = []
        for sim in range(1, PATHS + 1):
            start = bop[sim][1]
            starts.append(start)
            self.assertGreater(start, 0, msg=f"{self.frozen_name} start is 0")
            for year in range(1, HORIZON + 1):
                self.assertTrue(close(returns[sim][year], GROWTH - 1), msg=f"return sim={sim} year={year}")
                self.assertTrue(
                    close(ptf2[sim][year], ptf1[sim][year]),
                    msg=f"pre-return rebalance moved {self.frozen_name}",
                )
                self.assertTrue(
                    close(ptf3[sim][year], ptf2[sim][year] * GROWTH),
                    msg=f"applied return sim={sim} year={year}",
                )
                self.assertTrue(
                    close(ptf5[sim][year], ptf3[sim][year]),
                    msg=f"post-return rebalance moved {self.frozen_name}",
                )
                expected = start * (GROWTH**year)
                self.assertTrue(
                    close(eop[sim][year], expected),
                    msg=f"NAV sim={sim} year={year}: {eop[sim][year]} vs {expected}",
                )
                if year > 1:
                    self.assertTrue(
                        close(eop[sim][year] / eop[sim][year - 1], GROWTH),
                        msg=f"YoY sim={sim} year={year}",
                    )

        self.assertTrue(all(close(start, starts[0]) for start in starts))
        for year in range(1, HORIZON + 1):
            values = [eop[sim][year] for sim in range(1, PATHS + 1)]
            self.assertTrue(
                all(close(value, values[0]) for value in values),
                msg=f"frozen NAV differed across paths at year {year}",
            )

        peer_horizon = [peer_eop[sim][HORIZON] for sim in range(1, PATHS + 1)]
        self.assertGreater(
            max(peer_horizon) - min(peer_horizon),
            1.0,
            msg=f"{self.peer_name} paths did not disperse; the book may not be volatile",
        )

        on_eop = load_series(self.on_csv, self.frozen_name, "ptf_eop")
        drifted = 0
        for sim in range(1, PATHS + 1):
            for year in range(2, HORIZON + 1):
                prev = on_eop[sim][year - 1]
                if prev == 0:
                    continue
                if not close(on_eop[sim][year] / prev, GROWTH):
                    drifted += 1
        self.assertGreater(
            drifted,
            0,
            msg="rebalance-on control still grew at 1% every year; rebalance is not changing the mix",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
