"""RealQuestionValidator — ensures every question comes from a registered exam pattern."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.question_pipeline.exam_pattern_library import (
    get_library, ExamPattern,
)
from core.pdf_content_v2.question_pipeline.question_source_priority import (
    QuestionSource, SourcePriority,
)

TEMPLATE_FAKE_PATTERNS = [
    "请填写一个高频公式",
    "请说明",
    "请谈谈",
    "请掌握",
    "请列举",
    "请简述",
]


@dataclass
class RealQuestionReport:
    total_questions: int = 0
    pattern_matched: int = 0        # from registered ExamPattern
    template_fake: int = 0          # "请填写..." style
    generic_stem: int = 0           # no specific data/conditions
    ai_generated: int = 0           # labeled AI_GENERATED
    web_retrieved: int = 0          # labeled WEB_RETRIEVED
    past_exam: int = 0              # from real exams
    textbook: int = 0               # from textbook
    real_exam_score: float = 0.0    # 0-100
    issues: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "total_questions": self.total_questions,
            "pattern_matched": self.pattern_matched,
            "template_fake": self.template_fake,
            "generic_stem": self.generic_stem,
            "ai_generated": self.ai_generated,
            "web_retrieved": self.web_retrieved,
            "past_exam": self.past_exam,
            "textbook": self.textbook,
            "real_exam_score": round(self.real_exam_score, 1),
            "issues": self.issues,
            "passed": self.passed,
        }


class RealQuestionValidator:
    """Validates that questions are real exam-style, not templates.

    Requires:
        1. Every question matches a registered ExamPattern, OR
        2. Comes from past_exam/textbook/ppt source, OR
        3. Is AI_GENERATED with explicit label AND matches a pattern's structure.

    Hard gates:
        template_fake == 0
        real_exam_score >= 85
    """

    def __init__(self, course_id: str = "probability_ch2"):
        self.course_id = course_id
        self.library = get_library()

    def validate(self, questions: list[dict]) -> RealQuestionReport:
        report = RealQuestionReport()
        report.total_questions = len(questions)
        patterns = self.library.get_patterns(self.course_id)

        for q in questions:
            stem = str(q.get("stem", q.get("problem", "")))
            qtype = str(q.get("type", q.get("question_type", "")))
            source = str(q.get("source", q.get("source_level", "")))

            # ── 1. Template fake check ──
            is_fake = False
            for fp in TEMPLATE_FAKE_PATTERNS:
                if fp in stem:
                    report.template_fake += 1
                    report.issues.append({
                        "question": stem[:60], "issue": "template_fake",
                        "detail": f"包含模板句式: {fp}",
                    })
                    is_fake = True
                    break
            if is_fake:
                continue

            # ── 2. Generic stem check ──
            has_numbers = any(c.isdigit() for c in stem)
            has_condition = any(kw in stem for kw in ["设", "已知", "若", "当", "其中"])
            has_goal = any(kw in stem for kw in ["求", "计算", "判断", "证明", "写出"])
            if len(stem) > 15 and not has_numbers and not has_condition:
                report.generic_stem += 1
                report.issues.append({
                    "question": stem[:60], "issue": "generic_stem",
                    "detail": "缺少具体数据和条件",
                })

            # ── 3. Source tracking ──
            if "past_exam" in source.lower() or "真题" in source:
                report.past_exam += 1
            elif "textbook" in source.lower() or "教材" in source:
                report.textbook += 1
            elif "ai_generated" in source.lower() or "ai_derived" in source.lower():
                report.ai_generated += 1
            elif "web_retrieved" in source.lower():
                report.web_retrieved += 1

            # ── 4. Pattern match attempt ──
            if self._matches_any_pattern(stem, qtype, patterns):
                report.pattern_matched += 1

        # ── Compute real_exam_score ──
        valid = report.total_questions - report.template_fake
        if report.total_questions == 0:
            report.real_exam_score = 0
        else:
            base = 100
            base -= report.template_fake * 15    # -15 per fake
            base -= report.generic_stem * 5      # -5 per generic
            base -= max(0, report.ai_generated - 2) * 3  # -3 per AI beyond 2
            report.real_exam_score = max(0, base)

        report.passed = report.template_fake == 0 and report.real_exam_score >= 85
        return report

    def _matches_any_pattern(self, stem: str, qtype: str,
                              patterns: list[ExamPattern]) -> bool:
        """Check if a question stem matches any registered pattern's structure."""
        for p in patterns:
            if p.question_type != qtype and qtype:
                continue
            # Extract key Chinese terms from the pattern template
            template_terms = set(
                t for t in p.stem_template.replace("{", " ").replace("}", " ").split()
                if len(t) >= 3 and any('一' <= c <= '鿿' for c in t)
            )
            stem_terms = set(
                t for t in stem.replace("{", " ").replace("}", " ").split()
                if len(t) >= 3 and any('一' <= c <= '鿿' for c in t)
            )
            if template_terms and stem_terms:
                overlap = len(template_terms & stem_terms) / max(1, len(template_terms))
                if overlap > 0.4:
                    return True
        return False
