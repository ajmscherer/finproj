# finproj - reusable tour predicates
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from model.state import TourState

Predicate = Callable[[TourState], bool]


@dataclass(frozen=True)
class Condition:
    name: str
    pred: Predicate

    def __call__(self, state: TourState) -> bool:
        return self.pred(state)

    def __and__(self, other: Condition) -> Condition:
        return Condition(
            f"({self.name} AND {other.name})",
            lambda state, left=self, right=other: left(state) and right(state),
        )

    def __or__(self, other: Condition) -> Condition:
        return Condition(
            f"({self.name} OR {other.name})",
            lambda state, left=self, right=other: left(state) or right(state),
        )


goal_is_other = Condition("goal_is_other", lambda state: state.goal.kind == "other")
goal_is_retire_when = Condition(
    "goal_is_retire_when", lambda state: state.goal.kind == "retire_when"
)
goal_is_save_for_income = Condition(
    "goal_is_save_for_income", lambda state: state.goal.kind == "save_for_income"
)
