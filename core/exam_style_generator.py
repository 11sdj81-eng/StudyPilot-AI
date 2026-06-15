"""Exam-style metadata helpers for v1.1 PDF quality generation."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class SourceBasis:
    paper: str
    topic: str
    textbook_section: str
    reference_example: str
    adaptation: str
    source_type: str

    def as_dict(self) -> dict:
        return asdict(self)


def source_basis(
    topic: str,
    source_type: str = "真题考点题",
    paper: str = "2023 电磁场与电磁波期末试卷",
    textbook_section: str = "第一章 静电场",
    reference_example: str = "教材同知识点例题/习题",
    adaptation: str = "同知识点、同题型、同难度改编",
) -> dict:
    return SourceBasis(paper, topic, textbook_section, reference_example, adaptation, source_type).as_dict()


def bupt_mock_blueprint() -> dict:
    return {
        "duration_minutes": 90,
        "total_score": 100,
        "distribution": {
            "选择题": "5题 × 4分 = 20分",
            "填空题": "5题 × 4分 = 20分",
            "简答/判断题": "2题 × 10分 = 20分",
            "计算题": "2题 × 20分 = 40分",
        },
        "basis": ["上传试卷题型分布", "考点分布", "教材章节范围", "同类题"],
    }
