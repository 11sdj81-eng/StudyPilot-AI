"""BUPT-style mock exam blueprint with source metadata."""

from __future__ import annotations

from core.example_generator_v2 import electrostatics_question_pool


def bupt_style_mock_blueprint_v2() -> dict:
    pool = electrostatics_question_pool()
    return {
        "style": "BUPT Style Mock Exam",
        "source_basis": "上传期末试卷题型结构 + 教材第一章例题/习题范围 + 本地同类题池",
        "question_mix": {
            "choice": 6,
            "blank": 5,
            "short_answer": 2,
            "calculation": 2,
            "comprehensive": 1,
        },
        "difficulty_distribution": {"基础": 0.35, "中等": 0.45, "提高": 0.20},
        "questions": pool,
        "constraints": [
            "A/B/C/D 分行",
            "填空题应用化",
            "至少一道综合计算题",
            "每题带 source_basis",
            "全部题目在第一章静电场范围内",
        ],
    }
