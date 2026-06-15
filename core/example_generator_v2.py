"""Metadata-first local example pool for v1.1 PDFs."""

from __future__ import annotations

from core.exam_mining_engine import mine_exam_signals


def electrostatics_question_pool() -> list[dict]:
    signals = mine_exam_signals()
    return [
        {
            "id": "L1",
            "title": "均匀带电球体的高斯面分段题",
            "metadata": signals[1].as_dict(),
            "needs_diagram": "高斯面",
        },
        {
            "id": "L2",
            "title": "电位函数求场与负号判断题",
            "metadata": signals[0].as_dict(),
            "needs_diagram": "等位线",
        },
        {
            "id": "L3",
            "title": "接地导体平面镜像法综合题",
            "metadata": signals[3].as_dict(),
            "needs_diagram": "镜像法",
        },
        {
            "id": "L4",
            "title": "介质分界面边界条件判断题",
            "metadata": signals[2].as_dict(),
            "needs_diagram": "边界条件",
        },
    ]
