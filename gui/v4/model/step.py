# finproj - one unit of the guided interview
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from model.conditions import Condition
from model.state import TourState

from gui.v4.content.verbiage import Verbiage

FieldKind = Literal["choice", "amount", "int", "text", "percent"]


@dataclass
class FieldSpec:
    path: str
    label: Verbiage
    kind: FieldKind
    required: bool = True
    choices: tuple[str, ...] | None = None
    choice_labels: dict[str, Verbiage] | None = None
    help: Verbiage | None = None
    min: float | None = None
    max: float | None = None
    video: str | None = None
    when: Condition | None = None

    def is_visible(self, state: TourState) -> bool:
        return self.when is None or self.when(state)


@dataclass
class Step:
    id: str
    title: Verbiage
    prompt: Verbiage
    fields: list[FieldSpec]
    when: Condition | None = None
    next_steps: list[tuple[Condition, str]] = field(default_factory=list)
    default_next: str | None = None
    clears_on_change: tuple[str, ...] = ()

    def is_visible(self, state: TourState) -> bool:
        return self.when is None or self.when(state)

    def visible_fields(self, state: TourState) -> list[FieldSpec]:
        return [spec for spec in self.fields if spec.is_visible(state)]

    def resolve_next(self, state: TourState) -> str | None:
        for cond, dest in self.next_steps:
            if cond(state):
                return dest
        return self.default_next
