"""Lightweight subject-type detection for StudyPilot generation."""

from __future__ import annotations

import re


SUBJECT_TYPES = {
    "engineering": {
        "label": "理工工程类",
        "keywords": ["电磁场", "电路", "数字电路", "信号", "物理", "电磁波", "通信原理"],
        "generation_focus": "公式推导、示意图、工程例题、计算题和适用条件。",
    },
    "math": {
        "label": "数学类",
        "keywords": ["概率", "高数", "线代", "数学", "随机过程", "离散数学", "微积分"],
        "generation_focus": "定义、定理、函数/分布图、证明思路、题型方法和易错条件。",
    },
    "humanities": {
        "label": "人文社科类",
        "keywords": ["历史", "近现代史", "纲要", "思政", "马原", "马克思", "毛概", "法学", "文学", "哲学"],
        "generation_focus": "时间线、概念对比、人物/事件关系、论述题模板、记忆口诀和案例分析。",
    },
    "language": {
        "label": "语言类",
        "keywords": ["英语", "日语", "语言", "写作", "翻译", "作文"],
        "generation_focus": "词汇、语法、例句、作文模板、翻译技巧和高频表达。",
    },
}


def detect_subject_type(course: dict | str | None) -> str:
    """Detect a broad subject type from course metadata or a course name."""
    if isinstance(course, dict):
        text = " ".join(str(course.get(key, "")) for key in ("course_name", "book_name", "teacher", "university"))
    else:
        text = str(course or "")
    compact = re.sub(r"\s+", "", text).lower()
    for subject_type, config in SUBJECT_TYPES.items():
        if any(keyword.lower() in compact for keyword in config["keywords"]):
            return subject_type
    return "engineering"


def subject_prompt_hint(subject_type: str) -> str:
    config = SUBJECT_TYPES.get(subject_type, SUBJECT_TYPES["engineering"])
    return f"学科类型：{config['label']}。生成倾向：{config['generation_focus']}"
