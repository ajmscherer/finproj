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
from click_panel import ClickPanelRegistry, bind_panel_click
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


@dataclass
class Section(SectionBaseLayout):
    title: str = "No Title"
    content_form: Callable[[], None] | None = None
    footer_form: Callable[[], None] | None = None
    panel_key: str | None = None

    @property
    def _content_container_key(self) -> str:
        if self.panel_key:
            return self.panel_key
        return f"{self._slug}_panel_v5"

    def _render_panel_body(self) -> None:
        if self.content_form:
            self.content_form()

    def render(self) -> None:
        """Render step label (fixed width) | title + bordered panel (stretch).

        Uses a horizontal container so the left rail is exactly
        ``left_column_width`` pixels and the right side fills remaining space.
        (``st.columns`` only supports relative weights, not fixed pixel widths.)
        """
        with st.container(
            horizontal=True,
            width="stretch",
            height="stretch",
            gap="small",
            # Center the short left label against the taller right column.
            vertical_alignment="center",
            key=f"section_{self._slug}_row_v5",
        ):
            with st.container(
                width=self.left_column_width,
                border=False,
                key=f"{self._slug}_left_col_v5",
                vertical_alignment="center",
                horizontal_alignment="center",
            ):
                st.markdown(
                    f'<p class="fp-section-title">{html.escape(self.name)}</p>',
                    unsafe_allow_html=True,
                )
            with st.container(
                width="stretch",
                border=False,
                key=f"{self._slug}_right_col_v5",
                gap="small",

            ):
                st.header(self.title)
                with st.container(
                    width="stretch",
                    border=True,
                    key=self._content_container_key,
                    gap="small",
                    vertical_alignment="top",
                ):
                    self._render_panel_body()
                if self.footer_form is not None:
                    self.footer_form()
        st.space()


@dataclass
class SectionContentEditable(Section):
    edit_form: Callable[[], None] = _need_to_be_implemented
    readonly_form: Callable[[], None] = _need_to_be_implemented
    done_button_text: str = "Done"
    edit_button_text: str = "Edit"
    on_enter_edit: Callable[[], None] | None = None
    on_exit_edit: Callable[[], None] | None = None

    @property
    def _slug(self) -> str:
        return self.name.lower().replace(" ", "_")

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
        was_editing = bool(st.session_state.get(self._editing_state_key, False))
        st.session_state[self._editing_state_key] = value
        if value and not was_editing:
            st.session_state.result = None

    def on_click(self) -> None:
        if st.session_state.get("simulation_running"):
            return
        if self.editing:
            if self.on_exit_edit is not None:
                self.on_exit_edit()
            self.editing = False
        else:
            if self.on_enter_edit is not None:
                self.on_enter_edit()
            self.editing = True

    def _render_panel_body(self) -> None:
        force_readonly = bool(st.session_state.get("simulation_running"))
        show_editing = self.editing and not force_readonly
        
        mode_class = (
            "fp-section-panel-edit" if show_editing else "fp-section-panel-readonly"
        )
        st.markdown(
            f'<span class="{mode_class}" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
           
        mode_button_key = self._render_inside_panel(show_editing=show_editing)
        ClickPanelRegistry.register_handler(self._handler_key, self.on_click)
        bind_panel_click(
            panel_key=self._content_container_key,
            trigger_key=mode_button_key,
        )

    @classmethod
    def install_click_handlers(cls) -> None:
        ClickPanelRegistry.install_handlers()

    def _render_inside_panel(self, *, show_editing: bool | None = None) -> str:
        if show_editing is None:
            show_editing = self.editing
        running = bool(st.session_state.get("simulation_running"))
        # Keep ONE stable body key for both modes so Streamlit does not tear
        # down / remount the whole panel when toggling edit (empty-frame source).
        body_key = f"{self._slug}_inner_v5"
        mode_key = f"{self._slug}_mode_btn_v5"
        mode_label = self.done_button_text if show_editing else self.edit_button_text
        mode_help = (
            "Done editing this section"
            if show_editing
            else "Edit the content of this section"
        )

        with st.container(
            key=body_key,
            gap="xxsmall",
            horizontal=True,
            border=False,
        ):
            
            if show_editing:
                self.edit_form()
            else:
                self.readonly_form()
            st.button(
                mode_label,
                key=mode_key,
                on_click=self.on_click,
                help=mode_help,
                disabled=running,
            )
        return mode_key
