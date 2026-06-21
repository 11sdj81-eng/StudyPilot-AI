"""Central Formula Registry — prevents LLM-generated formulas from leaking into PDFs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from core.pdf_content_v2.formula_registry.formula_card import RegFormulaCard


class FormulaRegistry:
    """Single source of truth for all core course formulas.

    Rules:
        1. Only registered formulas may appear in final PDFs.
        2. LLM-generated formulas go to unverified_queue first.
        3. lookup() returns None for unregistered formulas.
    """

    def __init__(self):
        self._formulas: dict[str, RegFormulaCard] = {}
        self._unverified: list[dict[str, Any]] = []
        self._by_concept: dict[str, list[RegFormulaCard]] = defaultdict(list)
        self._by_course: dict[str, list[RegFormulaCard]] = defaultdict(list)

    def register(self, formula: RegFormulaCard) -> None:
        """Register a verified formula."""
        self._formulas[formula.formula_id] = formula
        self._by_concept[formula.concept_id].append(formula)
        self._by_course[formula.course_id].append(formula)

    def register_all(self, formulas: list[RegFormulaCard]) -> None:
        for f in formulas:
            self.register(f)

    def lookup(self, formula_id: str) -> RegFormulaCard | None:
        return self._formulas.get(formula_id)

    def by_concept(self, concept_id: str) -> list[RegFormulaCard]:
        return self._by_concept.get(concept_id, [])

    def by_course(self, course_id: str) -> list[RegFormulaCard]:
        return self._by_course.get(course_id, [])

    def all_formulas(self) -> list[RegFormulaCard]:
        return list(self._formulas.values())

    def get_expected_ids(self, course_id: str) -> list[str]:
        """Get all expected formula IDs for a course."""
        return [f.formula_id for f in self.by_course(course_id)]

    def submit_unverified(self, formula_dict: dict[str, Any]) -> None:
        """Submit an LLM-generated formula for review before registration."""
        self._unverified.append(formula_dict)

    def unverified_count(self) -> int:
        return len(self._unverified)

    def stats(self, course_id: str | None = None) -> dict:
        formulas = self.by_course(course_id) if course_id else self.all_formulas()
        levels = defaultdict(int)
        for f in formulas:
            levels[f.source_level] += 1
        return {
            "total_registered": len(formulas),
            "by_source_level": dict(levels),
            "unverified_queue": len(self._unverified),
        }
