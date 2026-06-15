"""Diagram policy checks for PDF learning materials."""

from __future__ import annotations


REQUIRED_DIAGRAM_KEYWORDS = {
    "高斯": "高斯面",
    "镜像": "镜像法",
    "边界条件": "边界条件",
    "等位": "等位线",
    "电场线": "电场线",
    "坐标": "坐标系",
    "积分区域": "二维积分区域",
    "分布": "概率分布图",
    "时间线": "时间线",
}


def required_diagram_topics(content: str) -> list[str]:
    text = str(content or "")
    return sorted({label for key, label in REQUIRED_DIAGRAM_KEYWORDS.items() if key in text})


def validate_diagram_policy(content: str, figures: list[dict] | None = None) -> dict:
    figures = figures or []
    required = required_diagram_topics(content)
    fig_text = " ".join(str(f.get("title", "")) + str(f.get("caption", "")) + str(f.get("target_section", "")) for f in figures)
    missing = [topic for topic in required if topic not in fig_text and not any(topic[:2] in str(f) for f in figures)]
    return {
        "passed": not missing,
        "required_topics": required,
        "figure_count": len(figures),
        "missing_topics": missing,
        "policy": "题目 -> 配图 -> 解题思路 -> 标准答案 -> 注释 -> 易错总结",
    }
