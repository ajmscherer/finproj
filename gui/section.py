# finproj - Section component for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import streamlit as st

from click_panel import ClickPanelRegistry, click_panel


@dataclass
class Section(ABC):
    title: str

    @property
    def _slug(self) -> str:
        return self.title.lower().replace(" ", "_")

    @property
    def _frame_key(self) -> str:
        return f"section_{self._slug}"

    @property
    def _panel_key(self) -> str:
        return f"{self._slug}_panel"

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

    def on_click(self) -> None:
        self.editing = not self.editing

    def _handle_panel_click(self) -> None:
        self.on_click()

    def render(self) -> None:
        self.frame = st.container(border=True, key=self._frame_key)
        with self.frame:
            self.left_column, self.right_column = st.columns(2)

            with self.left_column:
                st.write(self.title)

            with self.right_column:
                with st.container(border=True, key=self._panel_key):
                    if self.editing:
                        st.caption("Edit mode")
                        self.render_edit_form()
                    else:
                        st.caption("Readonly mode")
                        self.render_readonly_form()

                    ClickPanelRegistry.register_handler(
                        self._handler_key,
                        self._handle_panel_click,
                    )
                    click_panel(
                        panel_key=self._panel_key,
                        handler_key=self._handler_key,
                    )

    @classmethod
    def install_click_handlers(cls) -> None:
        ClickPanelRegistry.install_handlers()

    @abstractmethod
    def render_readonly_form(self) -> None:
        pass

    @abstractmethod
    def render_edit_form(self) -> None:
        pass


class Section1(Section):
    title: str = "Step 1"



    def render_readonly_form(self) -> None:
        st.write("Click the panel to enter edit mode.")

    def render_edit_form(self) -> None:
        st.write("Click the panel to return to read-only mode.")
