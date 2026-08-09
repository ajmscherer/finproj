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
from click_panel import ClickPanelRegistry, click_panel
from streamlit.delta_generator import DeltaGenerator
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
    # Optional lifecycle hooks (run from button/panel callbacks, before widgets render).
    on_enter_edit: Callable[[], None] | None = None
    on_exit_edit: Callable[[], None] | None = None

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
        was_editing = bool(st.session_state.get(self._editing_state_key, False))
        st.session_state[self._editing_state_key] = value
        # Only invalidate results when *entering* edit (assumptions may change).
        # Never clear simulation_running here — the run flow owns that flag.
        if value and not was_editing:
            st.session_state.result = None

    def on_click(self) -> None:
        """Toggle edit mode, running enter/exit hooks around the transition.

        Callbacks run before the script body, so widget-bound session keys from
        the previous run are still available for commit on exit, and safe to
        force-seed on enter (widgets have not been created yet this run).
        """
        # Ignore panel/edit clicks while a simulation is in progress.
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

    def _handle_panel_click(self) -> None:
        self.on_click()

    def render(self) -> tuple[DeltaGenerator, DeltaGenerator]:
        left, right = super().render()
        # While a simulation runs, force readonly *content* but keep the same
        # widget skeleton (edit button + click-panel trigger) so Streamlit does
        # not leave empty frames where removed elements used to be.
        force_readonly = bool(st.session_state.get("simulation_running"))
        show_editing = self.editing and not force_readonly
        with right:
            mode_class = (
                "fp-section-panel-edit"
                if show_editing
                else "fp-section-panel-readonly"
            )
            st.markdown(
                f'<span class="{mode_class}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )

            self._render_inside_panel(show_editing=show_editing)

            # Always register click panel (handler no-ops while running).
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

    def _render_inside_panel(self, *, show_editing: bool | None = None) -> None:
        if show_editing is None:
            show_editing = self.editing
        running = bool(st.session_state.get("simulation_running"))
        # Always stack form content vertically. Wrapping the readonly form in a
        # horizontal container next to Edit produced tall empty regions and made
        # residual click-trigger buttons look like empty frames.
        # Distinct keys keep edit vs readonly element trees from being reused.
        body_key = (
            f"{self._slug}_body_edit" if show_editing else f"{self._slug}_body_ro"
        )
        with st.container(key=body_key, gap="small"):
            if show_editing:
                self.edit_form()
            else:
                self.readonly_form()

        # Mode button is always mounted (stable tree) and hidden via theme CSS
        # unless section_mode_buttons_visible is true. Panel click uses click_panel.
        if show_editing:
            st.button(
                self.done_button_text,
                key=f"{self._slug}_done",
                on_click=self.on_click,
                help="Done editing this section",
                disabled=running,
            )
        else:
            st.button(
                self.edit_button_text,
                key=f"{self._slug}_edit",
                on_click=self.on_click,
                help="Edit the content of this section",
                disabled=running,
            )
