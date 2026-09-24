# finproj - one field spec to a Streamlit control
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from typing import Any

import streamlit as st
from content.verbiage import Language
from model.paths import get_path
from model.state import TourState
from model.step import FieldSpec


class FieldWidget:
    """Draw one field. Does not decide which field comes next."""

    def __init__(self, spec: FieldSpec) -> None:
        self.spec = spec

    def key(self) -> str:
        return "v4w_" + self.spec.path.replace(".", "_")

    def seed(self, state: TourState) -> None:
        key = self.key()
        if key in st.session_state:
            return
        value = get_path(state, self.spec.path)
        if value is None:
            return
        st.session_state[key] = value

    def render(self, language: Language) -> None:
        spec = self.spec
        st.markdown(f"**{spec.label}**")
        if spec.help:
            st.caption(spec.help)
        key = self.key()
        if spec.kind == "choice":
            labels = spec.choice_labels or {}
            st.radio(
                spec.label.to(language),
                options=list(spec.choices or ()),
                format_func=lambda value: labels.get(value, value),
                key=key,
                label_visibility="visible",
                help=spec.help.to(language) if spec.help else None,
            )
        elif spec.kind == "text":
            st.text_area(spec.label.to(language), key=key, label_visibility="collapsed")
        elif spec.kind == "amount":
            st.text_input(spec.label.to(language), key=key, label_visibility="collapsed")
        elif spec.kind == "int":
            st.number_input(
                spec.label.to(language),
                min_value=None if spec.min is None else int(spec.min),
                max_value=None if spec.max is None else int(spec.max),
                step=1,
                key=key,
                label_visibility="collapsed",
            )
        elif spec.kind == "percent":
            st.number_input(
                spec.label.to(language),
                min_value=None if spec.min is None else float(spec.min),
                max_value=None if spec.max is None else float(spec.max),
                step=0.5,
                key=key,
                label_visibility="collapsed",
            )

    def read(self) -> Any:
        key = self.key()
        if key not in st.session_state:
            return None
        value = st.session_state[key]
        if self.spec.kind in {"text", "amount"} and value == "":
            return None
        return value
