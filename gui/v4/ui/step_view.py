# finproj - render the runner's current step. Does not choose the next step.
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import streamlit as st
from content.verbiage import Language, Verbiage
from model.runner import TourRunner
from model.step import FieldSpec
from ui.widgets import FieldWidget

BUTTON_VERBIAGE: dict[str,  Verbiage] = {
    "previous": Verbiage("Previous[en]|Anterior[es]|Précédent[fr]|Vorheriger[de]|Precedente[it]|前へ[ja]|Anterior[pt]|Предыдущий[ru]|上一步[zh]"),
    "back": Verbiage("Back[en]|Atrás[es]|Retour[fr]|Zurück[de]|Indietro[it]|戻る[ja]|Voltar[pt]|Назад[ru]|返回[zh]"),
    "next": Verbiage("Next[en]|Siguiente[es]|Suivant[fr]|Weiter[de]|Avanti[it]|次へ[ja]|Seguinte[pt]|Далее[ru]|下一步[zh]"),
    "continue": Verbiage("Continue[en]|Continuar[es]|Continuer[fr]|Fortfahren[de]|Continua[it]|続ける[ja]|Continuar[pt]|Продолжить[ru]|继续[zh]"),
    "done": Verbiage("Tour complete.[en]|Recorrido terminado.[es]|Parcours terminé.[fr]|Rundgang abgeschlossen.[de]|Percorso completato.[it]|案内は終わりです。[ja]|Percurso concluído.[pt]|Обход завершён.[ru]|引导已完成。[zh]"),
}

CLEAR_WIDGETS = False


def _button_label(key: str, language: Language) -> str:
    return BUTTON_VERBIAGE[key].to(language)


class StepView:
    def __init__(self, runner: TourRunner) -> None:
        self.runner: TourRunner = runner

    def _cursor_key(self) -> str:
        step = self.runner.current()
        step_id = step.id if step else "none"
        return f"v4_field_i_{step_id}"

    def _draft_answers(self) -> dict[str, object]:
        step = self.runner.current()
        if step is None:
            return {}
        answers: dict[str, object] = {}
        for spec in step.fields:
            widget = FieldWidget(spec)
            if widget.key() in st.session_state:
                answers[spec.path] = widget.read()
        return answers

    def _visible(self) -> list[FieldSpec]:
        """Return the list of fields that are visible for the current step."""
        step = self.runner.current()
        if step is None:
            return []
        state = self.runner.preview(self._draft_answers())
        return step.visible_fields(state)

    def render(self, language: Language) -> None:
        step = self.runner.current()
        if step is None:
            st.success(_button_label("done", language))
            return

        # timeline
        self._timeline(language)

        # visible fields
        visible = self._visible()
        index = int(st.session_state.get(self._cursor_key(), 0))
        if visible:
            index = max(0, min(index, len(visible) - 1))
        else:
            index = 0
        st.session_state[self._cursor_key()] = index

        with st.container(border=False):
            #st.markdown(f"### {step.title.to(language)}")
            st.caption(f"{step.prompt.to(language)}")
            if not visible:
                self._nav(index, 0, language)
                return
            preview = self.runner.preview(self._draft_answers())
            for i, spec in enumerate(visible):
                if i > index:
                    break
                widget = FieldWidget(spec)
                widget.seed(preview)

                with st.container(border=True):
                    widget.render(language)

            # navigation buttons
            self._nav(index, len(visible), language)
            
        self._debug()
        
    def _timeline(self, language: Language) -> None:
        ids = [
            step_id
            for step_id in (*self.runner.history, self.runner.current_id)
            if step_id
        ]
        if not ids:
            return
        with st.container(border=False, horizontal=True):
            for step_id in ids:
                if st.button(
                    self.runner.definition.get(step_id).title.to(language),
                    key=f"v4_tl_{step_id}_{len(self.runner.history)}",
                    disabled=False,
                    #width=100,
                    type="primary"
                    if step_id == self.runner.current_id
                    else "secondary",
                ) and step_id != self.runner.current_id:
                    self.runner.go_to(step_id, self._draft_answers())
                    self._clear_widgets(CLEAR_WIDGETS)
                    st.session_state[f"v4_field_i_{step_id}"] = 0
                    st.rerun()
    
    def _debug(self) -> None:
        st.divider()
        st.markdown("### Debug")
        #st.write(self._draft_answers())
        st.write(self.runner.preview(self._draft_answers()))

    def _clear_widgets(self, clear:bool=True) -> None:
        '''
        Clear all widgets from the session state.
        '''
        if not clear:
            return
        for key in list(st.session_state.keys()):
            if str(key).startswith("v4w_"):
                del st.session_state[key]

    def _nav(self, index: int, count: int, language: Language) -> None:
        button_width = 150
        with st.container(border=False, horizontal=True, width="stretch", horizontal_alignment="right"):
            if (index > 0 or self.runner.history) and st.button(
                _button_label("previous", language), width=button_width, key="v4_prev"
            ):
                if index > 0:
                    st.session_state[self._cursor_key()] = index - 1
                else:
                    self.runner.retreat(self._draft_answers())
                    self._clear_widgets(CLEAR_WIDGETS)
                    step = self.runner.current()
                    visible = step.visible_fields(self.runner.state) if step else []
                    st.session_state[self._cursor_key()] = max(0, len(visible) - 1)
                st.rerun()

            if st.button(  # noqa: SIM102
                    _button_label("next", language),
                    type="primary",
                    width=button_width,
                    key="v4_next",
                ):
                if count and index < count - 1:
                    st.session_state[self._cursor_key()] = index + 1
                    st.rerun()
                else:
                    step = self.runner.current()
                    answers: dict[str, object] = {}
                    if step is not None:
                        state = self.runner.preview(self._draft_answers())
                        for spec in step.visible_fields(state):
                            answers[spec.path] = FieldWidget(spec).read()
                    self.runner.apply(answers)
                    self._clear_widgets(CLEAR_WIDGETS)
                    arrived = self.runner.current()
                    if arrived is not None:
                        st.session_state.pop(f"v4_field_i_{arrived.id}", None)
                    st.rerun()

            '''
            if count and index < count - 1:
                if st.button(
                    _button_label("next", language),
                    type="primary",
                    width=button_width,
                    key="v4_next",
                ):
                    st.session_state[self._cursor_key()] = index + 1
                    st.rerun()
            elif st.button(
                _button_label("continue", language),
                type="primary",
                width=button_width,
                key="v4_continue",
            ):
                step = self.runner.current()
                answers: dict[str, object] = {}
                if step is not None:
                    state = self.runner.preview(self._draft_answers())
                    for spec in step.visible_fields(state):
                        answers[spec.path] = FieldWidget(spec).read()
                self.runner.apply(answers)
                self._clear_widgets(CLEAR_WIDGETS)
                arrived = self.runner.current()
                if arrived is not None:
                    st.session_state.pop(f"v4_field_i_{arrived.id}", None)
                st.rerun()
            '''