# finproj - sequential question guide for GUI v2
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import streamlit as st
import streamlit.components.v1 as components

_MEDIA_DIR = Path(__file__).resolve().parent / "media"

# Light yellow highlight for the question that currently has focus.
_ACTIVE_CSS = """
<style>
div[class*="st-key-v2g_on_"],
div[class*="st-key-v2g_on_"] [data-testid="stVerticalBlockBorderWrapper"],
div[class*="st-key-v2g_on_"] [data-testid="stVerticalBlock"] {
    background-color: #fff9c4 !important;
}
div[class*="st-key-v2g_on_"] [data-testid="stVerticalBlockBorderWrapper"] {
    border: 2px solid #e6c229 !important;
    border-radius: 0.6rem !important;
}
div[class*="st-key-v2g_off_"] [data-testid="stVerticalBlockBorderWrapper"] {
    cursor: pointer;
}
div[class*="st-key-v2g_pick_"] {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    clip: rect(0 0 0 0) !important;
    clip-path: inset(50%) !important;
    border: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}
div[class*="st-key-v2g_on_"] p,
div[class*="st-key-v2g_off_"] p {
    text-align: left !important;
}
</style>
"""

NavFn = Callable[[], None]
WidgetFn = Callable[[], None]


@dataclass
class GuidedItem:
    """One prompt inside a wizard step."""

    item_id: str
    title: str
    help_html: str
    widget: WidgetFn
    focus_key: str
    video: str | None = None


