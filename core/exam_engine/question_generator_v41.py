"""Deterministic v4.1 question generation from exam patterns."""

from __future__ import annotations

from core.exam_engine.exam_pattern import ExamPattern


def question_from_pattern(pattern: ExamPattern, number: int, points: int | None = None) -> dict:
    return {
        "no": number,
        "pattern_id": pattern.pattern_id,
        "kind": pattern.question_type,
        "points": points if points is not None else pattern.score,
        "difficulty": pattern.difficulty,
        "question": pattern.sample_problem,
        "teacher_intent": pattern.teacher_intent,
        "required_steps": pattern.required_steps,
        "common_traps": pattern.common_traps,
        "variation_methods": pattern.variation_methods,
        "grading_points": pattern.grading_points,
        "diagram_type": pattern.diagram_type,
        "formula_ids": pattern.formula_ids,
        "concept_ids": pattern.concept_ids,
        "expected_solution_depth": pattern.expected_solution_depth,
    }
