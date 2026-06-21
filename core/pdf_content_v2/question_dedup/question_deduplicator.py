"""4-level question deduplication with cross-PDF detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.question_dedup.question_fingerprint import (
    DuplicateLevel, QuestionFingerprint,
)
from core.pdf_content_v2.question_dedup.similarity import (
    compute_similarity, diversity_score,
)


@dataclass
class DuplicatePair:
    level: DuplicateLevel
    fp1: QuestionFingerprint
    fp2: QuestionFingerprint
    similarity: float
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "level": self.level.name,
            "level_num": self.level.value,
            "q1": self.fp1.question_id,
            "q2": self.fp2.question_id,
            "q1_source": self.fp1.source_pdf,
            "q2_source": self.fp2.source_pdf,
            "similarity": round(self.similarity, 4),
            "description": self.description,
        }


@dataclass
class DuplicateReport:
    exact_duplicate_count: int = 0
    normalized_duplicate_count: int = 0
    pattern_duplicate_count: int = 0
    semantic_duplicate_count: int = 0
    cross_pdf_duplicate_count: int = 0
    total_questions: int = 0
    diversity_score: float = 0.0
    duplicates: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "exact_duplicate_count": self.exact_duplicate_count,
            "normalized_duplicate_count": self.normalized_duplicate_count,
            "pattern_duplicate_count": self.pattern_duplicate_count,
            "semantic_duplicate_count": self.semantic_duplicate_count,
            "cross_pdf_duplicate_count": self.cross_pdf_duplicate_count,
            "total_questions": self.total_questions,
            "diversity_score": round(self.diversity_score, 1),
            "duplicates": self.duplicates,
            "passed": self.passed,
        }


class QuestionDeduplicator:
    """4-level deduplication for PDF question sets."""

    def __init__(self):
        self.fingerprints: list[QuestionFingerprint] = []

    def add_questions(self, questions: list[dict], source_pdf: str = "",
                       course_id: str = "probability_ch2") -> None:
        """Add questions from a dict list, tagging with source PDF."""
        for q in questions:
            fp = QuestionFingerprint.from_dict(q, source_pdf=source_pdf)
            fp.course_id = course_id
            self.fingerprints.append(fp)

    def check_all(self) -> DuplicateReport:
        """Run 4-level dedup on all fingerprints."""
        report = DuplicateReport()
        report.total_questions = len(self.fingerprints)
        seen_pairs: set[tuple[str, str]] = set()

        for i, fp1 in enumerate(self.fingerprints):
            for j, fp2 in enumerate(self.fingerprints):
                if j <= i:
                    continue
                pair_key = (min(fp1.question_id, fp2.question_id),
                            max(fp1.question_id, fp2.question_id))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                level, sim = compute_similarity(fp1, fp2)
                if level is None:
                    continue

                cross_pdf = fp1.source_pdf != fp2.source_pdf
                desc = self._describe(fp1, fp2, level)

                pair = DuplicatePair(level=level, fp1=fp1, fp2=fp2,
                                     similarity=sim, description=desc)
                report.duplicates.append(pair.to_dict())

                if level == DuplicateLevel.EXACT:
                    report.exact_duplicate_count += 1
                elif level == DuplicateLevel.NORMALIZED:
                    report.normalized_duplicate_count += 1
                elif level == DuplicateLevel.PATTERN:
                    report.pattern_duplicate_count += 1
                elif level == DuplicateLevel.SEMANTIC:
                    report.semantic_duplicate_count += 1

                if cross_pdf:
                    report.cross_pdf_duplicate_count += 1

        # Diversity score
        report.diversity_score = diversity_score(self.fingerprints)
        # Reduce diversity score per duplicate found
        dup_penalty = (report.exact_duplicate_count * 10
                       + report.normalized_duplicate_count * 5
                       + report.pattern_duplicate_count * 3
                       + report.cross_pdf_duplicate_count * 5)
        report.diversity_score = max(0, report.diversity_score - dup_penalty)

        # Pass if: no cross-PDF duplicates and diversity > 80
        report.passed = (
            report.cross_pdf_duplicate_count == 0
            and report.diversity_score >= 80
            and report.exact_duplicate_count == 0
        )
        return report

    def _describe(self, fp1: QuestionFingerprint, fp2: QuestionFingerprint,
                  level: DuplicateLevel) -> str:
        if level == DuplicateLevel.EXACT:
            return f"完全重复: {fp1.question_id} ≡ {fp2.question_id}"
        if level == DuplicateLevel.NORMALIZED:
            return f"同结构(不同数据): {fp1.concept_id}"
        if level == DuplicateLevel.PATTERN:
            return f"同考法: {fp1.pattern_key()}"
        return f"语义相似: {fp1.concept_id}"
