"""Question quality checks for v4.1."""

from __future__ import annotations

from core.exam_engine.exam_pattern import ExamPattern
from core.exam_engine.question_difficulty import average_difficulty, has_level4_or_above


def inspect_question_set(patterns: list[ExamPattern]) -> dict:
    return {
        "question_count": len(patterns),
        "average_difficulty": average_difficulty(patterns),
        "has_level4_or_above": has_level4_or_above(patterns),
        "level4_count": sum(1 for p in patterns if p.difficulty >= 4),
        "diagram_required_count": sum(1 for p in patterns if p.diagram_required),
    }
