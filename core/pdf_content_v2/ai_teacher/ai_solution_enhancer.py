"""AI Solution Enhancer — adds teacher annotations to solution steps."""

from typing import Any


def enhance_solution(example: dict) -> dict:
    """Add teacher annotations to solution steps."""
    steps = list(example.get("solution_steps", []))
    mistakes = example.get("common_mistakes", [])
    grading = example.get("rubric", example.get("grading_points", []))

    enhanced_steps = []
    for i, step in enumerate(steps):
        annotation = ""
        if i == 0:
            annotation = "【第一步：理解题意】"
        elif i == len(steps) - 1:
            annotation = "【最后一步：写出答案】"
        else:
            annotation = f"【第{i+1}步】"
        enhanced_steps.append(f"{annotation}\n{step}")

    return {
        "enhanced_steps": enhanced_steps,
        "step_count": len(steps),
        "has_mistake_warnings": len(mistakes) > 0,
        "has_grading_points": len(grading) > 0,
        "teacher_annotations": len(steps),
    }


def teacher_style_solution(problem: str, steps: list[str], answer: str,
                            mistakes: list[str], grading: list[str]) -> str:
    """Build a complete teacher-style solution block."""
    parts = []
    parts.append(f"题目：{problem}")
    parts.append("")

    for i, step in enumerate(steps, 1):
        parts.append(f"第{i}步：{step}")

    parts.append("")
    parts.append(f"答案：{answer}")

    if grading:
        parts.append("")
        parts.append("评分点：")
        for g in grading[:4]:
            parts.append(f"  • {g}")

    if mistakes:
        parts.append("")
        parts.append("易错提醒：")
        for m in mistakes[:3]:
            parts.append(f"  ⚠️ {m}")

    return "\n".join(parts)
