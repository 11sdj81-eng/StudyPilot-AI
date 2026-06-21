"""BaseCoursePlugin — universal course interface. No hardcoded course names anywhere."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseCoursePlugin:
    """Every course MUST implement this interface. GenericCoursePlugin is the fallback.

    Rules:
        1. No code may check `if course_name == "概率论"`.
        2. All course behavior comes from plugin methods.
        3. Unknown courses use GenericCoursePlugin (never crash, never fallback to wrong course).
    """
    course_id: str
    course_name: str
    subject_type: str = "unknown"

    # ── Content extraction ──
    def extract_concepts(self, materials: dict | None = None) -> list[str]:
        return []

    def extract_formulas(self, materials: dict | None = None) -> list[str]:
        return []

    def extract_question_types(self, materials: dict | None = None) -> list[str]:
        return ["选择题", "填空题", "计算题", "综合题"]

    # ── Generation ──
    def generate_questions(self, concept_id: str, question_type: str,
                           count: int = 1, difficulty: str = "中等") -> list[dict]:
        return []

    def generate_figures(self, concept_id: str, figure_type: str) -> list[dict]:
        return []

    def build_concept_graph(self) -> dict:
        return {"concepts": [], "edges": []}

    # ── Validation ──
    def validate_content(self, content: dict) -> dict:
        return {"valid": True, "issues": []}

    def render_pdf_context(self, pdf_type: str, data: dict) -> dict:
        return {"title": "", "subtitle": "", "sections": []}

    # ── Course identity ──
    def forbidden_keywords(self) -> list[str]:
        """Keywords that MUST NOT appear in this course's PDFs."""
        return []

    def required_keywords(self) -> list[str]:
        """Keywords that SHOULD appear in this course's PDFs."""
        return []

    def concept_ids(self) -> list[str]:
        return []

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id, "course_name": self.course_name,
            "subject_type": self.subject_type,
            "concepts": len(self.concept_ids()),
        }
