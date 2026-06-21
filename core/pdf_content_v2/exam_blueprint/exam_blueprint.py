"""ExamBlueprint and ExamSectionBlueprint — real exam structure definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BlueprintSource(Enum):
    PAST_EXAM_STATS = "past_exam_stats"    # From uploaded real exams
    LOCAL_COURSE_PROFILE = "local_course"   # From course-specific profile
    DEFAULT_PROFILE = "default_profile"     # Generic course default
    AI_ESTIMATED = "ai_estimated"           # LLM guessed


@dataclass
class ExamSectionBlueprint:
    """A single section in the exam blueprint."""
    section_name: str           # e.g. "一、选择题"
    question_type: str          # e.g. "选择题"
    question_count: int         # e.g. 5
    score_per_question: int     # e.g. 4
    total_score: int            # count × score_per
    required_concepts: list[str] = field(default_factory=list)
    difficulty_range: list[str] = field(default_factory=list)  # e.g. ["基础", "中等"]

    def validate(self) -> bool:
        return self.total_score == self.question_count * self.score_per_question

    def to_dict(self) -> dict:
        return {
            "section_name": self.section_name, "question_type": self.question_type,
            "question_count": self.question_count, "score_per_question": self.score_per_question,
            "total_score": self.total_score, "required_concepts": self.required_concepts,
            "difficulty_range": self.difficulty_range,
        }


@dataclass
class ExamBlueprint:
    """Complete exam blueprint for a course chapter."""
    course_id: str
    chapter_id: str
    course_name: str
    chapter_name: str
    total_score: int = 100
    sections: list[ExamSectionBlueprint] = field(default_factory=list)
    difficulty_distribution: dict[str, float] = field(default_factory=dict)  # {"基础": 0.35, ...}
    concept_weight_distribution: dict[str, float] = field(default_factory=dict)  # {"分布函数": 0.15, ...}
    source: BlueprintSource = BlueprintSource.DEFAULT_PROFILE
    confidence: float = 0.8  # 0.0–1.0

    def section_total(self) -> int:
        return sum(s.total_score for s in self.sections)

    def is_valid(self) -> bool:
        return (
            self.total_score == 100
            and self.section_total() == 100
            and all(s.validate() for s in self.sections)
            and abs(sum(self.difficulty_distribution.values()) - 1.0) < 0.05
            if self.difficulty_distribution else True
        )

    def choice_answer_distribution(self, answer_letters: list[str]) -> dict[str, int]:
        """Count choice answer distribution."""
        dist: dict[str, int] = {}
        for letter in answer_letters:
            dist[letter] = dist.get(letter, 0) + 1
        return dist

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id, "chapter_id": self.chapter_id,
            "course_name": self.course_name, "chapter_name": self.chapter_name,
            "total_score": self.total_score,
            "sections": [s.to_dict() for s in self.sections],
            "section_score_sum": self.section_total(),
            "difficulty_distribution": self.difficulty_distribution,
            "concept_weight_distribution": self.concept_weight_distribution,
            "source": self.source.value, "confidence": self.confidence,
        }
