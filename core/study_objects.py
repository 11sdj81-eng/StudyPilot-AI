"""Structured StudyPilot v2.0 learning objects.

PDFs should be rendered from these objects, not from free-form LLM Markdown.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FormulaCard:
    id: str
    concept_id: str
    latex: str
    display_text: str
    symbol_explanation: dict[str, str]
    conditions: str
    forbidden_alias: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    display_title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConceptCard:
    id: str
    name: str
    subject_type: str
    chapter: str
    textbook_section: str
    definition: str
    plain_explanation: str
    why_important: str
    prerequisites: list[str] = field(default_factory=list)
    related_formulas: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    exam_usage: list[str] = field(default_factory=list)
    display_title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiagramBlock:
    id: str
    diagram_type: str
    linked_concept_ids: list[str]
    required_labels: list[str]
    render_method: str
    path: str
    description: str
    valid_for_question_types: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SolutionBlock:
    steps: list[str]
    answer: str
    rubric: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExampleCard:
    id: str
    source_type: str
    source_ref: str
    concept_ids: list[str]
    question_type: str
    difficulty: float
    question: str
    diagram_required: bool
    diagram_type: str
    solution: SolutionBlock
    variants: list[str] = field(default_factory=list)
    required_formulas: list[str] = field(default_factory=list)
    display_title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionCard:
    id: str
    question: str
    concept_ids: list[str]
    formula_ids: list[str]
    source_basis: str
    difficulty: float
    question_type: str
    score: int
    chapter: str
    diagram_required: bool
    diagram_type: str
    diagram_id: str
    solution: SolutionBlock
    metadata: dict[str, Any]
    options: list[str] = field(default_factory=list)
    display_title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SprintCard:
    concept_id: str
    definition: str
    formula_ids: list[str]
    symbol_notes: dict[str, str]
    exam_usage: list[str]
    quick_question_id: str
    quick_answer: str
    quick_steps: list[str]
    common_mistakes: list[str]
    review_location: str
    ten_second_reminder: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PastPaperCase:
    question: QuestionCard
    source_reliability: str
    textbook_location: str
    variant_question: str
    takeaway: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Section:
    id: str
    title: str
    blocks: list[Any] = field(default_factory=list)
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocks"] = [b.to_dict() if hasattr(b, "to_dict") else b for b in self.blocks]
        return data


@dataclass
class ExamPaper:
    title: str
    instructions: list[str]
    questions: list[QuestionCard]
    source_basis: str
    score_total: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StudyDocument:
    id: str
    title: str
    course: dict[str, Any]
    subject_type: str
    task_type: str
    sections: list[Section]
    formulas: dict[str, FormulaCard] = field(default_factory=dict)
    concepts: dict[str, ConceptCard] = field(default_factory=dict)
    examples: dict[str, ExampleCard] = field(default_factory=dict)
    diagrams: dict[str, DiagramBlock] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "course": self.course,
            "subject_type": self.subject_type,
            "task_type": self.task_type,
            "sections": [section.to_dict() for section in self.sections],
            "formulas": {k: v.to_dict() for k, v in self.formulas.items()},
            "concepts": {k: v.to_dict() for k, v in self.concepts.items()},
            "examples": {k: v.to_dict() for k, v in self.examples.items()},
            "diagrams": {k: v.to_dict() for k, v in self.diagrams.items()},
            "metadata": self.metadata,
        }
