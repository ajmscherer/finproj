# finproj - tests for VivaFlowEngine
# Copyright (C) 2025-2026 Alex Scherer

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from viva_adapter import HAS_VIVA, FlowStructure, VivaFlowEngine

_VIVA_PROGRAM = (
    "flow: savings, 5000 per year, for 3 years\n"
    "flow: draw, -2000 per year, from year 2, for 2 years"
)


@unittest.skipUnless(HAS_VIVA, "viva is not installed")
class VivaFlowEngineTest(unittest.TestCase):
    def test_draw_flows_seed_1(self):
        engine = VivaFlowEngine.build(
            _VIVA_PROGRAM,
            start_year=2025,
            horizon_years=5,
        )
        result = engine.draw_flows(seed=1)

        self.assertIsInstance(result, FlowStructure)
        self.assertEqual(result.flows, [5000.0, 3000.0, 3000.0, 0, 0])
        self.assertEqual(
            result.audit,
            {
                "draw": [0, -2000.0, -2000.0, 0, 0],
                "savings": [5000.0, 5000.0, 5000.0, 0, 0],
            },
        )
        self.assertEqual(result.start_year, 2025)
        self.assertEqual(result.horizon_years, 5)
        self.assertEqual(result.seed, 1)


if __name__ == "__main__":
    unittest.main()
