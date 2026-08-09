# finproj - regression tests for section edit open/close (no lost field content)
# Copyright (C) 2025-2026 Alex Scherer
#
# These tests lock in the enter/exit lifecycle that prevents Streamlit widget
# session keys from wiping user edits when sections are opened and closed.

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


def _import_app_with_session(state: FakeSessionState):
    """Import gui.app with st.session_state replaced by *state*."""
    # Fresh import path for app helpers (app is large; import once per test class setup).
    import app as gui_app
    import streamlit as st

    return gui_app, st


class SectionContentEditableLifecycleTest(unittest.TestCase):
    """SectionContentEditable must commit on exit and seed on enter via hooks."""

    def test_on_click_enter_calls_hook_then_sets_editing(self):
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

    def test_on_click_exit_calls_hook_while_keys_still_present(self):
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

    def test_multiple_toggle_cycles_invoke_enter_exit_in_order(self):
        from section import SectionContentEditable

        state = FakeSessionState()
        events: list[str] = []

        section = SectionContentEditable(
            name="Step 2",
            title="Test",
            on_enter_edit=lambda: events.append("enter"),
            on_exit_edit=lambda: events.append("exit"),
        )
        with patch("section.st.session_state", state):
            section.on_click()  # enter
            section.on_click()  # exit
            section.on_click()  # enter
            section.on_click()  # exit
        self.assertEqual(events, ["enter", "exit", "enter", "exit"])


class Step1EditLifecycleTest(unittest.TestCase):
    """Step 1 (simulation setup) seed → edit → exit → re-enter preserves values."""

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
        self.assertEqual(self.state.portfolio_edit_initial_capital, "1M")
        self.assertEqual(self.state.portfolio_edit_cash_buffer, "150k")
        self.assertEqual(self.state.portfolio_edit_max_year, 20)
        self.assertEqual(self.state.portfolio_edit_nb_projections, 2000)

    def test_exit_commits_edits_and_clears_widget_keys(self) -> None:
        self.app._on_enter_step_1_edit()
        self.state.portfolio_edit_description = "Updated plan"
        self.state.portfolio_edit_initial_capital = "2.5M"
        self.state.portfolio_edit_cash_buffer = "200k"
        self.state.portfolio_edit_max_year = 30
        self.state.portfolio_edit_nb_projections = 5000

        self.app._on_exit_step_1_edit()

        self.assertEqual(self.state.portfolio["description"], "Updated plan")
        self.assertEqual(self.state.portfolio["initial_capital"], "2.5M")
        self.assertEqual(self.state.portfolio["cash_buffer"], "200k")
        self.assertEqual(self.state.portfolio["max_year"], 30)
        self.assertEqual(self.state.portfolio["nb_projections"], 5000)
        for key in self.app.STEP_1_EDIT_KEYS:
            self.assertNotIn(key, self.state, f"{key} should be cleared after exit")

    def test_reenter_after_exit_restores_committed_values_not_defaults(self) -> None:
        self.app._on_enter_step_1_edit()
        self.state.portfolio_edit_description = "Cycle test"
        self.state.portfolio_edit_initial_capital = "900k"
        self.app._on_exit_step_1_edit()

        # Simulate Streamlit dropping unbound widget keys (already cleared on exit).
        self.app._on_enter_step_1_edit()
        self.assertEqual(self.state.portfolio_edit_description, "Cycle test")
        self.assertEqual(self.state.portfolio_edit_initial_capital, "900k")

    def test_many_open_close_cycles_do_not_lose_content(self) -> None:
        for i in range(8):
            self.app._on_enter_step_1_edit()
            self.state.portfolio_edit_description = f"desc-{i}"
            self.state.portfolio_edit_initial_capital = f"{100 + i}k"
            self.state.portfolio_edit_cash_buffer = f"{50 + i}k"
            self.state.portfolio_edit_max_year = 10 + i
            self.state.portfolio_edit_nb_projections = 1000 + i * 10
            self.app._on_exit_step_1_edit()

        self.app._on_enter_step_1_edit()
        self.assertEqual(self.state.portfolio_edit_description, "desc-7")
        self.assertEqual(self.state.portfolio_edit_initial_capital, "107k")
        self.assertEqual(self.state.portfolio_edit_cash_buffer, "57k")
        self.assertEqual(self.state.portfolio_edit_max_year, 17)
        self.assertEqual(self.state.portfolio_edit_nb_projections, 1070)

    def test_exit_without_widget_keys_does_not_wipe_portfolio(self) -> None:
        """Exit when keys already gone must not blank portfolio (Done edge case)."""
        original = copy.deepcopy(self.state.portfolio)
        self.app._on_exit_step_1_edit()
        self.assertEqual(self.state.portfolio, original)


