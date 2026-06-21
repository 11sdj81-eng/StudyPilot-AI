"""AI Explainer — transforms concept definitions into multi-level explanations."""

from typing import Any

EMPTY_PHRASES = [
    "该知识点很重要", "建议掌握", "需要认真学习", "综上所述",
    "本章主要介绍", "可以帮助你理解", "是非常重要的",
]


def check_empty_advice(text: str) -> list[str]:
    """Detect generic/empty advice phrases."""
    hits = []
    for phrase in EMPTY_PHRASES:
        if phrase in text:
            hits.append(phrase)
    return hits


def build_concept_explanation(concept: dict, style: str = "intuition_first") -> str:
    """Build a teacher-quality explanation from concept data."""
    title = concept.get("display_name", concept.get("title", ""))
    definition = concept.get("definition", "")
    plain = concept.get("plain_explanation", "")
    why = concept.get("why_important", "")

    parts = []
    if style == "intuition_first":
        if plain:
            parts.append(f"直观理解：{plain}")
        if definition:
            parts.append(f"严格定义：{definition}")
    else:
        if definition:
            parts.append(f"定义：{definition}")
        if plain:
            parts.append(f"通俗解释：{plain}")

    if why:
        parts.append(f"考试地位：{why}")

    return "\n\n".join(parts) if parts else title