@dataclass
class GuidedTour:
    """Reveal one question at a time, focus it, and optionally play an explainer video.

    Register videos in one place::

        GuidedTour.VIDEOS["wealth.capital"] = "capital.mp4"  # file in gui/v2/media/
        GuidedTour.VIDEOS["wealth.capital"] = "https://…"     # or a URL

    Or pass ``video=`` on ``add()``. Missing videos are skipped (hook stays).
    """

    VIDEOS: ClassVar[dict[str, str]] = {}

    step_id: str
    items: list[GuidedItem] = field(default_factory=list)

    def add(
        self,
        item_id: str,
        title: str,
        help_html: str,
        widget: WidgetFn,
        *,
        focus_key: str,
        video: str | None = None,
    ) -> GuidedTour:
        self.items.append(
            GuidedItem(item_id, title, help_html, widget, focus_key, video)
        )
        return self

    def _index_key(self) -> str:
        return f"v2_guide_i_{self.step_id}"

    def _max_key(self) -> str:
        return f"v2_guide_max_{self.step_id}"

    def index(self) -> int:
        if not self.items:
            return 0
        return max(0, min(int(st.session_state.get(self._index_key(), 0)), len(self.items) - 1))

    def revealed(self) -> int:
        if not self.items:
            return 0
        return max(self.index(), min(int(st.session_state.get(self._max_key(), 0)), len(self.items) - 1))

    def _set_index(self, value: int) -> None:
        idx = max(0, min(int(value), len(self.items) - 1))
        st.session_state[self._index_key()] = idx
        st.session_state[self._max_key()] = max(
            idx, int(st.session_state.get(self._max_key(), 0))
        )

    @classmethod
    def resolve_video(cls, item_id: str, explicit: str | None = None) -> str | None:
        raw = explicit or cls.VIDEOS.get(item_id)
        if not raw:
            return None
        path = Path(raw)
        if path.is_file():
            return str(path)
        local = _MEDIA_DIR / raw
        if local.is_file():
            return str(local)
        if raw.startswith(("http://", "https://", "/")):
            return raw
        return None

    def render(
        self,
        *,
        on_back_step: NavFn | None = None,
        on_next_step: NavFn | None = None,
        after_last: WidgetFn | None = None,
    ) -> None:
        if not self.items:
            return
        st.markdown(_ACTIVE_CSS, unsafe_allow_html=True)
        current = self.index()
        shown = self.revealed()
        total = len(self.items)

        for i, item in enumerate(self.items):
            if i > shown:
                break
            self._render_item(item, index=i, active=(i == current))

        self._render_pick_buttons(shown)

        if after_last is not None and current >= total - 1:
            after_last()

        self._render_item_nav(current, total, on_back_step, on_next_step)
        self._install_click_to_focus(shown, current)
        focus_token = f"{self.step_id}:{current}"
        if st.session_state.get("v2_guide_last_focus") != focus_token:
            st.session_state.v2_guide_last_focus = focus_token
            self._focus(self.items[current].focus_key)

    def _activate(self, index: int) -> None:
        self._set_index(index)
        st.session_state.v2_guide_last_focus = None

    def _render_item(self, item: GuidedItem, *, index: int, active: bool) -> None:
        slug = item.item_id.replace(".", "_")
        key = f"v2g_on_{self.step_id}_{slug}" if active else f"v2g_off_{self.step_id}_{slug}"
        with st.container(border=True, key=key):
            st.markdown(
                f'<div data-fp2-q="{index}" data-fp2-step="{self.step_id}"></div>',
                unsafe_allow_html=True,
            )
            video = self.resolve_video(item.item_id, item.video)
            if video:
                st.video(video)
            st.markdown(f"**{item.title}**")
            if item.help_html:
                st.markdown(f'<p class="fp2-help">{item.help_html}</p>', unsafe_allow_html=True)
            item.widget()

    def _render_item_nav(
        self,
        current: int,
        total: int,
        on_back_step: NavFn | None,
        on_next_step: NavFn | None,
    ) -> None:
        back_col, next_col = st.columns(2)
        with back_col:
            if current > 0:
                if st.button("Previous question", width="stretch", key=f"v2g_{self.step_id}_prev"):
                    self._set_index(current - 1)
                    st.rerun()
            elif on_back_step is not None:
                if st.button("Back", width="stretch", key=f"v2g_{self.step_id}_back_step"):
                    on_back_step()
        with next_col:
            if current < total - 1:
                if st.button(
                    "Next question",
                    type="primary",
                    width="stretch",
                    key=f"v2g_{self.step_id}_next",
                ):
                    self._set_index(current + 1)
                    st.rerun()
            elif on_next_step is not None:
                if st.button(
                    "Continue",
                    type="primary",
                    width="stretch",
                    key=f"v2g_{self.step_id}_next_step",
                ):
                    on_next_step()

    def _render_pick_buttons(self, shown: int) -> None:
        """Off-screen buttons so a click inside an earlier card can activate it."""
        for i in range(shown + 1):
            st.button(
                f"pick-{i}",
                key=f"v2g_pick_{self.step_id}_{i}",
                on_click=self._activate,
                args=(i,),
            )

    def _install_click_to_focus(self, shown: int, current: int) -> None:
        picks = [f"v2g_pick_{self.step_id}_{i}" for i in range(shown + 1)]
        components.html(
            f"""
            <script>
            (function () {{
              const picks = {json.dumps(picks)};
              const current = {int(current)};
              const parentDoc = (window.parent && window.parent.document) || document;

              function questionIndex(target) {{
                let n = target;
                while (n) {{
                  if (n.querySelectorAll) {{
                    const markers = n.querySelectorAll('[data-fp2-q]');
                    // Only the individual question card has exactly one marker.
                    // The step card contains several — ignore those or Continue
                    // would be treated as a click on question 1.
                    if (markers.length === 1 && n.contains(target)) {{
                      return parseInt(markers[0].getAttribute('data-fp2-q'), 10);
                    }}
                  }}
                  n = n.parentElement;
                }}
                return null;
              }}

              function clickPick(idx) {{
                const wrap = parentDoc.querySelector('.st-key-' + picks[idx]);
                const btn = wrap && wrap.querySelector('button');
                if (btn) btn.click();
              }}

              function handler(ev) {{
                if (!ev.target || !ev.target.closest) return;
                if (ev.target.closest('button')) return;
                const idx = questionIndex(ev.target);
                if (idx === null || idx === current || idx < 0 || idx >= picks.length) return;
                clickPick(idx);
              }}

              const flag = '__fp2GuidedTourClick';
              if (parentDoc[flag]) {{
                parentDoc.removeEventListener('mousedown', parentDoc[flag], true);
                parentDoc.removeEventListener('focusin', parentDoc[flag], true);
              }}
              parentDoc[flag] = handler;
              parentDoc.addEventListener('mousedown', handler, true);
              parentDoc.addEventListener('focusin', handler, true);
            }})();
            </script>
            """,
            height=0,
        )

    @staticmethod
    def _focus(widget_key: str) -> None:
        """Put a blinking caret in the active field (once per question change)."""
        components.html(
            f"""
            <script>
            (function () {{
              const key = {json.dumps(widget_key)};
              const docs = [];
              try {{ docs.push(document); }} catch (e) {{}}
              try {{ if (window.parent && window.parent.document) docs.push(window.parent.document); }} catch (e) {{}}

              function placeCaret(el) {{
                el.focus({{ preventScroll: false }});
                const val = el.value;
                if (typeof val === 'string' && el.setSelectionRange) {{
                  try {{
                    const n = val.length;
                    el.setSelectionRange(n, n);
                  }} catch (e) {{}}
                }}
              }}

              function tryFocus() {{
                for (const d of docs) {{
                  const root = d.querySelector('.st-key-' + key);
                  if (!root) continue;
                  const el = root.querySelector('input:not([type="hidden"]), textarea, select');
                  if (!el) continue;
                  placeCaret(el);
                  return true;
                }}
                return false;
              }}

              if (!tryFocus()) {{
                setTimeout(tryFocus, 50);
                setTimeout(tryFocus, 150);
                setTimeout(tryFocus, 350);
              }}
            }})();
            </script>
            """,
            height=0,
        )
