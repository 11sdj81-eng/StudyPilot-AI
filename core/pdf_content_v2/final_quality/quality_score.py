"""QualityScore — weighted scoring across all quality dimensions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QualityScore:
    correctness_score: float = 0.0   # 30% — answers, formulas, sources
    coverage_score: float = 0.0      # 20% — knowledge, formula, question type coverage
    pedagogy_score: float = 0.0      # 20% — teacher-like, mistakes, exam strategy
    layout_score: float = 0.0        # 15% — typesetting, textbook feel, printability
    diversity_score: float = 0.0     # 10% — question variety, dedup
    reliability_score: float = 0.0   # 5% — cache, source, web stability
    final_score: float = 0.0

    WEIGHTS = {
        "correctness": 0.30, "coverage": 0.20, "pedagogy": 0.20,
        "layout": 0.15, "diversity": 0.10, "reliability": 0.05,
    }

    def compute(self) -> float:
        # SP-083: Clamp all dimensions to [0, 100]
        self.correctness_score = max(0, min(100, self.correctness_score))
        self.coverage_score = max(0, min(100, self.coverage_score))
        self.pedagogy_score = max(0, min(100, self.pedagogy_score))
        self.layout_score = max(0, min(100, self.layout_score))
        self.diversity_score = max(0, min(100, self.diversity_score))
        self.reliability_score = max(0, min(100, self.reliability_score))
        self.final_score = max(0, min(100, (
            self.correctness_score * self.WEIGHTS["correctness"]
            + self.coverage_score * self.WEIGHTS["coverage"]
            + self.pedagogy_score * self.WEIGHTS["pedagogy"]
            + self.layout_score * self.WEIGHTS["layout"]
            + self.diversity_score * self.WEIGHTS["diversity"]
            + self.reliability_score * self.WEIGHTS["reliability"]
        )))
        return self.final_score

    def release_level(self) -> str:
        s = self.final_score
        if s >= 90:
            return "RELEASE_READY"
        if s >= 80:
            return "MANUAL_REVIEW"
        if s >= 60:
            return "DRAFT"
        return "FAILED"

    def to_dict(self) -> dict:
        return {
            "correctness_score": round(self.correctness_score, 1),
            "coverage_score": round(self.coverage_score, 1),
            "pedagogy_score": round(self.pedagogy_score, 1),
            "layout_score": round(self.layout_score, 1),
            "diversity_score": round(self.diversity_score, 1),
            "reliability_score": round(self.reliability_score, 1),
            "final_score": round(self.final_score, 1),
            "release_level": self.release_level(),
        }
