"""IntentRouter — classifies user input. PDF is NEVER the default."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class Intent(Enum):
    CHAT = "chat"
    SUMMARY = "summary"
    QUIZ = "quiz"
    MOCK_EXAM = "mock_exam"
    PDF_EXPORT = "pdf_export"
    UPLOAD = "upload"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    should_generate_pdf: bool
    reason: str


class IntentRouter:
    """Routes user input. PDF only via explicit trigger."""

    PDF_TRIGGERS = [
        "生成pdf", "导出pdf", "生成 pdf", "导出 pdf",
        "生成讲义", "导出讲义", "生成讲义文件",
    ]
    MOCK_TRIGGERS = ["模拟卷", "模拟考试", "生成试卷", "出一套", "考我"]
    QUIZ_TRIGGERS = ["出题", "练习题", "给我.*题", "出.*题", "来点.*题", "测试"]
    SUMMARY_TRIGGERS = ["总结", "归纳", "概括", "梳理", "本章讲"]

    def route(self, text: str) -> IntentResult:
        t = text.strip().lower()

        for trig in self.PDF_TRIGGERS:
            if trig in t:
                return IntentResult(Intent.PDF_EXPORT, 0.95, True, f"PDF trigger: {trig}")

        for trig in self.MOCK_TRIGGERS:
            if re.search(trig, t):
                return IntentResult(Intent.MOCK_EXAM, 0.85, False, f"Mock trigger: {trig}")

        for trig in self.QUIZ_TRIGGERS:
            if re.search(trig, t):
                return IntentResult(Intent.QUIZ, 0.80, False, f"Quiz trigger: {trig}")

        for trig in self.SUMMARY_TRIGGERS:
            if re.search(trig, t):
                return IntentResult(Intent.SUMMARY, 0.80, False, f"Summary trigger: {trig}")

        # Learning patterns → CHAT
        if re.search(r"什么|怎么|如何|为什么|我不会|不懂|不理解|讲一下|解释|区别|关系|作用|定义|意思|理解", t):
            return IntentResult(Intent.CHAT, 0.75, False, "Learning question")

        return IntentResult(Intent.CHAT, 0.50, False, "Default chat")


_router: IntentRouter | None = None


def get_router() -> IntentRouter:
    global _router
    if _router is None:
        _router = IntentRouter()
    return _router
