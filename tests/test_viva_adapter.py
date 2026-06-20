# finproj - tests for Viva adapter integration
# Copyright (C) 2025-2026 Alex Scherer

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'code'))

from viva_adapter import HAS_VIVA, FlowSchedule, resolve_viva_schedules, viva_flows_to_schedule


class VivaFlowsToScheduleTest(unittest.TestCase):
    def test_maps_signs_to_contributions_and_withdrawals(self):
        flows = [
            {'date': date(2025, 1, 1), 'amount': 5000.0},
            {'date': date(2025, 1, 1), 'amount': -2000.0},
            {'date': date(2026, 1, 1), 'amount': 3000.0},
        ]
        schedule = viva_flows_to_schedule(flows, start_year=2025, nb_years=3)
        self.assertEqual(schedule.contributions, [5000.0, 3000.0, 0.0])
        self.assertEqual(schedule.withdrawals, [2000.0, 0.0, 0.0])

    def test_ignores_flows_outside_horizon(self):
        flows = [
            {'date': date(2024, 1, 1), 'amount': -1000.0},
            {'date': date(2028, 1, 1), 'amount': 1000.0},
        ]
        schedule = viva_flows_to_schedule(flows, start_year=2025, nb_years=2)
        self.assertEqual(schedule.contributions, [0.0, 0.0])
        self.assertEqual(schedule.withdrawals, [0.0, 0.0])


@unittest.skipUnless(HAS_VIVA, 'viva is not installed')
class ResolveVivaSchedulesTest(unittest.TestCase):
    def test_deterministic_viva_program(self):
        source = (
            'flow: savings, 5000 per year, for 3 years\n'
            'flow: draw, -2000 per year, from year 2, for 2 years'
        )
        schedule = resolve_viva_schedules(
            source,
            start_year=2025,
            horizon_years=3,
            probabilistic=False,
        )
        self.assertIsInstance(schedule, FlowSchedule)
        self.assertEqual(len(schedule.contributions), 3)
        self.assertEqual(schedule.contributions[0], 5000.0)
        self.assertEqual(schedule.withdrawals[1], 2000.0)


if __name__ == '__main__':
    unittest.main()
