# finproj - Section component for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.

from __future__ import annotations

import html
from collections.abc import Callable
from dataclasses import dataclass
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from click_panel import ClickPanelRegistry, click_panel
from theme import THEME


def _need_to_be_implemented() -> None:
    st.write("Need to be implemented")


@dataclass
class SectionBaseLayout:
    name: str
    left_column_width: int = int(THEME.get("section_left_column_width", 100))

    @property
    def _slug(self) -> str:
        return self.name.lower().replace(" ", "_")

    def renderLayout(self) -> tuple[DeltaGenerator, DeltaGenerator]:
        with st.container(
            horizontal=True,
            gap="small", 
            vertical_alignment="center",
            key=f"section_{self._slug}_main_container",
        ):
            left=st.container(width=self.left_column_width, key=f"{self._slug}_left_column", gap="small")
            right=st.container(width="stretch", key=f"{self._slug}_right_column", gap="small")
            return left, right
@dataclass           
class Section(SectionBaseLayout):
    title: str = "No Title"
    content_form: Callable[[], None]|None = None
    
    @property
    def _content_container_key(self) -> str:
        return f"{self._slug}_panel"

    def render(self) -> tuple[DeltaGenerator, DeltaGenerator]:
        left, right0 =  super().renderLayout()
        with left:
            st.markdown(f'<p class="fp-section-title">{html.escape(self.name)}</p>', unsafe_allow_html=True)
        with right0:
            st.header(self.title)
            right = st.container(width="stretch", border=True, key=self._content_container_key)
            with right:
                if self.content_form:
                    self.content_form()
        return left, right

@dataclass
class SectionContentEditable(Section):
    edit_form: Callable[[], None] = _need_to_be_implemented
    readonly_form: Callable[[], None] = _need_to_be_implemented
    done_button_text: str = "Done"
    edit_button_text: str = "Edit"

    @property
    def _slug(self) -> str:
        return self.name.lower().replace(" ", "_")

    @property
    def _frame_key(self) -> str:
        return f"section_{self._slug}"

    @property
    def _handler_key(self) -> str:
        return f"{self._slug}_click"

    @property
    def _editing_state_key(self) -> str:
        return f"section_{self._slug}_editing"

    @property
    def editing(self) -> bool:
        return bool(st.session_state.get(self._editing_state_key, False))

    @editing.setter
    def editing(self, value: bool) -> None:
        st.session_state[self._editing_state_key] = value
        st.session_state.simulation_running = False
        st.session_state.result = None

    def on_click(self) -> None:
        self.editing = not self.editing

    def _handle_panel_click(self) -> None:
        self.on_click()

    def render(self) -> tuple[DeltaGenerator, DeltaGenerator]:
        left, right = super().render()
        with right:
            mode_class = (
                "fp-section-panel-edit"
                if self.editing
                else "fp-section-panel-readonly"
            )
            st.markdown(
                f'<span class="{mode_class}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )

            self._render_inside_panel()

            ClickPanelRegistry.register_handler(
                self._handler_key,
                self._handle_panel_click,
            )
            click_panel(
                panel_key=self._content_container_key,
                handler_key=self._handler_key,
            )
            return left, right

    @classmethod
    def install_click_handlers(cls) -> None:
        ClickPanelRegistry.install_handlers()

    def _render_inside_panel(self) -> None:
        hc = st.container(
            horizontal=not self.editing,
            vertical_alignment="center",
            gap="small",
            horizontal_alignment="right",
            key=f"{self._slug}_header",
        )
        with hc:
            if self.editing:
                self.edit_form()
                st.button(
                    self.done_button_text,
                    key=f"{self._slug}_done",
                    on_click=self.on_click,
                    help="Done editing this section",
                )
            else:
                self.readonly_form()
                st.button(
                    self.edit_button_text,
                    key=f"{self._slug}_edit",
                    on_click=self.on_click,
                    help="Edit the content of this section",
                )
