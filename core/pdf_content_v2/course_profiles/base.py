"""Base CourseProfile dataclass — the syllabus-level "what should be covered" spec."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpectedConcept:
    """A concept that the syllabus says must be covered."""
    name: str                    # Chinese name, e.g. "随机变量"
    english_key: str = ""        # Machine-readable key, e.g. "random_variable"
    priority: int = 3            # 1=low, 3=core, 5=critical
    depends_on: list[str] = field(default_factory=list)  # prerequisite concepts

    def to_dict(self) -> dict:
        return {"name": self.name, "english_key": self.english_key, "priority": self.priority, "depends_on": self.depends_on}


@dataclass
class ExpectedFormula:
    """A formula that the syllabus says must appear."""
    name: str                    # e.g. "CDF", "Binomial PMF"
    latex_hint: str = ""         # Key LaTeX fragment for matching
    display_hint: str = ""       # Key display-text fragment
    belongs_to: str = ""         # Which ExpectedConcept this formula belongs to

    def to_dict(self) -> dict:
        return {"name": self.name, "latex_hint": self.latex_hint, "display_hint": self.display_hint, "belongs_to": self.belongs_to}


@dataclass
class ExpectedQuestionType:
    """A question type that the exam MUST test."""
    name: str                    # e.g. "概率计算"
    typical_score_share: float = 0.0  # expected fraction of total score
    example_stem: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "typical_score_share": self.typical_score_share, "example_stem": self.example_stem}


@dataclass
class CourseProfile:
    """Syllabus-level specification of what a course chapter must cover.

    This is the "ground truth" that coverage validation checks against.
    Unlike ChapterProfile (which describes what seed data exists),
    CourseProfile describes what SHOULD exist according to the syllabus.
    """
    course_id: str
    course_name: str
    chapter_name: str
    subject_type: str  # math / engineering
    expected_concepts: list[ExpectedConcept] = field(default_factory=list)
    expected_formulas: list[ExpectedFormula] = field(default_factory=list)
    expected_question_types: list[ExpectedQuestionType] = field(default_factory=list)
    coverage_threshold: float = 0.95  # minimum acceptable coverage rate

    @property
    def concept_names(self) -> list[str]:
        return [c.name for c in self.expected_concepts]

    @property
    def formula_names(self) -> list[str]:
        return [f.name for f in self.expected_formulas]

    @property
    def question_type_names(self) -> list[str]:
        return [q.name for q in self.expected_question_types]

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "chapter_name": self.chapter_name,
            "subject_type": self.subject_type,
            "expected_concept_count": len(self.expected_concepts),
            "expected_formula_count": len(self.expected_formulas),
            "expected_question_type_count": len(self.expected_question_types),
            "coverage_threshold": self.coverage_threshold,
        }
