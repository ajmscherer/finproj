# finproj - dotted get/set on TourState
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from typing import Any


def get_path(obj: Any, path: str) -> Any:
    '''Get the value of a path in an object.'''
    current = obj
    for part in path.split("."):
        current = getattr(current, part)
    return current


def set_path(obj: Any, path: str, value: Any) -> None:
    '''Set the value of a path in an object.'''
    parts = path.split(".")
    current = obj
    for part in parts[:-1]:
        current = getattr(current, part)
    setattr(current, parts[-1], value)
