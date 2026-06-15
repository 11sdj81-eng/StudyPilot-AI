"""Exam pattern objects for StudyPilot v4.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ExamPattern:
    pattern_id: str
    source_type: str
    source_label: str
    concept_ids: list[str]
    formula_ids: list[str]
    question_type: str
    difficulty: int
    score: int
    teacher_intent: str
    required_steps: list[str]
    common_traps: list[str]
    variation_methods: list[str]
    expected_solution_depth: str
    diagram_required: bool
    diagram_type: str
    sample_problem: str
    grading_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
