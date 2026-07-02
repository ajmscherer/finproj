# finproj - parse and summarize Viva DSL programs for the GUI
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from dataclasses import dataclass

from viva_adapter import HAS_VIVA


@dataclass(frozen=True)
class VivaProgramSummary:
    lives: tuple[str, ...]
    events: tuple[str, ...]
    flows: tuple[str, ...]


def _format_viva_amount(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1e9:
        return f"{sign}{amount / 1e9:g}B"
    if amount >= 1e6:
        return f"{sign}{amount / 1e6:g}M"
    if amount >= 1e3:
        return f"{sign}{amount / 1e3:g}k"
    if value == int(value):
        return f"{sign}{int(amount)}"
    return f"{sign}{amount:g}"


def _format_viva_time_window(time_window: dict | None) -> str:
    if not time_window:
        return ""
    kind = time_window.get("kind")
    if kind == "absolute_year":
        return f"year {time_window['year']}"
    return str(time_window)


def _format_viva_probability(probability: dict | None) -> str:
    if not probability:
        return ""
    if probability.get("kind") == "simple":
        pct = probability["pct"]
        if pct == int(pct):
            return f"{int(pct)}% probability"
        return f"{pct:.1f}% probability"
    return str(probability)


def _compact_life(life) -> str:
    return f"{life.name} ({life.typ[0]}, {life.birth_year})"


def _compact_event(event) -> str:
    parts = [event.name]
    time_text = _format_viva_time_window(event.time_window)
    if time_text:
        parts.append(time_text.removeprefix("year "))
    prob_text = _format_viva_probability(event.probability)
    if prob_text:
        parts.append(prob_text.replace(" probability", ""))
    return ", ".join(parts)


def _compact_flow(flow) -> str:
    amount = _format_viva_amount(flow.amount)
    period = "/yr" if flow.period == "year" else ""
    modifier = flow.modifiers[0] if flow.modifiers else None
    suffix = ""
    if modifier:
        kind = modifier.get("kind")
        target = modifier.get("target")
        attr = modifier.get("attr")
        if kind == "upon":
            suffix = f" @{target}" + (f".{attr}" if attr else "")
        elif kind == "until":
            suffix = f" until {target}" + (f".{attr}" if attr else "")
        elif kind == "for" and modifier.get("years") is not None:
            suffix = f" for {modifier['years']}y"
    return f"{flow.name} {amount}{period}{suffix}"


def _summarize_viva_program(program) -> VivaProgramSummary:
    lives = tuple(_compact_life(life) for life in program.lives)
    events = tuple(_compact_event(event) for event in program.events)
    flows = tuple(_compact_flow(flow) for flow in program.flows)
    return VivaProgramSummary(lives=lives, events=tuple(events), flows=tuple(flows))


def format_viva_program_summary_lines(summary: VivaProgramSummary) -> list[str]:
    lines: list[str] = []
    header_parts: list[str] = []
    if summary.lives:
        header_parts.append(f"Lives: {', '.join(summary.lives)}")
    if summary.events:
        header_parts.append(f"Events: {', '.join(summary.events)}")
    if header_parts:
        lines.append(" · ".join(header_parts))
    if summary.flows:
        lines.append(f"Flows: {', '.join(summary.flows)}")
    if not lines:
        lines.append("Empty Viva program")
    return lines[:2]


def summarize_viva_source(source: str) -> VivaProgramSummary:
    if not HAS_VIVA:
        raise ImportError(
            "viva is not installed. Install GUI dependencies with "
            "pip install -r requirements-gui.txt"
        )
    from viva import parse

    return _summarize_viva_program(parse(source))


def try_summarize_viva_source(
    source: str,
) -> tuple[VivaProgramSummary | None, str | None]:
    if not HAS_VIVA:
        return None, "Viva is not installed."
    if not source.strip():
        return VivaProgramSummary(lives=(), events=(), flows=()), None
    try:
        return summarize_viva_source(source), None
    except Exception as exc:
        return None, str(exc)
