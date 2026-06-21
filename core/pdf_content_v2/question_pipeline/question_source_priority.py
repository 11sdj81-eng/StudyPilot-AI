"""Question Source Priority — immutable hierarchy for question provenance.

Priority (immutable):
    真题 > 教材例题 > PPT例题 > WEB_RETRIEVED > AI_GENERATED

AI can ONLY vary background/data/difficulty within registered patterns.
AI-generated questions MUST be labeled.
"""

from __future__ import annotations

from enum import Enum


class QuestionSource(Enum):
    PAST_EXAM = "past_exam"           # 真题
    TEXTBOOK = "textbook"             # 教材例题
    PPT = "ppt"                       # PPT例题
    WEB_RETRIEVED = "web_retrieved"   # 联网检索
    AI_GENERATED = "ai_generated"     # AI生成

    @property
    def priority(self) -> int:
        return {
            QuestionSource.PAST_EXAM: 1,
            QuestionSource.TEXTBOOK: 2,
            QuestionSource.PPT: 3,
            QuestionSource.WEB_RETRIEVED: 4,
            QuestionSource.AI_GENERATED: 5,
        }[self]

    @property
    def label(self) -> str:
        return {
            QuestionSource.PAST_EXAM: "真题",
            QuestionSource.TEXTBOOK: "教材例题",
            QuestionSource.PPT: "PPT例题",
            QuestionSource.WEB_RETRIEVED: "联网检索",
            QuestionSource.AI_GENERATED: "AI生成",
        }[self]

    @property
    def label_with_tag(self) -> str:
        return f"[{self.label}]"


class SourcePriority:
    """Immutable source priority check."""

    ORDER = [
        QuestionSource.PAST_EXAM,
        QuestionSource.TEXTBOOK,
        QuestionSource.PPT,
        QuestionSource.WEB_RETRIEVED,
        QuestionSource.AI_GENERATED,
    ]

    @classmethod
    def is_higher_than(cls, a: QuestionSource, b: QuestionSource) -> bool:
        return a.priority < b.priority

    @classmethod
    def best_available(cls, sources: list[QuestionSource]) -> QuestionSource:
        return min(sources, key=lambda s: s.priority)

    @classmethod
    def can_override(cls, new_source: QuestionSource, existing_source: QuestionSource) -> bool:
        """Web/AI content must NEVER override textbook or exam content."""
        return cls.is_higher_than(new_source, existing_source)

    @classmethod
    def requires_label(cls, source: QuestionSource) -> bool:
        """Sources that must be explicitly labeled in PDF output."""
        return source in (QuestionSource.WEB_RETRIEVED, QuestionSource.AI_GENERATED)

    @classmethod
    def ai_allowed_actions(cls) -> list[str]:
        """AI can ONLY do these — no free-form question invention."""
        return [
            "换背景（改变题目场景描述）",
            "换数据（改变数值参数）",
            "换难度（增加/减少推理步骤）",
            "同考法变式（保持相同知识点和求解方法）",
        ]

    @classmethod
    def ai_forbidden_actions(cls) -> list[str]:
        return [
            "自由发明新题目模式",
            "改变考查的知识点",
            "添加课程范围外的概念",
            "伪造教材/真题来源",
            "生成没有答案的题目",
            "生成无法验证的开放式问题",
        ]


def get_source_priority() -> list[QuestionSource]:
    return list(SourcePriority.ORDER)
