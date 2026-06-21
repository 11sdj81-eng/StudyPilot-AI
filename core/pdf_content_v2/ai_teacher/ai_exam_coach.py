"""AI Exam Coach — generates "why tested" / "how tested" / "how to score"."""

from typing import Any


def build_exam_strategy(concept: dict, pattern: dict | None = None) -> dict:
    """Build exam strategy from concept + exam pattern data."""
    title = concept.get("display_name", concept.get("title", ""))
    exam_usage = concept.get("exam_usage", [])
    how_tested = pattern.get("how_tested", "") if pattern else ""
    frequency = pattern.get("frequency", 0) if pattern else 0
    question_types = pattern.get("question_types", []) if pattern else []

    why = f"{title}是考试重点。"
    if frequency:
        why += f"近5年出现 {frequency} 次。"
    if question_types:
        why += f"常以{'、'.join(question_types)}形式出现。"

    how = list(exam_usage) if exam_usage else []
    if how_tested:
        how.append(how_tested)

    return {
        "why_tested": why,
        "how_tested": how,
        "scoring": _default_scoring(question_types),
    }


def _default_scoring(question_types: list[str]) -> list[str]:
    if "计算题" in question_types or "综合题" in question_types:
        return ["公式选择正确 2 分", "计算过程完整 2 分", "结果正确 1 分"]
    if "选择题" in question_types:
        return ["概念判断正确 2 分", "排除错误选项 2 分"]
    return ["答案正确 5 分"]


EMPTY_COACH_PATTERNS = [
    "该知识点很重要", "建议掌握", "需要认真学习",
    "考试中经常出现", "是考试重点", "必须掌握",
]


def is_empty_coach(text: str) -> bool:
    """Detect generic coaching phrases."""
    for p in EMPTY_COACH_PATTERNS:
        if text.strip() == p or (p in text and len(text) < 25):
            return True
    return False