class Step2EditLifecycleTest(unittest.TestCase):
    """Step 2 (flows / Viva) seed → edit → exit → re-enter preserves values."""

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
        self.assertEqual(self.state.portfolio_edit_withdrawals_from_period, 5)
        self.assertEqual(self.state.portfolio_edit_withdrawals_to_period, 15)

    def test_exit_commits_flows_and_clears_keys(self) -> None:
        self.app._on_enter_step_2_edit()
        self.state.portfolio_edit_contributions = "75k"
        self.state.portfolio_edit_withdrawals = "12k"
        self.state.portfolio_edit_viva_source = "flow: bonus, 10k, year 2030"
        self.state.portfolio_edit_contributions_from_period = 1
        self.state.portfolio_edit_contributions_to_period = 8
        self.state.portfolio_edit_withdrawals_from_period = 3
        self.state.portfolio_edit_withdrawals_to_period = 12
        self.app._on_exit_step_2_edit()

        p = self.state.portfolio
        self.assertEqual(p["contributions"], "75k")
        self.assertEqual(p["withdrawals"], "12k")
        self.assertEqual(p["viva_source"], "flow: bonus, 10k, year 2030")
        self.assertEqual(p["contributions_from_period"], 1)
        self.assertEqual(p["contributions_to_period"], 8)
        self.assertEqual(p["withdrawals_from_period"], 3)
        self.assertEqual(p["withdrawals_to_period"], 12)
        for key in self.app.STEP_2_EDIT_KEYS:
            self.assertNotIn(key, self.state)

    def test_alternating_step1_and_step2_cycles_preserve_both(self) -> None:
        """Regression: editing step 1 then step 2 repeatedly must not wipe either."""
        for i in range(5):
            self.app._on_enter_step_1_edit()
            self.state.portfolio_edit_description = f"s1-{i}"
            self.state.portfolio_edit_initial_capital = f"{200 + i}k"
            self.app._on_exit_step_1_edit()

            self.app._on_enter_step_2_edit()
            self.state.portfolio_edit_contributions = f"{10 + i}k"
            self.state.portfolio_edit_withdrawals = f"{20 + i}k"
            self.state.portfolio_edit_viva_source = f"flow: cycle {i}"
            self.app._on_exit_step_2_edit()

        self.app._on_enter_step_1_edit()
        self.assertEqual(self.state.portfolio_edit_description, "s1-4")
        self.assertEqual(self.state.portfolio_edit_initial_capital, "204k")
        self.app._on_exit_step_1_edit()

        self.app._on_enter_step_2_edit()
        self.assertEqual(self.state.portfolio_edit_contributions, "14k")
        self.assertEqual(self.state.portfolio_edit_withdrawals, "24k")
        self.assertEqual(self.state.portfolio_edit_viva_source, "flow: cycle 4")


