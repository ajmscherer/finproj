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


def main() -> None:
    st.set_page_config(page_title="finproj", layout="centered")
    language = _language()
    title_col, lang_col = st.columns([4, 1], vertical_alignment="center")
    with title_col:
        st.title("Serenity")
        st.caption(_CAPTION.to(language))
    with lang_col:
        st.selectbox(
            "Language",
            options=list(LANGUAGE_NAMES),
            format_func=lambda code: LANGUAGE_NAMES[code],
            key="v4_language",
            label_visibility="collapsed",
        )
    StepView(_runner()).render(st.session_state.v4_language)


main()
