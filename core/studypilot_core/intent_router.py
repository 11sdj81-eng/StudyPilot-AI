"""IntentRouter — classifies user input before dispatching.

P0-1: "我不会镜像法" must NOT trigger PDF generation.
Only explicit PDF requests trigger PDF pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Intent(Enum):
    CHAT = "chat"               # 学习问答 → TutorBrain.answer()
    SUMMARIZE = "summarize"     # 总结 → TutorBrain.summarize()
    QUIZ = "quiz"               # 练习题 → TutorBrain.generate_quiz()
    MOCK_EXAM = "mock_exam"     # 模拟卷 → TutorBrain.generate_mock_exam()
    PDF = "pdf"                 # PDF导出 → only via explicit request
    UPLOAD = "upload"           # 上传资料 → MaterialStore
    UNKNOWN = "unknown"         # 无法判断 → 默认聊天


@dataclass
class IntentResult:
    intent: Intent
    confidence: float  # 0.0-1.0
    extracted_query: str  # Cleaned question text
    should_generate_pdf: bool
    reason: str


class IntentRouter:
    """Routes user input to correct handler. NEVER defaults to PDF."""

    # ── PDF triggers — ONLY these patterns trigger PDF ──
    PDF_TRIGGERS = [
        "生成pdf", "导出pdf", "生成 pdf", "导出 pdf",
        "生成讲义", "导出讲义",
        "生成pdf文件", "生成复习资料", "生成学习资料",
        "generate pdf", "export pdf",
    ]

    # ── Mock exam triggers ──
    MOCK_TRIGGERS = [
        "模拟卷", "模拟考试", "生成试卷", "出一套卷子",
        "mock exam", "模拟题",
    ]

    # ── Quiz triggers ──
    QUIZ_TRIGGERS = [
        "出题", "练习题", "给我.*题", "出.*题",
        "测试一下", "检验", "自测",
    ]

    # ── Summarize triggers ──
    SUMMARIZE_TRIGGERS = [
        "总结", "归纳", "概括", "梳理",
        "本章讲了什么", "学了什么",
    ]

    def route(self, user_input: str) -> IntentResult:
        """Classify user input. PDF is NEVER the default."""
        text = user_input.strip().lower()

        # 1. Check PDF triggers first (most specific, highest risk)
        for trigger in self.PDF_TRIGGERS:
            if trigger in text:
                return IntentResult(
                    intent=Intent.PDF, confidence=0.95,
                    extracted_query=user_input,
                    should_generate_pdf=True,
                    reason=f"Matched PDF trigger: '{trigger}'",
                )

        # 2. Mock exam
        import re
        for trigger in self.MOCK_TRIGGERS:
            if re.search(trigger, text):
                return IntentResult(
                    intent=Intent.MOCK_EXAM, confidence=0.85,
                    extracted_query=user_input,
                    should_generate_pdf=False,
                    reason=f"Matched mock exam trigger: '{trigger}'",
                )

        # 3. Quiz
        for trigger in self.QUIZ_TRIGGERS:
            if re.search(trigger, text):
                return IntentResult(
                    intent=Intent.QUIZ, confidence=0.80,
                    extracted_query=user_input,
                    should_generate_pdf=False,
                    reason=f"Matched quiz trigger: '{trigger}'",
                )

        # 4. Summarize
        for trigger in self.SUMMARIZE_TRIGGERS:
            if re.search(trigger, text):
                return IntentResult(
                    intent=Intent.SUMMARIZE, confidence=0.80,
                    extracted_query=user_input,
                    should_generate_pdf=False,
                    reason=f"Matched summarize trigger: '{trigger}'",
                )

        # 5. Learning questions — Chinese question patterns
        learning_patterns = [
            r"怎么", r"如何", r"为什么", r"什么是", r"什么是",
            r"我不会", r"不懂", r"不理解", r"讲一下", r"解释",
            r"区别", r"关系", r"作用", r"意义", r"定义",
        ]
        for pattern in learning_patterns:
            if re.search(pattern, text):
                return IntentResult(
                    intent=Intent.CHAT, confidence=0.75,
                    extracted_query=user_input,
                    should_generate_pdf=False,
                    reason=f"Learning question detected",
                )

        # 6. Default: chat — NEVER PDF
        return IntentResult(
            intent=Intent.CHAT, confidence=0.50,
            extracted_query=user_input,
            should_generate_pdf=False,
            reason="Default to chat — unclear intent",
        )


# ── Singleton ──

_router: IntentRouter | None = None


def get_router() -> IntentRouter:
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router


def route_input(user_input: str) -> IntentResult:
    return get_router().route(user_input)
