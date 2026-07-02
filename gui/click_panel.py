# finproj - Click-panel helper for the Streamlit GUI
# Copyright (C) 2025-2026 Alex Scherer
#
# Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
# Commercial licensing is also available; see LICENSE and COMMERCIAL-LICENSE.md.

from __future__ import annotations

import html
import json
from collections.abc import Callable
from typing import ClassVar

import streamlit as st


def _dispatch_click(handler_key: str) -> None:
    handler = ClickPanelRegistry._handlers.get(handler_key)
    if handler is not None:
        handler()


class ClickPanelRegistry:
    """Collect panel→trigger bindings for one app run, then install a single JS handler."""

    _bindings: ClassVar[list[tuple[str, str]]] = []
    _handlers: ClassVar[dict[str, Callable[[], None]]] = {}

    @classmethod
    def reset(cls) -> None:
        cls._bindings.clear()
        cls._handlers.clear()

    @classmethod
    def register_handler(cls, handler_key: str, handler: Callable[[], None]) -> None:
        cls._handlers[handler_key] = handler

    @classmethod
    def register(cls, *, panel_key: str, trigger_key: str) -> None:
        binding = (panel_key, trigger_key)
        if binding not in cls._bindings:
            cls._bindings.append(binding)

    @classmethod
    def install_handlers(cls) -> None:
        if not cls._bindings:
            return

        bindings_json = json.dumps(cls._bindings)
        hide_rules = "\n".join(
            f".st-key-{html.escape(trigger_key)} {{ display: none !important; }}"
            for _, trigger_key in cls._bindings
        )
        pointer_rules = "\n".join(
            f".st-key-{html.escape(panel_key)}, "
            f".st-key-{html.escape(panel_key)} "
            f"[data-testid='stVerticalBlockBorderWrapper'] {{ cursor: pointer; }}"
            for panel_key, _ in cls._bindings
        )
        st.html(
            f"""
            <style>
            {hide_rules}
            {pointer_rules}
            </style>
            <div style="display:none" aria-hidden="true">
            <script>
            (function () {{
                const doc = document;
                const bindings = {bindings_json};

                function isDataEntryTarget(target) {{
                    if (target.closest('input, textarea, select, label, [contenteditable="true"]')) {{
                        return true;
                    }}
                    if (target.closest(
                        '[data-baseweb="select"], [data-baseweb="input"], [data-baseweb="textarea"], '
                        + '[data-baseweb="radio"], [data-baseweb="checkbox"]'
                    )) {{
                        return true;
                    }}
                    if (target.closest(
                        '[data-baseweb="popover"], [role="listbox"], [role="option"], '
                        + '[role="radiogroup"], [role="radio"]'
                    )) {{
                        return true;
                    }}
                    if (target.closest('[data-testid="stNumberInput"] button')) {{
                        return true;
                    }}
                    const widgetRoots = [
                        'stTextInput', 'stTextArea', 'stNumberInput', 'stRadio', 'stCheckbox',
                        'stSelectbox', 'stMultiSelect', 'stSlider', 'stDateInput', 'stTimeInput',
                        'stColorPicker', 'stFileUploader', 'stToggle', 'stSegmentedControl',
                    ];
                    for (const testId of widgetRoots) {{
                        if (target.closest('[data-testid="' + testId + '"]')) {{
                            return true;
                        }}
                    }}
                    return false;
                }}

                function triggerButton(panel, triggerKey) {{
                    const wrap = panel.querySelector('.st-key-' + triggerKey);
                    if (!wrap) return null;
                    return wrap.querySelector('button');
                }}

                function handler(event) {{
                    if (event.target.closest('button')) return;
                    if (event.target.closest('[data-testid="stTooltipIcon"]')) return;
                    if (isDataEntryTarget(event.target)) return;

                    for (const [panelKey, triggerKey] of bindings) {{
                        const panel = event.target.closest('.st-key-' + panelKey);
                        if (!panel) continue;

                        const btn = triggerButton(panel, triggerKey);
                        if (btn && !btn.contains(event.target)) {{
                            btn.click();
                            return;
                        }}
                    }}
                }}

                if (window.__fpClickPanelHandler) {{
                    doc.removeEventListener('click', window.__fpClickPanelHandler);
                }}
                window.__fpClickPanelHandler = handler;
                doc.addEventListener('click', handler);
            }})();
            </script>
            </div>
            """,
            unsafe_allow_javascript=True,
            width=1,
        )


def click_panel(*, panel_key: str, handler_key: str) -> None:
    """Listen for clicks on a bordered panel and invoke its registered handler."""
    trigger_key = f"{handler_key}_trigger"

    st.button(
        " ",
        key=trigger_key,
        on_click=lambda hk=handler_key: _dispatch_click(hk),
        help="",
    )
    ClickPanelRegistry.register(panel_key=panel_key, trigger_key=trigger_key)
