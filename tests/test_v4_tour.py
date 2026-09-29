# finproj - v4 tour runner (no Streamlit, no engine)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_V4 = Path(__file__).resolve().parent.parent / "gui" / "v4"
sys.path.insert(0, str(_V4))

from content.tour import build_definition
from content.verbiage import Verbiage
from model.definition import TourDefinition
from model.runner import TourRunner
from model.step import FieldSpec, Step

# gui/v4 also contains app.py. Leave it off sys.path so other tests
# keep importing the v1 GUI module.
sys.path.remove(str(_V4))

_INTRO = {
    "intro.goal": "retire_when",
    "intro.legacy": "not_sure",
    "intro.initial_capital": "1M",
    "intro.cash_buffer": "150k",
}


class TourPathTest(unittest.TestCase):
    def test_conditional_intro_fields(self) -> None:
        runner = TourRunner(build_definition())
        intro = runner.current()
        assert intro is not None
        always = [
            "intro.goal",
            "intro.legacy",
            "intro.initial_capital",
            "intro.cash_buffer",
        ]
        self.assertEqual(
            [spec.path for spec in intro.visible_fields(runner.state)],
            always,
        )

        retire = runner.preview({"intro.goal": "retire_when"})
        self.assertEqual(
            [spec.path for spec in intro.visible_fields(retire)],
            [
                "intro.goal",
                "intro.legacy",
                "intro.target_income",
                "intro.initial_capital",
                "intro.cash_buffer",
            ],
        )

        saving = runner.preview({"intro.goal": "save_for_income"})
        self.assertEqual(
            [spec.path for spec in intro.visible_fields(saving)],
            [
                "intro.goal",
                "intro.legacy",
                "intro.target_income",
                "intro.years_to_retire",
                "intro.initial_capital",
                "intro.cash_buffer",
            ],
        )

        other = runner.preview({"intro.goal": "other"})
        self.assertEqual(
            [spec.path for spec in intro.visible_fields(other)],
            always,
        )

    def test_linear_spine_after_intro(self) -> None:
        runner = TourRunner(build_definition())
        runner.apply(_INTRO)
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "flows")
        self.assertEqual(runner.state.intro.initial_capital, "1M")
        self.assertEqual(runner.state.intro.cash_buffer, "150k")
        runner.apply({"flows.contributions": "0k", "flows.withdrawals": "50k"})
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "mix")
        self.assertEqual(runner.state.flows.withdrawals, "50k")

    def test_retreat_keeps_answers_from_the_step_left(self) -> None:
        runner = TourRunner(build_definition())
        runner.apply(_INTRO)
        runner.retreat({"flows.contributions": "10k", "flows.withdrawals": "0k"})
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "intro")
        self.assertEqual(runner.state.intro.cash_buffer, "150k")
        self.assertEqual(runner.state.flows.contributions, "10k")
        self.assertEqual(runner.state.flows.withdrawals, "0k")

    def test_go_to_visited_step_keeps_later_answers(self) -> None:
        runner = TourRunner(build_definition())
        runner.apply(_INTRO)
        runner.apply({"flows.contributions": "0k", "flows.withdrawals": "50k"})
        runner.go_to("intro", {"mix.money_market": 20, "mix.bonds": 30, "mix.stocks": 50})
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "intro")
        self.assertEqual(runner.history, [])
        self.assertEqual(runner.state.intro.initial_capital, "1M")
        self.assertEqual(runner.state.flows.withdrawals, "50k")
        self.assertEqual(runner.state.mix.money_market, 20)

    def test_changing_an_answer_clears_dependents_not_resubmitted(self) -> None:
        label = Verbiage({"en": "label"})
        intro = Step(
            id="intro",
            title=label,
            prompt=label,
            fields=[
                FieldSpec("intro.goal", label, "choice"),
                FieldSpec("intro.target_income", label, "amount"),
            ],
            default_next="flows",
            clears_on_change=("intro.target_income",),
        )
        flows = Step(id="flows", title=label, prompt=label, fields=[])
        runner = TourRunner(TourDefinition([intro, flows], start="intro"))
        runner.state.intro.goal = "retire_when"
        runner.state.intro.target_income = "80k"
        runner.apply({"intro.goal": "other"})
        self.assertEqual(runner.state.intro.goal, "other")
        self.assertIsNone(runner.state.intro.target_income)
        assert runner.current() is not None
        self.assertEqual(runner.current().id, "flows")


if __name__ == "__main__":
    unittest.main()
