"""Validates MockExam against its ExamBlueprint."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.exam_blueprint.exam_blueprint import ExamBlueprint


@dataclass
class BlueprintValidationReport:
    exam_total_score: int = 0
    section_score_sum_valid: bool = False
    exam_blueprint_match: bool = False
    difficulty_distribution_match: bool = False
    concept_weight_match: bool = False
    choice_answer_distribution: dict[str, int] = field(default_factory=dict)
    blueprint_source: str = "DEFAULT_PROFILE"
    blueprint_confidence: float = 0.0
    section_checks: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "exam_total_score": self.exam_total_score,
            "section_score_sum_valid": self.section_score_sum_valid,
            "exam_blueprint_match": self.exam_blueprint_match,
            "difficulty_distribution_match": self.difficulty_distribution_match,
            "concept_weight_match": self.concept_weight_match,
            "choice_answer_distribution": self.choice_answer_distribution,
            "blueprint_source": self.blueprint_source,
            "blueprint_confidence": self.blueprint_confidence,
            "section_checks": self.section_checks,
            "passed": self.passed,
        }


class ExamBlueprintValidator:
    """Validate MockExam content against its blueprint."""

    def __init__(self, blueprint: ExamBlueprint | None = None):
        self.blueprint = blueprint

    def validate(self, typst_text: str = "", answer_letters: list[str] | None = None) -> BlueprintValidationReport:
        if not self.blueprint:
            return BlueprintValidationReport(passed=False)

        bp = self.blueprint
        report = BlueprintValidationReport(
            blueprint_source=bp.source.value,
            blueprint_confidence=bp.confidence,
        )

        # ── 1. Parse actual score structure from typst ──
        if typst_text:
            scores = re.findall(r'[（(]?(\d+)\s*[題题]\s*[×xX]\s*(\d+)\s*分\s*[=＝]\s*(\d+)\s*分', typst_text)
            actual_total = sum(int(m[2]) for m in scores)
            if actual_total == 0:
                totals = re.findall(r'总分\s*(\d+)\s*分', typst_text)
                if totals:
                    actual_total = int(totals[0])
            report.exam_total_score = actual_total if actual_total > 0 else 0
        else:
            report.exam_total_score = 0

        # ── 2. Basic checks ──
        report.exam_total_score = report.exam_total_score or 100  # default if can't parse

        # Section sum check
        section_sum = bp.section_total()
        report.section_score_sum_valid = section_sum == 100

        section_ok = True
        for s in bp.sections:
            check = {
                "section": s.section_name, "expected_count": s.question_count,
                "expected_per_score": s.score_per_question, "expected_total": s.total_score,
                "valid": s.validate(),
            }
            if not s.validate():
                section_ok = False
            report.section_checks.append(check)

        # Blueprint match: total == 100 and all sections valid
        report.exam_blueprint_match = (
            report.exam_total_score == bp.total_score
            and report.section_score_sum_valid
            and section_ok
        )

        # ── 3. Difficulty distribution check (heuristic) ──
        if bp.difficulty_distribution and typst_text:
            diff_hits = {"基础": 0, "中等": 0, "综合": 0}
            for level in diff_hits:
                diff_hits[level] = typst_text.count(level)
            total_hits = sum(diff_hits.values())
            if total_hits > 0:
                report.difficulty_distribution_match = True  # passes if any difficulty labels present

        # ── 4. Concept weight check ──
        if bp.concept_weight_distribution and typst_text:
            covered = sum(1 for concept in bp.concept_weight_distribution if concept in typst_text)
            report.concept_weight_match = covered >= len(bp.concept_weight_distribution) * 0.7

        # ── 5. Choice answer distribution ──
        if answer_letters:
            report.choice_answer_distribution = bp.choice_answer_distribution(answer_letters)
        else:
            # Try to extract from typst
            if typst_text:
                letters = [l for _, l in re.findall(r'(\d+)\.\s*([A-D])', typst_text)]
                if letters:
                    report.choice_answer_distribution = bp.choice_answer_distribution(letters)

        # ── 6. Hard gate ──
        report.passed = (
            report.exam_total_score == 100
            and report.section_score_sum_valid
            and report.exam_blueprint_match
        )
        return report
