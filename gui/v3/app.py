# finproj - Streamlit GUI v3
# Copyright (C) 2025-2026 Alex Scherer
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import streamlit as st
from guided import tour


def main() -> None:
    st.set_page_config(page_title="finproj", layout="centered")
    st.title("Serenity")
    tour.displayCurrentNode()
    

main()