class Step3EditLifecycleTest(unittest.TestCase):
    """Step 3 (allocation) seed → edit → exit → re-enter preserves values."""

    def setUp(self) -> None:
        from asset_classes import default_asset_catalog
        from inv_proj_runner import DEFAULT_RISK_MIX_PRESETS

        self.state = FakeSessionState()
        self.state.asset_catalog = default_asset_catalog()
        self.state.allocation = copy.deepcopy(DEFAULT_RISK_MIX_PRESETS["performance"])
        import app as gui_app

        self.app = gui_app
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_seed_loads_names_and_allocations(self) -> None:
        self.app._on_enter_step_3_edit()
        self.assertEqual(self.state.asset_name_stocks, "Stocks")
        self.assertIn("alloc_stocks", self.state)
        self.assertAlmostEqual(
            float(self.state.alloc_stocks),
            float(self.state.allocation["stocks"]),
        )

    def test_exit_commits_rename_and_allocation_changes(self) -> None:
        self.app._on_enter_step_3_edit()
        self.state.asset_name_stocks = "Equities"
        self.state.alloc_stocks = 55.0
        self.state.alloc_bonds = 25.0
        self.state.alloc_money_market = 20.0
        # zero out optionals if present
        for asset_id in list(self.state.allocation):
            key = f"alloc_{asset_id}"
            if key not in (
                "alloc_stocks",
                "alloc_bonds",
                "alloc_money_market",
            ) and key in self.state:
                self.state[key] = 0.0

        self.app._on_exit_step_3_edit()

        catalog = self.state.asset_catalog
        self.assertEqual(catalog.name("stocks"), "Equities")
        self.assertAlmostEqual(self.state.allocation["stocks"], 55.0)
        self.assertAlmostEqual(self.state.allocation["bonds"], 25.0)
        self.assertAlmostEqual(self.state.allocation["money_market"], 20.0)
        self.assertNotIn("asset_name_stocks", self.state)
        self.assertNotIn("alloc_stocks", self.state)

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
        self.assertAlmostEqual(float(self.state.alloc_money_market), 10.0)

    def test_many_cycles_do_not_lose_allocation(self) -> None:
        for i in range(6):
            self.app._on_enter_step_3_edit()
            stocks = 40.0 + i
            bonds = 40.0 - i
            mm = 20.0
            self.state.alloc_stocks = stocks
            self.state.alloc_bonds = bonds
            self.state.alloc_money_market = mm
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
        self.assertAlmostEqual(float(self.state.alloc_stocks), 45.0)
        self.assertAlmostEqual(float(self.state.alloc_bonds), 35.0)
        self.assertAlmostEqual(float(self.state.alloc_money_market), 20.0)


class Step4EditLifecycleTest(unittest.TestCase):
    """Step 4 (returns / correlations) seed → edit → exit → re-enter preserves values."""

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
            self.state[f"corr_{asset_id}"] = 0.0  # unused placeholder ok

        import app as gui_app

        self.app = gui_app
        # Init correlation pair keys the way the app does
        self.patcher = patch.object(gui_app.st, "session_state", self.state)
        self.patcher.start()
        self.app._init_correlation_keys(catalog)

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_seed_loads_mu_sigma_into_edit_keys(self) -> None:
        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(
            float(self.state.return_edit_mu_stocks),
            float(self.state.mu_stocks),
        )
        self.assertAlmostEqual(
            float(self.state.return_edit_sigma_stocks),
            float(self.state.sigma_stocks),
        )

    def test_exit_commits_return_and_correlation_edits(self) -> None:
        self.app._on_enter_step_4_edit()
        self.state.return_edit_mu_stocks = 12.5
        self.state.return_edit_sigma_stocks = 22.0
        # Flip a known correlation pair if present
        edit_key = "return_edit_corr_bonds_stocks"
        if edit_key not in self.state:
            # find any return_edit_corr_* key
            corr_keys = [k for k in self.state if str(k).startswith("return_edit_corr_")]
            self.assertTrue(corr_keys, "expected correlation edit keys after seed")
            edit_key = corr_keys[0]
        self.state[edit_key] = -0.42

        self.app._on_exit_step_4_edit()

        self.assertAlmostEqual(float(self.state.mu_stocks), 12.5)
        self.assertAlmostEqual(float(self.state.sigma_stocks), 22.0)
        self.assertNotIn("return_edit_mu_stocks", self.state)
        self.assertNotIn(edit_key, self.state)
        # correlation_values should hold the committed rho
        found = False
        for rho in self.state.correlation_values.values():
            if abs(float(rho) - (-0.42)) < 1e-9:
                found = True
                break
        self.assertTrue(found, "committed correlation not found in correlation_values")

    def test_reenter_restores_committed_returns(self) -> None:
        self.app._on_enter_step_4_edit()
        self.state.return_edit_mu_stocks = 9.9
        self.state.return_edit_sigma_bonds = 11.1
        self.app._on_exit_step_4_edit()

        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(float(self.state.return_edit_mu_stocks), 9.9)
        self.assertAlmostEqual(float(self.state.return_edit_sigma_bonds), 11.1)

    def test_many_cycles_do_not_lose_returns(self) -> None:
        for i in range(6):
            self.app._on_enter_step_4_edit()
            self.state.return_edit_mu_stocks = 5.0 + i
            self.state.return_edit_sigma_stocks = 15.0 + i
            self.app._on_exit_step_4_edit()

        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(float(self.state.return_edit_mu_stocks), 10.0)
        self.assertAlmostEqual(float(self.state.return_edit_sigma_stocks), 20.0)


