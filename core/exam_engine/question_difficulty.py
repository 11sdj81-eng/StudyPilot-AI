"""Difficulty scoring helpers for v4.1 questions."""

from __future__ import annotations

from core.exam_engine.exam_pattern import ExamPattern


def average_difficulty(patterns: list[ExamPattern]) -> float:
    return round(sum(p.difficulty for p in patterns) / max(1, len(patterns)), 2)


def has_level4_or_above(patterns: list[ExamPattern]) -> bool:
    return any(p.difficulty >= 4 for p in patterns)


def difficulty_summary(patterns: list[ExamPattern]) -> dict:
    counts: dict[str, int] = {}
    for pattern in patterns:
        key = f"level_{pattern.difficulty}"
        counts[key] = counts.get(key, 0) + 1
    return {"average": average_difficulty(patterns), "has_level4_or_above": has_level4_or_above(patterns), "counts": counts}
