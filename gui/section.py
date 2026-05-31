# finproj - Section component for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import streamlit as st


@dataclass
class Section(ABC):
    title: str
    editing: bool = False

    def render(self) -> None:
        self.frame = st.container(border=True, key="section_" + self.title)
        with self.frame:
            self.left_column, self.right_column = st.columns(2)

            with self.left_column:
                st.write(self.title)

            with self.right_column:
                if self.editing:
                    st.caption("Edit mode")
                    self.render_edit_form()
                else:
                    st.caption("Readonly mode")
                    self.render_readonly_form()

    @abstractmethod
    def render_readonly_form(self) -> None:
        pass

    @abstractmethod
    def render_edit_form(self) -> None:
        pass


class Section1(Section):
    title: str = "Step 1"

    def render_readonly_form(self) -> None:
        pass

    def render_edit_form(self) -> None:
        pass
