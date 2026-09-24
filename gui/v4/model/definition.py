# finproj - id-addressable step catalog
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from model.step import Step


class TourDefinition:
    def __init__(self, steps: list[Step], start: str) -> None:
        self.start = start
        self.steps = {step.id: step for step in steps}
        if len(self.steps) != len(steps):
            raise ValueError("duplicate step ids")
        if start not in self.steps:
            raise ValueError(f"start step {start!r} is not in the catalog")

    def get(self, step_id: str) -> Step:
        try:
            return self.steps[step_id]
        except KeyError as exc:
            raise KeyError(f"unknown step {step_id!r}") from exc
