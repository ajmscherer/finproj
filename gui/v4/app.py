# finproj - Streamlit GUI v4 (guided interview)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content.tour import build_definition
from model.runner import TourRunner
from ui.step_view import StepView


def _runner() -> TourRunner:
    if "v4_runner" not in st.session_state:
        st.session_state.v4_runner = TourRunner(build_definition())
    return st.session_state.v4_runner


def main() -> None:
    st.set_page_config(page_title="finproj", layout="centered")
    st.title("Serenity")
    st.caption("Guided interview. The projection engine is not called from this screen yet.")
    StepView(_runner()).render()


main()
