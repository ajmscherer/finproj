# finproj - browser cookie for the guest or signed-in session
# Copyright (C) 2025-2026 Alex Scherer

"""Persist the hosted-site token in a cookie.

Streamlit can read cookies on the next request. It has no built-in way to set
one, so a small component writes ``finproj_id``.
"""

from __future__ import annotations

import streamlit as st

_COMPONENT = None

_JS = """
export default function (component) {
  const { data, parentElement, setStateValue } = component
  // Streamlit mounts this inside a shadow root, which has no dataset.
  const host = parentElement && parentElement.dataset
    ? parentElement
    : parentElement && parentElement.host
  if (!host || !host.dataset) return
  if (host.dataset.finprojTokenReady === "1") return
  const name = "finproj_id"
  const wanted = (data && data.token) || ""
  const parts = document.cookie ? document.cookie.split("; ") : []
  let current = ""
  for (const part of parts) {
    if (part.startsWith(name + "=")) {
      current = decodeURIComponent(part.slice(name.length + 1))
      break
    }
  }
  if (wanted && wanted !== current) {
    const secure = location.protocol === "https:" ? "; Secure" : ""
    document.cookie = name + "=" + encodeURIComponent(wanted)
      + "; Path=/; Max-Age=31536000; SameSite=Lax" + secure
    current = wanted
  }
  host.dataset.finprojTokenReady = "1"
  setStateValue("token", current || wanted)
}
"""


def _component():
    global _COMPONENT
    if _COMPONENT is None:
        _COMPONENT = st.components.v2.component(
            "finproj_browser_token",
            html="<div></div>",
            js=_JS,
        )
    return _COMPONENT


def sync_browser_token(token: str) -> None:
    """Ask the browser to keep this guest or session token."""
    _component()(
        key="finproj_browser_token",
        data={"token": token},
        height=0,
        on_token_change=lambda: None,
    )
