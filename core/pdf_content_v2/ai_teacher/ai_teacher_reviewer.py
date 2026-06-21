"""AI Teacher Reviewer — quality checks on teacher-generated content."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.ai_teacher.ai_teacher import TeacherNote
from core.pdf_content_v2.ai_teacher.ai_explainer import EMPTY_PHRASES, check_empty_advice
from core.pdf_content_v2.ai_teacher.ai_exam_coach import EMPTY_COACH_PATTERNS, is_empty_coach


@dataclass
class TeacherReviewReport:
    teacher_note_count: int = 0
    empty_advice_count: int = 0
    missing_exam_strategy_count: int = 0
    missing_common_mistake_count: int = 0
    student_level_adaptation_pass: bool = True
    teacher_like_score: float = 0.0
    issues: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "teacher_note_count": self.teacher_note_count,
            "empty_advice_count": self.empty_advice_count,
            "missing_exam_strategy_count": self.missing_exam_strategy_count,
            "missing_common_mistake_count": self.missing_common_mistake_count,
            "student_level_adaptation_pass": self.student_level_adaptation_pass,
            "teacher_like_score": round(self.teacher_like_score, 1),
            "issues": self.issues,
            "passed": self.passed,
        }


class TeacherReviewer:
    """Review AI Teacher output for quality."""

    def review(self, notes: list[TeacherNote], typst_text: str = "") -> TeacherReviewReport:
        report = TeacherReviewReport()
        report.teacher_note_count = len(notes)

        if not notes:
            return report

        scores = []
        for note in notes:
            # Check for empty advice
            empty = check_empty_advice(note.why_exam_likes_it)
            empty += check_empty_advice(note.beginner_explanation)
            if empty:
                report.empty_advice_count += len(empty)
                report.issues.append({"concept": note.concept_id, "type": "empty_advice", "detail": empty})

            # Check exam strategy completeness
            if not note.how_it_is_tested or len(note.how_it_is_tested) == 0:
                report.missing_exam_strategy_count += 1
                report.issues.append({"concept": note.concept_id, "type": "missing_exam_strategy"})
            if is_empty_coach(note.why_exam_likes_it):
                report.missing_exam_strategy_count += 1

            # Check common mistakes
            if not note.common_mistakes or len(note.common_mistakes) < 2:
                report.missing_common_mistake_count += 1
                report.issues.append({"concept": note.concept_id, "type": "missing_common_mistakes"})

            # Compute teacher score per note
            scores.append(note.teacher_score())

        # Overall teacher_like_score
        report.teacher_like_score = sum(scores) / len(scores) if scores else 0.0

        # Also check typst for empty/generic phrases
        if typst_text:
            for phrase in EMPTY_PHRASES + EMPTY_COACH_PATTERNS:
                count = typst_text.count(phrase)
                if count > 0:
                    report.empty_advice_count += count

        # Hard gates
        report.passed = (
            report.teacher_like_score >= 85
            and report.empty_advice_count == 0
            and report.missing_exam_strategy_count == 0
        )
        return report
