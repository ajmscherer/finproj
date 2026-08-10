# finproj - regression tests for section edit open/close (no lost field content)
# Copyright (C) 2025-2026 Alex Scherer
#
# These tests lock in the enter/exit lifecycle that prevents Streamlit widget
# session keys from wiping user edits when sections are opened and closed.
#
# Display numbering (after Step 1 setup merged into Step 4 run section):
#   Step 1 = flows (internal helpers *_step_2_*)
#   Step 2 = allocation (internal helpers *_step_3_*)
#   Step 3 = returns (internal helpers *_step_4_*)
#   Step 4 = setup + run (setup helpers *_step_1_* / SETUP)

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "gui"))
sys.path.insert(0, str(PROJECT_ROOT / "code"))


class FakeSessionState(dict[str, Any]):
    """Minimal stand-in for st.session_state (dict + attribute access)."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class SectionContentEditableLifecycleTest(unittest.TestCase):
    """SectionContentEditable must commit on exit and seed on enter via hooks."""

    def test_on_click_enter_calls_hook_then_sets_editing(self) -> None:
        from section import SectionContentEditable

        state = FakeSessionState()
        events: list[str] = []

        def on_enter() -> None:
            events.append("enter")
            self.assertFalse(
                bool(state.get("section_step_1_editing")),
                "editing flag must still be false while on_enter runs",
            )

        section = SectionContentEditable(
            name="Step 1",
            title="Test",
            on_enter_edit=on_enter,
        )
        with patch("section.st.session_state", state):
            self.assertFalse(section.editing)
            section.on_click()
            self.assertTrue(section.editing)
        self.assertEqual(events, ["enter"])

    def test_on_click_exit_calls_hook_while_keys_still_present(self) -> None:
        from section import SectionContentEditable

        state = FakeSessionState()
        state["section_step_1_editing"] = True
        state["widget_key"] = "user value"
        events: list[str] = []

        def on_exit() -> None:
            events.append("exit")
            self.assertTrue(state.get("section_step_1_editing"))
            self.assertEqual(state.get("widget_key"), "user value")

        section = SectionContentEditable(
            name="Step 1",
            title="Test",
            on_exit_edit=on_exit,
        )
        with patch("section.st.session_state", state):
            self.assertTrue(section.editing)
            section.on_click()
            self.assertFalse(section.editing)
        self.assertEqual(events, ["exit"])

    def test_multiple_toggle_cycles_invoke_enter_exit_in_order(self) -> None:
        from section import SectionContentEditable

        state = FakeSessionState()
        events: list[str] = []

        section = SectionContentEditable(
            name="Step 1",
            title="Test",
            on_enter_edit=lambda: events.append("enter"),
            on_exit_edit=lambda: events.append("exit"),
        )
        with patch("section.st.session_state", state):
            section.on_click()
            section.on_click()
            section.on_click()
            section.on_click()
        self.assertEqual(events, ["enter", "exit", "enter", "exit"])


class SetupFieldsLifecycleTest(unittest.TestCase):
    """Setup fields (in Step 4) seed/commit without a separate edit section."""

    def setUp(self) -> None:
        self.state = FakeSessionState()
        self.state.portfolio = {
            "description": "Original scenario",
            "initial_capital": "1M",
            "contributions": "0k",
            "withdrawals": "50k",
            "cash_buffer": "150k",
            "max_year": 20,
            "nb_projections": 2000,
            "viva_source": "",
            "contributions_from_period": 1,
            "contributions_to_period": 20,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 20,
        }
        import app as gui_app

        self.app = gui_app
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_seed_loads_portfolio_into_edit_keys(self) -> None:
        self.app._on_enter_step_1_edit()
        self.assertEqual(self.state.portfolio_edit_description, "Original scenario")
        self.assertEqual(self.state.portfolio_edit_max_year, 20)
        self.assertEqual(self.state.portfolio_edit_nb_projections, 2000)
        self.assertNotIn("portfolio_edit_initial_capital", self.state)
        self.assertNotIn("portfolio_edit_cash_buffer", self.state)

    def test_commit_persists_setup_edits(self) -> None:
        self.app._ensure_setup_widgets_seeded()
        self.state.portfolio_edit_description = "Updated plan"
        self.state.portfolio_edit_max_year = 30
        self.state.portfolio_edit_nb_projections = 5000
        self.app._commit_step_1_edit_to_portfolio()

        self.assertEqual(self.state.portfolio["description"], "Updated plan")
        self.assertEqual(self.state.portfolio["max_year"], 30)
        self.assertEqual(self.state.portfolio["nb_projections"], 5000)

    def test_many_commit_cycles_do_not_lose_content(self) -> None:
        for i in range(8):
            self.app._ensure_setup_widgets_seeded()
            self.state.portfolio_edit_description = f"desc-{i}"
            self.state.portfolio_edit_max_year = 10 + i
            self.app._commit_step_1_edit_to_portfolio()

        self.app._ensure_setup_widgets_seeded()
        # Keys still present → ensure does not overwrite
        self.assertEqual(self.state.portfolio_edit_description, "desc-7")
        self.assertEqual(self.state.portfolio["description"], "desc-7")
        self.assertEqual(self.state.portfolio["max_year"], 17)

    def test_reseed_after_clear_restores_committed_portfolio(self) -> None:
        self.app._ensure_setup_widgets_seeded()
        self.state.portfolio_edit_description = "Cycle test"
        self.state.portfolio_edit_max_year = 25
        self.app._commit_step_1_edit_to_portfolio()
        self.app._clear_edit_keys(self.app.STEP_1_EDIT_KEYS)

        self.app._ensure_setup_widgets_seeded()
        self.assertEqual(self.state.portfolio_edit_description, "Cycle test")
        self.assertEqual(self.state.portfolio_edit_max_year, 25)


class Step1FlowsLifecycleTest(unittest.TestCase):
    """Step 1 (flows / Viva) — internal helpers are *_step_2_*."""

    def setUp(self) -> None:
        self.state = FakeSessionState()
        self.state.portfolio = {
            "description": "",
            "initial_capital": "1M",
            "contributions": "40k",
            "withdrawals": "30k",
            "cash_buffer": "100k",
            "max_year": 15,
            "nb_projections": 2000,
            "viva_source": "flow: none, 0 per year, for 15 years",
            "contributions_from_period": 2,
            "contributions_to_period": 10,
            "withdrawals_from_period": 5,
            "withdrawals_to_period": 15,
        }
        import app as gui_app

        self.app = gui_app
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_seed_loads_flow_fields_and_periods(self) -> None:
        self.app._on_enter_step_2_edit()
        self.assertEqual(self.state.portfolio_edit_contributions, "40k")
        self.assertEqual(self.state.portfolio_edit_withdrawals, "30k")
        self.assertIn("flow: none", self.state.portfolio_edit_viva_source)
        self.assertEqual(self.state.portfolio_edit_contributions_from_period, 2)
        self.assertEqual(self.state.portfolio_edit_contributions_to_period, 10)

    def test_exit_commits_flows_and_clears_keys(self) -> None:
        self.app._on_enter_step_2_edit()
        self.state.portfolio_edit_contributions = "75k"
        self.state.portfolio_edit_withdrawals = "12k"
        self.state.portfolio_edit_viva_source = "flow: bonus, 10k, year 2030"
        self.state.portfolio_edit_contributions_from_period = 1
        self.state.portfolio_edit_contributions_to_period = 8
        self.app._on_exit_step_2_edit()

        p = self.state.portfolio
        self.assertEqual(p["contributions"], "75k")
        self.assertEqual(p["withdrawals"], "12k")
        self.assertEqual(p["viva_source"], "flow: bonus, 10k, year 2030")
        self.assertEqual(p["contributions_from_period"], 1)
        self.assertEqual(p["contributions_to_period"], 8)
        for key in self.app.STEP_2_EDIT_KEYS:
            self.assertNotIn(key, self.state)

    def test_many_open_close_cycles_preserve_flows(self) -> None:
        for i in range(6):
            self.app._on_enter_step_2_edit()
            self.state.portfolio_edit_contributions = f"{10 + i}k"
            self.state.portfolio_edit_withdrawals = f"{20 + i}k"
            self.app._on_exit_step_2_edit()

        self.app._on_enter_step_2_edit()
        self.assertEqual(self.state.portfolio_edit_contributions, "15k")
        self.assertEqual(self.state.portfolio_edit_withdrawals, "25k")


class Step2AllocationLifecycleTest(unittest.TestCase):
    """Step 2 (allocation) — internal helpers are *_step_3_*."""

    def setUp(self) -> None:
        from asset_classes import default_asset_catalog
        from inv_proj_runner import DEFAULT_RISK_MIX_PRESETS

        self.state = FakeSessionState()
        self.state.asset_catalog = default_asset_catalog()
        self.state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
        self.state.portfolio = {
            "description": "",
            "initial_capital": "1M",
            "contributions": "0k",
            "withdrawals": "0k",
            "cash_buffer": "150k",
            "max_year": 20,
            "nb_projections": 1000,
            "viva_source": "",
            "contributions_from_period": 1,
            "contributions_to_period": 20,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 20,
        }
        import app as gui_app

        self.app = gui_app
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_seed_loads_names_allocations_and_capital(self) -> None:
        self.app._on_enter_step_3_edit()
        self.assertEqual(self.state.asset_name_stocks, "Stocks")
        self.assertEqual(self.state.portfolio_edit_initial_capital, "1M")
        self.assertEqual(self.state.portfolio_edit_cash_buffer, "150k")
        self.assertAlmostEqual(
            float(self.state.alloc_stocks),
            float(self.state.allocation["stocks"]),
        )

    def test_exit_commits_rename_allocation_and_capital(self) -> None:
        self.app._on_enter_step_3_edit()
        self.state.asset_name_stocks = "Equities"
        self.state.portfolio_edit_initial_capital = "2M"
        self.state.portfolio_edit_cash_buffer = "200k"
        self.state.alloc_stocks = 55.0
        self.state.alloc_bonds = 25.0
        self.state.alloc_money_market = 20.0
        for asset_id in list(self.state.allocation):
            key = f"alloc_{asset_id}"
            if key not in (
                "alloc_stocks",
                "alloc_bonds",
                "alloc_money_market",
            ) and key in self.state:
                self.state[key] = 0.0
        self.app._on_exit_step_3_edit()

        self.assertEqual(self.state.asset_catalog.name("stocks"), "Equities")
        self.assertEqual(self.state.portfolio["initial_capital"], "2M")
        self.assertEqual(self.state.portfolio["cash_buffer"], "200k")
        self.assertAlmostEqual(self.state.allocation["stocks"], 55.0)
        self.assertNotIn("asset_name_stocks", self.state)
        self.assertNotIn("alloc_stocks", self.state)
        self.assertNotIn("portfolio_edit_initial_capital", self.state)

    def test_reenter_shows_committed_allocation(self) -> None:
        self.app._on_enter_step_3_edit()
        self.state.alloc_stocks = 70.0
        self.state.alloc_bonds = 20.0
        self.state.alloc_money_market = 10.0
        for asset_id in list(self.state.allocation):
            key = f"alloc_{asset_id}"
            if key not in (
                "alloc_stocks",
                "alloc_bonds",
                "alloc_money_market",
            ) and key in self.state:
                self.state[key] = 0.0
        self.app._on_exit_step_3_edit()

        self.app._on_enter_step_3_edit()
        self.assertAlmostEqual(float(self.state.alloc_stocks), 70.0)
        self.assertAlmostEqual(float(self.state.alloc_bonds), 20.0)


class Step3ReturnsLifecycleTest(unittest.TestCase):
    """Step 3 (returns) — internal helpers are *_step_4_*."""

    def setUp(self) -> None:
        from asset_classes import default_asset_catalog
        from inv_proj_runner import (
            DEFAULT_RISK_CORRELATION,
            DEFAULT_RISK_MIX_PRESETS,
            DEFAULT_RISK_PARAM,
        )

        self.state = FakeSessionState()
        catalog = default_asset_catalog()
        self.state.asset_catalog = catalog
        self.state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
        self.state.correlation_values = copy.deepcopy(DEFAULT_RISK_CORRELATION)
        for asset_id, entries in DEFAULT_RISK_PARAM.items():
            self.state[f"mu_{asset_id}"] = float(entries[0]["mu"])
            self.state[f"sigma_{asset_id}"] = float(entries[0]["sigma"])

        import app as gui_app

        self.app = gui_app
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()
        self.app._init_correlation_keys(catalog)

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_seed_loads_mu_sigma(self) -> None:
        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(
            float(self.state.return_edit_mu_stocks), float(self.state.mu_stocks)
        )

    def test_exit_commits_returns(self) -> None:
        self.app._on_enter_step_4_edit()
        self.state.return_edit_mu_stocks = 12.5
        self.state.return_edit_sigma_stocks = 22.0
        self.app._on_exit_step_4_edit()
        self.assertAlmostEqual(float(self.state.mu_stocks), 12.5)
        self.assertAlmostEqual(float(self.state.sigma_stocks), 22.0)
        self.assertNotIn("return_edit_mu_stocks", self.state)

    def test_many_cycles_do_not_lose_returns(self) -> None:
        for i in range(6):
            self.app._on_enter_step_4_edit()
            self.state.return_edit_mu_stocks = 5.0 + i
            self.app._on_exit_step_4_edit()
        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(float(self.state.return_edit_mu_stocks), 10.0)


class CrossSectionIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        from asset_classes import default_asset_catalog
        from inv_proj_runner import (
            DEFAULT_RISK_CORRELATION,
            DEFAULT_RISK_MIX_PRESETS,
            DEFAULT_RISK_PARAM,
        )

        self.state = FakeSessionState()
        self.state.portfolio = {
            "description": "iso",
            "initial_capital": "1M",
            "contributions": "40k",
            "withdrawals": "30k",
            "cash_buffer": "100k",
            "max_year": 15,
            "nb_projections": 2000,
            "viva_source": "flow: keep me",
            "contributions_from_period": 1,
            "contributions_to_period": 15,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 15,
        }
        catalog = default_asset_catalog()
        self.state.asset_catalog = catalog
        self.state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
        self.state.correlation_values = copy.deepcopy(DEFAULT_RISK_CORRELATION)
        for asset_id, entries in DEFAULT_RISK_PARAM.items():
            self.state[f"mu_{asset_id}"] = float(entries[0]["mu"])
            self.state[f"sigma_{asset_id}"] = float(entries[0]["sigma"])

        import app as gui_app

        self.app = gui_app
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()
        self.app._init_correlation_keys(catalog)

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_allocation_edit_does_not_clear_setup(self) -> None:
        self.app._ensure_setup_widgets_seeded()
        self.state.portfolio_edit_description = "must survive"
        self.app._commit_step_1_edit_to_portfolio()

        self.app._on_enter_step_3_edit()
        self.state.alloc_stocks = 50.0
        self.app._on_exit_step_3_edit()

        self.assertEqual(self.state.portfolio["description"], "must survive")
        self.assertEqual(self.state.portfolio["viva_source"], "flow: keep me")

    def test_returns_edit_does_not_clear_flows(self) -> None:
        self.app._on_enter_step_2_edit()
        self.state.portfolio_edit_contributions = "99k"
        self.app._on_exit_step_2_edit()

        self.app._on_enter_step_4_edit()
        self.state.return_edit_mu_stocks = 8.8
        self.app._on_exit_step_4_edit()

        self.assertEqual(self.state.portfolio["contributions"], "99k")

    def test_full_walkthrough_multiple_passes(self) -> None:
        for pass_i in range(3):
            self.app._ensure_setup_widgets_seeded()
            self.state.portfolio_edit_description = f"pass-{pass_i}"
            self.app._commit_step_1_edit_to_portfolio()

            self.app._on_enter_step_2_edit()
            self.state.portfolio_edit_contributions = f"{pass_i}k"
            self.app._on_exit_step_2_edit()

            self.app._on_enter_step_3_edit()
            self.state.alloc_stocks = 50.0 + pass_i
            self.state.alloc_bonds = 30.0 - pass_i
            self.state.alloc_money_market = 20.0
            for asset_id in list(self.state.allocation):
                key = f"alloc_{asset_id}"
                if key not in (
                    "alloc_stocks",
                    "alloc_bonds",
                    "alloc_money_market",
                ) and key in self.state:
                    self.state[key] = 0.0
            self.app._on_exit_step_3_edit()

            self.app._on_enter_step_4_edit()
            self.state.return_edit_mu_stocks = 6.0 + pass_i
            self.app._on_exit_step_4_edit()

        self.assertEqual(self.state.portfolio["description"], "pass-2")
        self.assertEqual(self.state.portfolio["contributions"], "2k")
        self.app._on_enter_step_3_edit()
        self.assertAlmostEqual(float(self.state.alloc_stocks), 52.0)
        self.app._on_exit_step_3_edit()
        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(float(self.state.return_edit_mu_stocks), 8.0)


class SectionWiringTest(unittest.TestCase):
    def test_editable_sections_have_lifecycle_hooks(self) -> None:
        import app as gui_app

        for section in (gui_app.section1, gui_app.section2, gui_app.section3):
            self.assertIsNotNone(section.on_enter_edit, section.name)
            self.assertIsNotNone(section.on_exit_edit, section.name)

    def test_section_names_are_steps_1_through_4(self) -> None:
        import app as gui_app

        self.assertEqual(gui_app.section1.name, "Step 1")
        self.assertEqual(
            gui_app.section1.title,
            "Contributions, withdrawals, and additional flows",
        )
        self.assertEqual(gui_app.section2.name, "Step 2")
        self.assertEqual(gui_app.section2.title, "Portfolio")
        self.assertEqual(gui_app.section3.name, "Step 3")
        self.assertEqual(gui_app.section3.title, "Assets Performance")
        self.assertEqual(gui_app.section4.name, "Step 4")
        self.assertEqual(gui_app.section4.title, "Simulation")
        self.assertFalse(hasattr(gui_app, "section5"))

    def test_section_is_editing_uses_display_names(self) -> None:
        import app as gui_app

        state = FakeSessionState()
        state["section_step_1_editing"] = True
        state["section_step_2_editing"] = False
        with patch.object(gui_app.st, "session_state", state):
            self.assertTrue(gui_app._section_is_editing("Step 1"))
            self.assertFalse(gui_app._section_is_editing("Step 2"))


class SimulationRunSectionStabilityTest(unittest.TestCase):
    """Regression: Run simulation must not leave empty/flickering section frames.

    Guards the fixes around:
    - editing setter not clearing simulation_running
    - panel clicks ignored while a run is in progress
    - open edit modes force-closed (commit + exit) before a run starts
    """

    def test_entering_edit_clears_result_but_not_simulation_running(self) -> None:
        from section import SectionContentEditable

        state = FakeSessionState()
        state["result"] = object()
        state["simulation_running"] = True
        section = SectionContentEditable(name="Step 1", title="Test")
        with patch("section.st.session_state", state):
            section.editing = True
        self.assertIsNone(state.get("result"))
        # Run flag is owned by the run flow, not by section edit toggles.
        self.assertTrue(state.get("simulation_running"))

    def test_exiting_edit_does_not_clear_result_or_running(self) -> None:
        from section import SectionContentEditable

        state = FakeSessionState()
        state["section_step_1_editing"] = True
        sentinel = object()
        state["result"] = sentinel
        state["simulation_running"] = True
        section = SectionContentEditable(name="Step 1", title="Test")
        with patch("section.st.session_state", state):
            section.editing = False
        self.assertIs(state.get("result"), sentinel)
        self.assertTrue(state.get("simulation_running"))

    def test_panel_click_ignored_while_simulation_running(self) -> None:
        from section import SectionContentEditable

        state = FakeSessionState()
        state["simulation_running"] = True
        events: list[str] = []
        section = SectionContentEditable(
            name="Step 1",
            title="Test",
            on_enter_edit=lambda: events.append("enter"),
            on_exit_edit=lambda: events.append("exit"),
        )
        with patch("section.st.session_state", state):
            self.assertFalse(section.editing)
            section.on_click()  # would enter if not blocked
            self.assertFalse(section.editing)
            state["section_step_1_editing"] = True
            section.on_click()  # would exit if not blocked
            self.assertTrue(section.editing)
        self.assertEqual(events, [])

    def test_force_close_commits_open_step1_and_clears_editing_flag(self) -> None:
        import app as gui_app

        state = FakeSessionState()
        state.portfolio = {
            "description": "",
            "initial_capital": "1M",
            "contributions": "40k",
            "withdrawals": "30k",
            "cash_buffer": "100k",
            "max_year": 15,
            "nb_projections": 2000,
            "viva_source": "flow: keep",
            "contributions_from_period": 1,
            "contributions_to_period": 15,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 15,
        }
        state["section_step_1_editing"] = True
        state["result"] = object()
        state["simulation_running"] = False

        with patch.object(gui_app.st, "session_state", state):
            gui_app._on_enter_step_2_edit()
            state.portfolio_edit_contributions = "88k"
            state.portfolio_edit_withdrawals = "11k"
            # Leave keys present as if still editing (re-seed then mutate).
            state["section_step_1_editing"] = True

            gui_app._force_close_all_section_edits()

        self.assertFalse(state.get("section_step_1_editing"))
        self.assertEqual(state.portfolio["contributions"], "88k")
        self.assertEqual(state.portfolio["withdrawals"], "11k")
        # Force-close must not wipe an existing result by itself.
        self.assertIsNotNone(state.get("result"))

    def test_force_close_closes_all_three_editable_sections(self) -> None:
        import app as gui_app
        from asset_classes import default_asset_catalog
        from inv_proj_runner import (
            DEFAULT_RISK_CORRELATION,
            DEFAULT_RISK_MIX_PRESETS,
            DEFAULT_RISK_PARAM,
        )

        state = FakeSessionState()
        state.portfolio = {
            "description": "x",
            "initial_capital": "1M",
            "contributions": "40k",
            "withdrawals": "30k",
            "cash_buffer": "100k",
            "max_year": 15,
            "nb_projections": 500,
            "viva_source": "",
            "contributions_from_period": 1,
            "contributions_to_period": 15,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 15,
        }
        catalog = default_asset_catalog()
        state.asset_catalog = catalog
        state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
        state.correlation_values = copy.deepcopy(DEFAULT_RISK_CORRELATION)
        for asset_id, entries in DEFAULT_RISK_PARAM.items():
            state[f"mu_{asset_id}"] = float(entries[0]["mu"])
            state[f"sigma_{asset_id}"] = float(entries[0]["sigma"])

        with patch.object(gui_app.st, "session_state", state):
            gui_app._init_correlation_keys(catalog)
            state["section_step_1_editing"] = True
            state["section_step_2_editing"] = True
            state["section_step_3_editing"] = True
            gui_app._on_enter_step_2_edit()
            gui_app._on_enter_step_3_edit()
            gui_app._on_enter_step_4_edit()

            gui_app._force_close_all_section_edits()

        self.assertFalse(state.get("section_step_1_editing"))
        self.assertFalse(state.get("section_step_2_editing"))
        self.assertFalse(state.get("section_step_3_editing"))

    def test_request_simulation_run_closes_edits_sets_flags_and_reruns(self) -> None:
        import app as gui_app

        state = FakeSessionState()
        state.portfolio = {
            "description": "",
            "initial_capital": "1M",
            "contributions": "40k",
            "withdrawals": "30k",
            "cash_buffer": "100k",
            "max_year": 15,
            "nb_projections": 2000,
            "viva_source": "",
            "contributions_from_period": 1,
            "contributions_to_period": 15,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 15,
        }
        state["section_step_1_editing"] = True
        state["simulation_running"] = False
        state["run_simulation_requested"] = False

        with patch.object(gui_app.st, "session_state", state):
            gui_app._on_enter_step_2_edit()
            state.portfolio_edit_contributions = "77k"
            state["section_step_1_editing"] = True
            with patch.object(gui_app.st, "rerun") as rerun:
                gui_app._request_simulation_run()
                rerun.assert_called_once()

        self.assertFalse(state.get("section_step_1_editing"))
        self.assertEqual(state.portfolio["contributions"], "77k")
        self.assertTrue(state.get("run_simulation_requested"))
        self.assertTrue(state.get("simulation_running"))

    def test_show_editing_false_while_running_even_if_flag_set(self) -> None:
        """If edit flag is stuck True during a run, UI must still force readonly."""
        from section import SectionContentEditable

        state = FakeSessionState()
        state["section_step_1_editing"] = True
        state["simulation_running"] = True
        section = SectionContentEditable(name="Step 1", title="Test")
        with patch("section.st.session_state", state):
            # Same condition as SectionContentEditable.render()
            force_readonly = bool(state.get("simulation_running"))
            show_editing = section.editing and not force_readonly
            self.assertTrue(section.editing)  # flag may still be set
            self.assertTrue(force_readonly)
            self.assertFalse(show_editing)  # UI must not open edit forms mid-run

    def test_readonly_body_key_differs_from_edit_body_key(self) -> None:
        """Edit vs readonly must not reuse the same Streamlit container key.

        Distinct body keys keep Streamlit from remapping the form block when
        mode flips (a common cause of empty frames after Run force-closes edits).
        """
        from section import SectionContentEditable
        import inspect

        section = SectionContentEditable(name="Step 2", title="Portfolio")
        # Mirror key scheme in _render_inside_panel
        edit_key = f"{section._slug}_body_edit"
        ro_key = f"{section._slug}_body_ro"
        self.assertNotEqual(edit_key, ro_key)
        self.assertEqual(edit_key, "step_2_body_edit")
        self.assertEqual(ro_key, "step_2_body_ro")
        src = inspect.getsource(SectionContentEditable._render_inside_panel)
        self.assertIn("_body_edit", src)
        self.assertIn("_body_ro", src)
        # Readonly uses a horizontal row so Edit sits to the right of the form.
        self.assertIn("horizontal=not show_editing", src)

    def test_force_close_then_idle_layout_is_readonly_not_edit(self) -> None:
        """After Run is requested, all sections must be non-editing for next render."""
        import app as gui_app

        state = FakeSessionState()
        state.portfolio = {
            "description": "",
            "initial_capital": "1M",
            "contributions": "40k",
            "withdrawals": "30k",
            "cash_buffer": "100k",
            "max_year": 15,
            "nb_projections": 2000,
            "viva_source": "",
            "contributions_from_period": 1,
            "contributions_to_period": 15,
            "withdrawals_from_period": 1,
            "withdrawals_to_period": 15,
        }
        # Only Step 1 (flows) open — enough to prove force-close before run.
        state["section_step_1_editing"] = True
        state["section_step_2_editing"] = False
        state["section_step_3_editing"] = False

        with patch.object(gui_app.st, "session_state", state):
            gui_app._on_enter_step_2_edit()
            state["section_step_1_editing"] = True
            with patch.object(gui_app.st, "rerun"):
                gui_app._request_simulation_run()

        # Next paint must be readonly for every editable section.
        self.assertFalse(state.get("section_step_1_editing"))
        self.assertFalse(state.get("section_step_2_editing"))
        self.assertFalse(state.get("section_step_3_editing"))
        self.assertTrue(state.get("simulation_running"))


if __name__ == "__main__":
    unittest.main()


