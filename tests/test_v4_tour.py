# finproj - v4 tour runner (no Streamlit, no engine)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gui" / "v4"))

from content.tour import build_definition
from model.runner import TourRunner


class TourPathTest(unittest.TestCase):
    def test_other_text_cleared_when_goal_changes(self) -> None:
        runner = TourRunner(build_definition())
        runner.apply({"goal.kind": "other", "goal.other_text": "estate planning"})
        self.assertIsNotNone(runner.current())
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "wealth")
        self.assertEqual(runner.state.goal.other_text, "estate planning")

        runner.back()
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "goal")
        runner.apply({"goal.kind": "retire_when"})
        self.assertIsNone(runner.state.goal.other_text)
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "wealth")

    def test_linear_spine_after_goal(self) -> None:
        runner = TourRunner(build_definition())
        runner.apply({"goal.kind": "retire_when"})
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "wealth")
        runner.apply(
            {"wealth.initial_capital": "1M", "wealth.cash_buffer": "150k"}
        )
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "flows")
        runner.apply({"flows.contributions": "0k", "flows.withdrawals": "50k"})
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "mix")

    def test_other_field_hidden_until_selected(self) -> None:
        runner = TourRunner(build_definition())
        goal = runner.current()
        assert goal is not None
        self.assertEqual(
            [spec.path for spec in goal.visible_fields(runner.state)],
            ["goal.kind"],
        )
        preview = runner.preview({"goal.kind": "other"})
        self.assertEqual(
            [spec.path for spec in goal.visible_fields(preview)],
            ["goal.kind", "goal.other_text"],
        )


if __name__ == "__main__":
    unittest.main()
