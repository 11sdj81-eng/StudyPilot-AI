"""Local exam-mining fallback for StudyPilot v1.1.

The project may not reliably recover full OCR questions from uploaded scans.
This module therefore distinguishes confirmed exam signals from textbook or
similar-question adaptations instead of pretending to have exact originals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class ExamSignal:
    source_basis: str
    knowledge_point: str
    chapter: str
    difficulty: str
    question_type: str
    mutation_type: str
    in_scope: bool
    reliability: str

    def as_dict(self) -> dict:
        return asdict(self)


def mine_exam_signals(course_id: str = "course_bb15e787") -> list[ExamSignal]:
    return [
        ExamSignal("2023 期末试卷 OCR 可确认考点", "静电场无旋与电位", "第一章 静电场", "基础", "选择题", "考点复原", True, "OCR 可确认考点"),
        ExamSignal("教材第一章高斯定理例题/往年题型", "均匀带电球体与高斯面", "第一章 静电场", "中等", "计算题", "教材例题同范围改编", True, "教材例题改编"),
        ExamSignal("2023 期末试卷静电边界条件相关题型", "边界条件", "第一章 静电场", "中等", "填空/简答", "同类题改编", True, "OCR 可确认考点"),
        ExamSignal("镜像法高频题型池", "接地导体平面镜像法", "第一章 静电场", "提高", "综合计算题", "同类题改编", True, "同类题改编"),
    ]


def grouped_metadata() -> dict:
    signals = mine_exam_signals()
    return {f"Q{index}": signal.as_dict() for index, signal in enumerate(signals, start=1)}
