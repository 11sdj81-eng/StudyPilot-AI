"""Quality gate for source-aligned PDF 2.0 content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.models import LectureDocument


EMPTY_SUMMARY_PATTERNS = [
    "本章主要介绍",
    "需要认真学习",
    "掌握相关知识",
    "综上所述",
    "可以帮助你理解",
]

INTERNAL_FIELD_PATTERNS = [
    "concept_id",
    "source_refs",
    "exam_frequency",
    "metadata",
    "render_priority",
]


@dataclass
class QualityResult:
    passed: bool
    checks: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "checks": self.checks, "failures": self.failures}


class PDFContentQualityGate:
    """Reject PDFs that are unsupported summaries instead of study handouts.

    Demo mode: relaxes source requirements for courses without textbooks.
    """

    def check(self, document: LectureDocument, typst_text: str = "",
              is_demo: bool = False) -> QualityResult:
        sections = document.sections
        concept_count = sum(1 for s in sections if s.concept)
        sourced = sum(1 for s in sections if s.concept and s.concept.has_source())
        with_examples = sum(1 for s in sections if s.examples)
        with_patterns = sum(1 for s in sections if s.exam_pattern and s.exam_pattern.past_exam_refs)
        unsupported_frequency = sum(1 for s in sections if s.exam_pattern and s.exam_pattern.frequency > 0 and not s.exam_pattern.past_exam_refs)
        no_answers = sum(1 for s in sections for e in s.examples if not e.standard_answer.strip())
        empty_summary_count = sum(typst_text.count(p) for p in EMPTY_SUMMARY_PATTERNS)
        internal_leaks = [p for p in INTERNAL_FIELD_PATTERNS if p in typst_text]
        dense_blocks = len(re.findall(r".{900,}", typst_text))

        checks = {
            "concept_count": concept_count,
            "source_aligned_rate": _ratio(sourced, concept_count),
            "example_coverage_rate": _ratio(with_examples, concept_count),
            "exam_pattern_coverage_rate": _ratio(with_patterns, concept_count),
            "unsupported_claim_count": unsupported_frequency,
            "empty_summary_count": empty_summary_count,
            "internal_field_leak_count": len(internal_leaks),
            "question_without_answer_count": no_answers,
            "layout_dense_block_count": dense_blocks,
            "large_blank_risk": False,
            "overlap_risk": False,
        }
        failures = []
        if concept_count == 0:
            failures.append("没有可渲染知识点。")
        if checks["source_aligned_rate"] < 1 and not is_demo:
            failures.append("存在无来源知识点。")
        # Demo: relax requirements since all content is AI-generated
        min_example_rate = 0.5 if (document.pdf_type in ("MockExam", "Sprint") or is_demo) else 0.85
        if checks["example_coverage_rate"] < min_example_rate:
            failures.append("存在无例题重点。")
        if checks["exam_pattern_coverage_rate"] < 0.75 and document.pdf_type != "MockExam" and not is_demo:
            failures.append("真题考法覆盖不足。")
        if unsupported_frequency and not is_demo:
            failures.append("存在无来源考频。")
        if no_answers:
            failures.append("存在无答案题目。")
        if empty_summary_count:
            failures.append("存在空洞 AI 总结式表达。")
        if internal_leaks:
            failures.append(f"内部字段泄露：{', '.join(internal_leaks)}")
        if dense_blocks > 3:
            failures.append("可能存在排版拥挤。")
        return QualityResult(passed=not failures, checks=checks, failures=failures)


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0
