# finproj - tests for assumptions save/load
# Copyright (C) 2025-2026 Alex Scherer

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'code'))

from assumptions import Assumptions
from inv_proj_runner import DEFAULT_RISK_MIX_PRESETS, default_config, validate_allocation, validate_correlation


class AssumptionsTest(unittest.TestCase):
    def test_round_trip_json(self):
        catalog = default_config().asset_catalog
        assumptions = Assumptions.from_gui_state(
            name='Test scenario',
            initial_capital='2M',
            contributions='100k',
            withdrawals='50k',
            cash_buffer='120k',
            max_year=20,
            nb_projections=500,
            output_dir='output',
            mix_preset='moderate',
            asset_catalog=catalog,
            allocation=DEFAULT_RISK_MIX_PRESETS['moderate'],
            mu_sigma={'bonds': (2.0, 10.0), 'stocks': (7.0, 18.0), 'cash': (0.0, 0.0),
                      'money_market': (0.5, 4.0), 'crypto': (50.0, 100.0),
                      'pmetal': (1.0, 18.0), 'real_estate': (3.0, 15.0)},
            correlation_values={('money_market', 'bonds'): 0.5},
        )
        restored = Assumptions.from_json(assumptions.to_json())
        self.assertEqual(restored.name, 'Test scenario')
        self.assertEqual(restored.initial_capital, '2M')
        self.assertEqual(restored.max_year, 20)
        self.assertEqual(restored.allocation['bonds'], 45.0)

    def test_save_and_load_file(self):
        config = default_config()
        assumptions = Assumptions.from_gui_state(
            name='File test',
            initial_capital=config.initial_capital,
            contributions=config.contributions,
            withdrawals=config.withdrawals,
            cash_buffer=config.cash_buffer,
            max_year=config.max_year,
            nb_projections=config.nb_projections,
            output_dir=str(config.output_dir),
            mix_preset='performance',
            asset_catalog=config.asset_catalog,
            allocation=config.risk_mix,
            mu_sigma={
                asset_id: (entry[0]['mu'], entry[0]['sigma'])
                for asset_id, entry in config.risk_param.items()
            },
            correlation_values=config.risk_correlation,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'scenario.json'
            assumptions.save(path)
            loaded = Assumptions.load(path)
            self.assertEqual(loaded.name, 'File test')

    def test_to_simulation_config_is_valid(self):
        config = default_config()
        assumptions = Assumptions.from_gui_state(
            name='Runnable',
            initial_capital=config.initial_capital,
            contributions=config.contributions,
            withdrawals=config.withdrawals,
            cash_buffer=config.cash_buffer,
            max_year=config.max_year,
            nb_projections=10,
            output_dir=str(config.output_dir),
            mix_preset='performance',
            asset_catalog=config.asset_catalog,
            allocation=config.risk_mix,
            mu_sigma={
                asset_id: (entry[0]['mu'], entry[0]['sigma'])
                for asset_id, entry in config.risk_param.items()
            },
            correlation_values=config.risk_correlation,
        )
        sim_config = assumptions.to_simulation_config()
        validate_allocation(sim_config.risk_mix, sim_config.asset_catalog)
        validate_correlation(sim_config.risk_param, sim_config.risk_correlation)


if __name__ == '__main__':
    unittest.main()
