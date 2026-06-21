"""StyleValidator — ensures questions match course exam style."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.question_style.fake_question_detector import FakeQuestionDetector
from core.pdf_content_v2.question_style.real_question_rewriter import RealQuestionRewriter
from core.pdf_content_v2.question_style.exam_style_profile import ExamStyleProfile


@dataclass
class StyleValidationReport:
    checked_question_count: int = 0
    fake_question_count: int = 0
    rewritten_question_count: int = 0
    unfixable_fake_question_count: int = 0
    fake_reasons: list[str] = field(default_factory=list)
    rewrite_results: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "checked_question_count": self.checked_question_count,
            "fake_question_count": self.fake_question_count,
            "rewritten_question_count": self.rewritten_question_count,
            "unfixable_fake_question_count": self.unfixable_fake_question_count,
            "fake_reasons": self.fake_reasons,
            "rewrite_results": self.rewrite_results,
            "passed": self.passed,
        }


class StyleValidator:
    """Detect fake questions and attempt rewriting."""

    def __init__(self, course_id: str = "probability_ch2"):
        self.course_id = course_id
        self.detector = FakeQuestionDetector()
        self.rewriter = RealQuestionRewriter()

    def validate(self, questions: list[dict]) -> StyleValidationReport:
        report = StyleValidationReport()
        report.checked_question_count = len(questions)

        for q in questions:
            result = self.detector.detect(q)
            if result.is_fake:
                report.fake_question_count += 1
                report.fake_reasons.extend(result.fake_reasons[:2])

                # Attempt rewrite
                rewrite = self.rewriter.rewrite(q, result)
                if rewrite.success:
                    report.rewritten_question_count += 1
                    report.rewrite_results.append(rewrite.to_dict())
                else:
                    report.unfixable_fake_question_count += 1
                    report.rewrite_results.append(rewrite.to_dict())

        # Hard gates
        report.passed = (
            report.fake_question_count == 0
            and report.unfixable_fake_question_count == 0
        )
        return report