class CrossSectionIsolationTest(unittest.TestCase):
    """Edits in one section must not clobber another section's canonical data."""

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

    def test_step3_edit_does_not_clear_step1_portfolio(self) -> None:
        self.app._on_enter_step_1_edit()
        self.state.portfolio_edit_description = "must survive step 3"
        self.app._on_exit_step_1_edit()

        self.app._on_enter_step_3_edit()
        self.state.alloc_stocks = 50.0
        self.app._on_exit_step_3_edit()

        self.assertEqual(self.state.portfolio["description"], "must survive step 3")
        self.assertEqual(self.state.portfolio["viva_source"], "flow: keep me")

    def test_step4_edit_does_not_clear_step2_flows(self) -> None:
        self.app._on_enter_step_2_edit()
        self.state.portfolio_edit_contributions = "99k"
        self.state.portfolio_edit_viva_source = "flow: protected"
        self.app._on_exit_step_2_edit()

        self.app._on_enter_step_4_edit()
        self.state.return_edit_mu_stocks = 8.8
        self.app._on_exit_step_4_edit()

        self.assertEqual(self.state.portfolio["contributions"], "99k")
        self.assertEqual(self.state.portfolio["viva_source"], "flow: protected")

    def test_full_walkthrough_all_sections_multiple_passes(self) -> None:
        """Simulate user opening each section several times in sequence."""
        for pass_i in range(3):
            self.app._on_enter_step_1_edit()
            self.state.portfolio_edit_description = f"pass-{pass_i}"
            self.state.portfolio_edit_initial_capital = f"{1000 + pass_i}k"
            self.app._on_exit_step_1_edit()

            self.app._on_enter_step_2_edit()
            self.state.portfolio_edit_contributions = f"{pass_i}k"
            self.state.portfolio_edit_withdrawals = f"{pass_i + 1}k"
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

        # Final re-open of each section must show last pass values
        self.app._on_enter_step_1_edit()
        self.assertEqual(self.state.portfolio_edit_description, "pass-2")
        self.assertEqual(self.state.portfolio_edit_initial_capital, "1002k")
        self.app._on_exit_step_1_edit()

        self.app._on_enter_step_2_edit()
        self.assertEqual(self.state.portfolio_edit_contributions, "2k")
        self.assertEqual(self.state.portfolio_edit_withdrawals, "3k")
        self.app._on_exit_step_2_edit()

        self.app._on_enter_step_3_edit()
        self.assertAlmostEqual(float(self.state.alloc_stocks), 52.0)
        self.assertAlmostEqual(float(self.state.alloc_bonds), 28.0)
        self.app._on_exit_step_3_edit()

        self.app._on_enter_step_4_edit()
        self.assertAlmostEqual(float(self.state.return_edit_mu_stocks), 8.0)


class SectionWiringTest(unittest.TestCase):
    """Section instances must wire enter/exit hooks (guards against accidental unhook)."""

    def test_sections_have_lifecycle_hooks(self) -> None:
        import app as gui_app

        for section in (
            gui_app.section1,
            gui_app.section2,
            gui_app.section3,
            gui_app.section4,
        ):
            self.assertIsNotNone(
                section.on_enter_edit,
                f"{section.name} missing on_enter_edit",
            )
            self.assertIsNotNone(
                section.on_exit_edit,
                f"{section.name} missing on_exit_edit",
            )

    def test_section_names_are_step_1_through_4(self) -> None:
        import app as gui_app

        self.assertEqual(gui_app.section1.name, "Step 1")
        self.assertEqual(gui_app.section2.name, "Step 2")
        self.assertEqual(gui_app.section3.name, "Step 3")
        self.assertEqual(gui_app.section4.name, "Step 4")
        self.assertEqual(gui_app.section5.name, "Step 5")


if __name__ == "__main__":
    unittest.main()
