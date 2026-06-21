"""BaseCourseProfile — the single unified interface all validators depend on."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProfileSource(Enum):
    SEED_DATA = "seed_data"          # From golden_chapters JSON
    AUTO_EXTRACTED = "auto_extracted" # From uploaded files
    GENERIC = "generic"              # GenericCourseProfile fallback
    USER_CONFIRMED = "user_confirmed" # User manually confirmed


@dataclass
class BaseCourseProfile:
    """Unified course profile — the ONLY interface validators should use.

    Every validator calls `get_profile(course_id)` from the registry.
    If no explicit profile exists, GenericCourseProfile is returned.
    Validation is NEVER silently skipped.
    """
    course_id: str
    course_name: str
    subject_type: str = "unknown"  # math / engineering / humanities / language / unknown
    chapter_name: str = ""
    expected_concepts: list[str] = field(default_factory=list)
    expected_formulas: list[str] = field(default_factory=list)
    expected_question_types: list[str] = field(default_factory=list)
    exam_blueprint: dict | None = None  # ExamBlueprint-compatible dict
    teacher_style_rules: list[str] = field(default_factory=list)
    figure_rules: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    required_keywords: list[str] = field(default_factory=list)
    source: ProfileSource = ProfileSource.GENERIC
    confidence: float = 0.5
    coverage_threshold: float = 0.95  # minimum acceptable coverage rate for this course

    # ── Convenience ────────────────────────────────────────────────────

    @property
    def is_generic(self) -> bool:
        return self.source == ProfileSource.GENERIC

    @property
    def is_auto_extracted(self) -> bool:
        return self.source == ProfileSource.AUTO_EXTRACTED

    @property
    def needs_user_confirmation(self) -> bool:
        return self.confidence < 0.7

    @property
    def concept_count(self) -> int:
        return len(self.expected_concepts)

    @property
    def formula_count(self) -> int:
        return len(self.expected_formulas)

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id, "course_name": self.course_name,
            "subject_type": self.subject_type, "chapter_name": self.chapter_name,
            "expected_concepts": self.expected_concepts,
            "expected_formulas": self.expected_formulas,
            "expected_question_types": self.expected_question_types,
            "source": self.source.value, "confidence": self.confidence,
            "is_generic": self.is_generic,
            "needs_user_confirmation": self.needs_user_confirmation,
        }
