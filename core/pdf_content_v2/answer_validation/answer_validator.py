"""Base AnswerValidator — unified interface for course-specific validators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating a single question's answer."""
    is_valid: bool
    confidence: float                    # 0.0–1.0
    error_type: str | None = None        # e.g. "probability_out_of_range", "sum_not_one"
    message: str = ""


@dataclass
class ValidatedQuestion:
    """A question that has been through the validation pipeline."""
    question_id: str
    question_type: str                   # choice / fill / calculation / comprehensive
    question_text: str
    answer_text: str
    validation: ValidationResult
    needs_manual_review: bool = False
    validated: bool = True
    validation_confidence: float = 0.0
    validation_message: str = ""

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question_type": self.question_type,
            "question_text": self.question_text[:80],
            "answer_text": self.answer_text[:80],
            "is_valid": self.validation.is_valid,
            "confidence": self.validation.confidence,
            "error_type": self.validation.error_type,
            "message": self.validation.message,
            "needs_manual_review": self.needs_manual_review,
            "validated": self.validated,
        }


@dataclass
class ValidationReport:
    """Aggregate validation report for all questions in a PDF set."""
    validated_questions: int = 0
    failed_questions: int = 0
    manual_review_questions: int = 0
    passed_questions: int = 0
    validation_rate: float = 0.0
    answer_error_count: int = 0
    questions: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "validated_questions": self.validated_questions,
            "failed_questions": self.failed_questions,
            "manual_review_questions": self.manual_review_questions,
            "passed_questions": self.passed_questions,
            "validation_rate": round(self.validation_rate, 4),
            "answer_error_count": self.answer_error_count,
            "passed": self.passed,
            "questions": self.questions,
        }


class AnswerValidator:
    """Base class for course-specific answer validators.

    Subclasses must implement validate() for their course's question types.
    """

    def validate(self, question: dict | ValidatedQuestion) -> ValidationResult:
        raise NotImplementedError

    def validate_all(self, questions: list[dict]) -> ValidationReport:
        report = ValidationReport()
        for q in questions:
            if isinstance(q, ValidatedQuestion):
                result = q.validation
                qid = q.question_id
                qtype = q.question_type
            else:
                result = self.validate(q)
                qid = q.get("id", q.get("question_id", "unknown"))
                qtype = q.get("type", q.get("question_type", "unknown"))

            vq = ValidatedQuestion(
                question_id=qid, question_type=qtype,
                question_text=str(q.get("problem", q.get("stem", "")))[:80],
                answer_text=str(q.get("answer", q.get("standard_answer", "")))[:80],
                validation=result,
                needs_manual_review=not result.is_valid and result.confidence < 0.9,
                validation_confidence=result.confidence,
                validation_message=result.message,
            )
            report.questions.append(vq.to_dict())
            report.validated_questions += 1
            if not result.is_valid:
                report.failed_questions += 1
                report.answer_error_count += 1
            if vq.needs_manual_review:
                report.manual_review_questions += 1

        report.passed_questions = report.validated_questions - report.failed_questions
        report.validation_rate = (
            report.passed_questions / report.validated_questions
            if report.validated_questions > 0 else 0.0
        )
        report.passed = report.answer_error_count == 0
        return report
