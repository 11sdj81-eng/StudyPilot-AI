"""ExamImportanceScorer — scores concept exam importance 0-100 for PDF 5.0.

Course-agnostic: driven by ExamPatternLibrary data, not hardcoded.
Displays as star ratings: ★★★★★ (90+), ★★★★ (70-89), ★★★ (50-69), ★★ (30-49), ★ (0-29).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExamImportanceResult:
    concept_id: str
    score: int = 0  # 0-100
    stars: str = ""
    factors: dict = field(default_factory=dict)


class ExamImportanceScorer:
    """Scores each concept's exam importance based on evidence.

    Factors:
        - exam_frequency: raw count of past exam appearances
        - pattern_count: number of registered exam patterns
        - formula_count: number of formulas tied to this concept
        - prerequisite_position: earlier in course = more foundational = higher
        - question_type_variety: number of distinct question types
    """

    WEIGHTS = {
        "exam_frequency": 0.40,
        "pattern_count": 0.25,
        "formula_count": 0.15,
        "question_type_variety": 0.10,
        "prerequisite_position": 0.10,
    }

    @staticmethod
    def stars_for(score: int) -> str:
        if score >= 90:
            return "★★★★★"
        elif score >= 70:
            return "★★★★"
        elif score >= 50:
            return "★★★"
        elif score >= 30:
            return "★★"
        else:
            return "★"

    def score(self, concept_id: str, concept_data: dict | None = None,
              exam_patterns: list[dict] | None = None,
              total_concepts: int = 1, position: int = 0) -> ExamImportanceResult:
        """Score a single concept's exam importance."""
        concept_data = concept_data or {}
        exam_patterns = exam_patterns or []

        # Factor 1: Exam frequency
        frequency = concept_data.get("exam_frequency", 0)
        if isinstance(frequency, (int, float)):
            freq_score = min(100, frequency * 25)  # 4 appearances = 100
        else:
            freq_score = 0

        # Factor 2: Pattern count
        pattern_count = len(exam_patterns)
        pattern_score = min(100, pattern_count * 33)  # 3 patterns = 100

        # Factor 3: Formula count
        formulas = concept_data.get("formulas", [])
        formula_count = len(formulas) if isinstance(formulas, list) else 0
        formula_score = min(100, formula_count * 25)  # 4 formulas = 100

        # Factor 4: Question type variety
        question_types = set()
        for p in exam_patterns:
            qt = p.get("type", p.get("question_type", ""))
            if qt:
                question_types.add(qt)
        type_score = min(100, len(question_types) * 33)  # 3 types = 100

        # Factor 5: Prerequisite position (earlier = more foundational)
        if total_concepts > 0:
            position_ratio = position / total_concepts
            position_score = max(20, 100 - int(position_ratio * 80))
        else:
            position_score = 50

        # Weighted total
        raw_score = (
            freq_score * self.WEIGHTS["exam_frequency"] +
            pattern_score * self.WEIGHTS["pattern_count"] +
            formula_score * self.WEIGHTS["formula_count"] +
            type_score * self.WEIGHTS["question_type_variety"] +
            position_score * self.WEIGHTS["prerequisite_position"]
        )

        score = min(100, int(raw_score))
        return ExamImportanceResult(
            concept_id=concept_id,
            score=score,
            stars=self.stars_for(score),
            factors={
                "frequency": round(freq_score, 1),
                "patterns": round(pattern_score, 1),
                "formulas": round(formula_score, 1),
                "type_variety": round(type_score, 1),
                "position": round(position_score, 1),
            },
        )

    def score_all(self, concepts: list[dict],
                  exam_patterns_by_concept: dict[str, list[dict]] | None = None) -> list[ExamImportanceResult]:
        """Score all concepts and sort by importance."""
        exam_patterns_by_concept = exam_patterns_by_concept or {}
        results = []
        for i, c in enumerate(concepts):
            cid = c.get("concept_id", c.get("id", f"concept_{i}"))
            patterns = exam_patterns_by_concept.get(cid, [])
            result = self.score(cid, c, patterns, len(concepts), i)
            results.append(result)
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def get_sprint_order(self, concepts: list[dict],
                         exam_patterns_by_concept: dict[str, list[dict]] | None = None) -> list[str]:
        """Get concept ordering for Sprint PDF (top-N by exam importance)."""
        results = self.score_all(concepts, exam_patterns_by_concept)
        return [r.concept_id for r in results[:6]]

    def get_mock_exam_distribution(self, concepts: list[dict],
                                   exam_patterns_by_concept: dict[str, list[dict]] | None = None) -> list[dict]:
        """Get concept distribution for MockExam with importance scores."""
        results = self.score_all(concepts, exam_patterns_by_concept)
        return [{"concept_id": r.concept_id, "importance": r.score, "stars": r.stars}
                for r in results]
