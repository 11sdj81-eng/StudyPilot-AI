"""Structured, evidence-first content objects for StudyPilot PDF 2.0.

These objects are deliberately factual containers. LLMs may rewrite prose
outside this module, but they must not invent concepts, source locations,
exam frequency, or past-paper evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class SourceRef:
    source_type: Literal["textbook", "ppt", "past_exam", "generated_variant", "unknown"]
    file_name: str
    page: str = ""
    year: str = ""
    question_no: str = ""
    note: str = ""
    confidence: float = 1.0

    def label(self) -> str:
        if self.source_type == "past_exam":
            parts = [self.year or self.file_name, self.question_no]
            return " ".join(p for p in parts if p) or "未找到高置信来源"
        loc = self.page or self.note
        return f"{self.file_name} {loc}".strip() or "未找到高置信来源"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MarginNote:
    type: Literal["source", "warning", "exam", "tip"]
    content: str
    source_ref: SourceRef | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.source_ref:
            data["source_ref"] = self.source_ref.to_dict()
        return data


@dataclass
class FormulaCard:
    formula_id: str
    concept_id: str
    title: str
    latex: str
    display_text: str
    conditions: str
    symbol_explanation: dict[str, str]
    source_refs: list[SourceRef]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "source_refs": [ref.to_dict() for ref in self.source_refs],
        }


@dataclass
class ConceptCard:
    concept_id: str
    title: str
    textbook_evidence: list[SourceRef]
    ppt_evidence: list[SourceRef]
    exam_evidence: list[SourceRef]
    explanation: str
    formulas: list[FormulaCard]
    difficulty: int
    exam_frequency: int
    mastery_level: str
    source_refs: list[SourceRef]
    why_important: str
    exam_usage: list[str]
    common_mistakes: list[str]
    recommended_priority: str
    margin_notes: list[MarginNote] = field(default_factory=list)

    def has_source(self) -> bool:
        return bool(self.textbook_evidence or self.ppt_evidence or self.exam_evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "textbook_evidence": [ref.to_dict() for ref in self.textbook_evidence],
            "ppt_evidence": [ref.to_dict() for ref in self.ppt_evidence],
            "exam_evidence": [ref.to_dict() for ref in self.exam_evidence],
            "formulas": [formula.to_dict() for formula in self.formulas],
            "source_refs": [ref.to_dict() for ref in self.source_refs],
            "margin_notes": [note.to_dict() for note in self.margin_notes],
        }


@dataclass
class ExampleCard:
    example_id: str
    concept_id: str
    source_type: Literal["textbook", "past_exam", "generated_variant"]
    problem: str
    solution_steps: list[str]
    standard_answer: str
    annotations: list[str]
    common_mistakes: list[str]
    source_refs: list[SourceRef]
    difficulty: int
    grading_points: list[str]
    question_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "source_refs": [ref.to_dict() for ref in self.source_refs],
        }


@dataclass
class ExamPatternCard:
    concept_id: str
    frequency: int
    avg_score: float
    question_types: list[str]
    common_contexts: list[str]
    past_exam_refs: list[SourceRef]
    recommended_priority: str
    how_tested: str
    common_traps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "past_exam_refs": [ref.to_dict() for ref in self.past_exam_refs],
        }


@dataclass
class LectureSection:
    section_id: str
    title: str
    concept: ConceptCard | None = None
    examples: list[ExampleCard] = field(default_factory=list)
    exam_pattern: ExamPatternCard | None = None
    margin_notes: list[MarginNote] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "concept": self.concept.to_dict() if self.concept else None,
            "examples": [example.to_dict() for example in self.examples],
            "exam_pattern": self.exam_pattern.to_dict() if self.exam_pattern else None,
            "margin_notes": [note.to_dict() for note in self.margin_notes],
        }


@dataclass
class LectureDocument:
    document_id: str
    pdf_type: Literal["Sprint", "Review", "PastPaper", "MockExam"]
    title: str
    subtitle: str
    sections: list[LectureSection]
    source_aligned: bool
    target_pages: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "pdf_type": self.pdf_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "sections": [section.to_dict() for section in self.sections],
            "source_aligned": self.source_aligned,
            "target_pages": self.target_pages,
            "metadata": self.metadata,
        }
