# finproj - Streamlit GUI v4 (guided interview)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content.tour import build_definition
from content.verbiage import LANGUAGE_NAMES, Language, Verbiage
from model.runner import TourRunner
from ui.step_view import StepView

_CAPTION=Verbiage("Guided interview. The projection engine is not called from this screen yet.[en]|Entrevista guiada. El motor de proyección aún no se llama desde esta pantalla.[es]|Entretien guidé. Le moteur de projection n’est pas encore appelé depuis cet écran.[fr]|Geführtes Gespräch. Die Projektionsengine wird von diesem Bildschirm noch nicht aufgerufen.[de]|Intervista guidata. Il motore di proiezione non è ancora chiamato da questa schermata.[it]|ガイド付きの質問です。この画面からはまだ試算エンジンを呼び出しません。[ja]|Entrevista guiada. O motor de projeção ainda não é chamado desta tela.[pt]|Пошаговое интервью. Движок проекции с этого экрана ещё не вызывается.[ru]|引导式访谈。此屏幕尚未调用预测引擎。[zh]")


def _runner() -> TourRunner:
    if "v4_runner" not in st.session_state:
        st.session_state.v4_runner = TourRunner(build_definition())
    return st.session_state.v4_runner


def _language() -> Language:
    st.session_state.setdefault("v4_language", "en")
    return st.session_state.v4_language


def _set_language(code: str) -> None:
    st.session_state.v4_language = code


def main() -> None:
    st.set_page_config(page_title="finproj", layout="centered")
    with st.container(horizontal=False):
    
        with st.container(horizontal=True, horizontal_alignment="right", gap=None):
            language = _language()
            if st.button(f"🌐 {language}", key="v4_language_toggle", help=f"{LANGUAGE_NAMES[language]}"):                
                for code, name in LANGUAGE_NAMES.items():
                    if code !=language:
                        st.button(code, key=f"v4_language_{code}", help=name, on_click=lambda c=code:_set_language(c))
                
        st.title("Serenity")
        st.caption(_CAPTION.to(language))
    StepView(_runner()).render(_language())


main()
