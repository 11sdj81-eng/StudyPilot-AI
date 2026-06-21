"""Final PDF 2.2 quality gate — comprehensive pass/fail for all quality dimensions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.pdf_content_v2.models import LectureDocument, LectureSection
from core.pdf_content_v2.quality.answer_validator import AnswerValidator
from core.pdf_content_v2.quality.question_deduplicator import QuestionDeduplicator
from core.pdf_content_v2.quality.exam_blueprint import ExamBlueprintValidator
from core.pdf_content_v2.quality.source_level_validator import SourceLevelValidator


INTERNAL_LEAK_PATTERNS = [
    "concept_id", "formula_id", "source_refs", "source_basis",
    "diagram_db", "programmatic", "QuestionCard", "ExampleCard",
    "metadata", "render_priority", "Typst", "MathJax", "Chromium",
]

FORBIDDEN_GENERIC = [
    "请填写一个高频公式",
    "请列举以下内容",
    "请简述以下概念",
    "本章主要介绍了",
    "综上所述，本章",
]

LAYOUT_ISSUES = [
    (r"\\{\\s*\\}", "空的大括号"),
    (r"\\$\\$\\s*\\$\\$", "空公式块"),
    (r"\\\\$", "孤立换行"),
]


@dataclass
class FinalQualityResult:
    passed: bool = False
    answer_error_count: int = 0
    duplicate_question_count: int = 0
    near_duplicate_question_count: int = 0
    cross_pdf_duplicate_count: int = 0
    fake_question_count: int = 0
    unsupported_claim_count: int = 0
    source_missing_count: int = 0
    internal_field_leak_count: int = 0
    formula_issue_count: int = 0
    layout_overlap_count: int = 0
    exam_total_score: int = 0
    exam_blueprint_match: bool = False
    manual_acceptance_recommended: bool = False
    per_pdf_results: dict[str, dict] = field(default_factory=dict)
    all_checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "answer_error_count": self.answer_error_count,
            "duplicate_question_count": self.duplicate_question_count,
            "near_duplicate_question_count": self.near_duplicate_question_count,
            "cross_pdf_duplicate_count": self.cross_pdf_duplicate_count,
            "fake_question_count": self.fake_question_count,
            "unsupported_claim_count": self.unsupported_claim_count,
            "source_missing_count": self.source_missing_count,
            "internal_field_leak_count": self.internal_field_leak_count,
            "formula_issue_count": self.formula_issue_count,
            "layout_overlap_count": self.layout_overlap_count,
            "exam_total_score": self.exam_total_score,
            "exam_blueprint_match": self.exam_blueprint_match,
            "manual_acceptance_recommended": self.manual_acceptance_recommended,
            "per_pdf_results": self.per_pdf_results,
            "all_checks": self.all_checks,
        }


def _count_sections(doc) -> int:
    """Count sections whether doc is a dict or LectureDocument."""
    if doc is None:
        return 0
    if isinstance(doc, dict):
        return len(doc.get("sections", []))
    if hasattr(doc, 'sections'):
        return len(doc.sections)
    return 0


class FinalPDFQualityGate:
    """Comprehensive quality gate for all four PDF types."""

    def __init__(self, course_name: str = "概率论与随机过程"):
        self.course_name = course_name
        self.answer_validator = AnswerValidator()
        self.deduplicator = QuestionDeduplicator()
        self.blueprint_validator = ExamBlueprintValidator()
        self.source_validator = SourceLevelValidator()

    def check_all(
        self,
        documents: dict[str, LectureDocument],
        typst_files: dict[str, Path],
        course_name: str = "",
    ) -> FinalQualityResult:
        """Run all quality checks on a set of documents."""
        if course_name:
            self.course_name = course_name
        result = FinalQualityResult()

        per_pdf: dict[str, dict] = {}

        # ── 1. Answer validation (MockExam) ──
        mock_doc = documents.get("MockExam")
        mock_typst = ""
        if mock_doc is not None and "MockExam" in typst_files:
            mock_path = typst_files["MockExam"]
            if mock_path.exists():
                mock_typst = mock_path.read_text(encoding="utf-8")
            answer_result = self.answer_validator.validate(mock_doc, mock_typst)
            result.answer_error_count = answer_result.answer_error_count
            result.exam_total_score = answer_result.score_total
            result.exam_blueprint_match = answer_result.score_valid
            per_pdf["MockExam"] = answer_result.to_dict()

        # ── 2. Deduplication (all PDFs) ──
        dedup_result = self.deduplicator.check_all(typst_files)
        result.duplicate_question_count = dedup_result.duplicate_question_count
        result.near_duplicate_question_count = dedup_result.near_duplicate_question_count
        result.cross_pdf_duplicate_count = dedup_result.cross_pdf_duplicate_count
        per_pdf["_dedup"] = dedup_result.to_dict()

        # ── 3. Source validation (all Typst) ──
        all_typst = ""
        for path in typst_files.values():
            if path.exists():
                all_typst += path.read_text(encoding="utf-8")
        source_result = self.source_validator.validate(all_typst)
        result.source_missing_count = source_result.source_missing_count
        result.fake_question_count = source_result.fake_question_count
        result.unsupported_claim_count = source_result.unsupported_claim_count

        # ── 4. Internal field leak check ──
        for pattern in INTERNAL_LEAK_PATTERNS:
            if pattern in all_typst:
                result.internal_field_leak_count += all_typst.count(pattern)

        # ── 5. Formula issues ──
        result.formula_issue_count = len(re.findall(r'\$\$?\s*\$\$?', all_typst))  # empty formulas
        # LaTeX leakage
        latex_leaks = re.findall(r'\\begin\{|\\frac\{|\\sqrt\{|\\\\\[', all_typst)
        result.formula_issue_count += len(latex_leaks)

        # ── 6. Layout issues ──
        for pattern, desc in LAYOUT_ISSUES:
            hits = len(re.findall(pattern, all_typst))
            if hits > 3:
                result.layout_overlap_count += hits

        # ── 7. Per-PDF checks ──
        for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
            if name in typst_files and typst_files[name].exists():
                content = typst_files[name].read_text(encoding="utf-8")
                doc = documents.get(name)
                per_pdf[name] = {
                    "has_content": len(content) > 1000,
                    "concept_count": _count_sections(doc),
                    "empty_summary_count": sum(content.count(p) for p in ["综上所述", "本章主要"]),
                    "fake_question_count": sum(content.count(p) for p in FORBIDDEN_GENERIC),
                    "internal_leaks": [p for p in INTERNAL_LEAK_PATTERNS if p in content],
                }

        result.per_pdf_results = per_pdf

        # ── 8. Final pass/fail ──
        all_pass = (
            result.answer_error_count == 0
            and result.duplicate_question_count == 0
            and result.cross_pdf_duplicate_count == 0
            and result.fake_question_count == 0
            and result.source_missing_count == 0
            and result.internal_field_leak_count == 0
            and result.formula_issue_count == 0
            and result.exam_blueprint_match
        )
        result.passed = all_pass
        result.manual_acceptance_recommended = all_pass

        result.all_checks = {
            "course_name": self.course_name,
            "pdfs_checked": list(typst_files.keys()),
            "total_pass": all_pass,
        }
        return result
