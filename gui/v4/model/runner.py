# finproj - tour cursor. No financial rules live here.
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

import copy
from typing import Any

from model.definition import TourDefinition
from model.paths import get_path, set_path
from model.state import TourState
from model.step import Step


def merge_answers(state: TourState, step: Step, answers: dict[str, Any]) -> TourState:
    """Copy state, write this step's answers, then blank dependents that were not resubmitted."""
    new_state = copy.deepcopy(state)
    changed = False
    for spec in step.fields:
        if spec.path not in answers:
            continue
        if get_path(state, spec.path) != answers[spec.path]:
            changed = True
        set_path(new_state, spec.path, answers[spec.path])
    if changed and step.clears_on_change:
        for path in step.clears_on_change:
            if path not in answers:
                set_path(new_state, path, None)
    return new_state


class TourRunner:
    def __init__(
        self, definition: TourDefinition, state: TourState | None = None
    ) -> None:
        self.definition = definition
        self.state = state or TourState()
        self.current_id: str | None = definition.start
        self.history: list[str] = []
        self.snapshots: list[TourState] = []

    def current(self) -> Step | None:
        if self.current_id is None:
            return None
        return self.definition.get(self.current_id)

    def preview(self, answers: dict[str, Any]) -> TourState:
        step = self.current()
        if step is None:
            return self.state
        return merge_answers(self.state, step, answers)

    def apply(self, answers: dict[str, Any]) -> Step | None:
        step = self.current()
        if step is None:
            return None
        new_state = merge_answers(self.state, step, answers)
        self.snapshots.append(self.state)
        self.history.append(self.current_id or "")
        self.state = new_state
        nxt = step.resolve_next(self.state)
        while nxt is not None and not self.definition.get(nxt).is_visible(self.state):
            nxt = self.definition.get(nxt).resolve_next(self.state)
        self.current_id = nxt
        return self.current()

    def back(self) -> Step | None:
        if not self.history:
            return self.current()
        self.current_id = self.history.pop()
        self.state = self.snapshots.pop()
        return self.current()

    def retreat(self, answers: dict[str, Any] | None = None) -> Step | None:
        """Move to the previous step and keep answers from the step being left."""
        leaving = self.current()
        if leaving is not None and answers:
            self.state = merge_answers(self.state, leaving, answers)
        if not self.history:
            return self.current()
        self.current_id = self.history.pop()
        if self.snapshots:
            self.snapshots.pop()
        return self.current()

    def go_to(self, step_id: str, answers: dict[str, Any] | None = None) -> Step | None:
        """Move to a step already on the timeline, keeping answers from the step left."""
        leaving = self.current()
        if leaving is not None and answers:
            self.state = merge_answers(self.state, leaving, answers)
        if step_id == self.current_id or step_id not in self.history:
            return self.current()
        while self.history and self.current_id != step_id:
            self.current_id = self.history.pop()
            if self.snapshots:
                self.snapshots.pop()
        return self.current()
