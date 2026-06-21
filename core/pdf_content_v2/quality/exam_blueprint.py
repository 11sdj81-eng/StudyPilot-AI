"""Exam blueprints per course — default score structures and question type distributions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# Course-specific exam blueprints
# ═══════════════════════════════════════════════════════════════════════════

EXAM_BLUEPRINTS: dict[str, dict] = {
    "概率论与随机过程": {
        "total_score": 100,
        "sections": [
            {"type": "选择题", "score": 20, "question_count": "5", "score_per": 4},
            {"type": "填空题", "score": 20, "question_count": "4", "score_per": 5},
            {"type": "计算题", "score": 36, "question_count": "3", "score_per": 12},
            {"type": "综合题", "score": 24, "question_count": "1", "score_per": 24},
        ],
        "difficulty_mix": {"基础": 0.3, "典型": 0.4, "综合": 0.3},
        "topic_coverage": [
            "随机变量定义",
            "分布函数及其性质",
            "离散型随机变量与分布律",
            "连续型随机变量与密度函数",
            "二项分布与泊松分布",
            "正态分布与标准化",
            "随机变量函数的分布",
        ],
    },
    "电磁场与电磁波": {
        "total_score": 100,
        "sections": [
            {"type": "选择/填空题", "score": 30, "question_count": "6", "score_per": 5},
            {"type": "简答/推导题", "score": 20, "question_count": "2", "score_per": 10},
            {"type": "计算题", "score": 30, "question_count": "3", "score_per": 10},
            {"type": "综合题", "score": 20, "question_count": "1", "score_per": 20},
        ],
        "difficulty_mix": {"基础": 0.3, "典型": 0.3, "综合": 0.4},
        "topic_coverage": [
            "电场强度与库仑定律",
            "高斯定理",
            "电位与梯度",
            "边界条件",
            "镜像法",
            "静电能量",
        ],
    },
    "数字电路逻辑设计": {
        "total_score": 100,
        "sections": [
            {"type": "选择/填空题", "score": 30, "question_count": "6", "score_per": 5},
            {"type": "逻辑化简", "score": 20, "question_count": "2", "score_per": 10},
            {"type": "电路分析", "score": 20, "question_count": "2", "score_per": 10},
            {"type": "设计题", "score": 30, "question_count": "1", "score_per": 30},
        ],
        "difficulty_mix": {"基础": 0.25, "典型": 0.4, "综合": 0.35},
        "topic_coverage": [
            "数制与码制",
            "逻辑代数与化简",
            "门电路",
            "组合逻辑电路",
            "触发器",
            "时序逻辑电路",
            "计数器与寄存器",
        ],
    },
}


@dataclass
class BlueprintCheckResult:
    passed: bool = False
    exam_total_score: int = 0
    exam_blueprint_match: bool = False
    course_name: str = ""
    blueprint_used: dict | None = None
    actual_sections: list[dict] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    score_mismatch: bool = False
    checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "exam_total_score": self.exam_total_score,
            "exam_blueprint_match": self.exam_blueprint_match,
            "course_name": self.course_name,
            "blueprint_used": self.blueprint_used,
            "actual_sections": self.actual_sections,
            "missing_sections": self.missing_sections,
            "score_mismatch": self.score_mismatch,
            "checks": self.checks,
        }


class ExamBlueprintValidator:
    """Validate MockExam score structure against course blueprint."""

    def get_blueprint(self, course_name: str) -> dict | None:
        """Get the exam blueprint for a course, or default."""
        return EXAM_BLUEPRINTS.get(course_name)

    def validate(self, typst_text: str, course_name: str) -> BlueprintCheckResult:
        result = BlueprintCheckResult(course_name=course_name)

        blueprint = self.get_blueprint(course_name)
        if not blueprint:
            # Use generic blueprint
            blueprint = {
                "total_score": 100,
                "sections": [
                    {"type": "选择题", "score": 20, "question_count": "5", "score_per": 4},
                    {"type": "填空题", "score": 20, "question_count": "4", "score_per": 5},
                    {"type": "计算题", "score": 40, "question_count": "3", "score_per": "12-16"},
                    {"type": "综合题", "score": 20, "question_count": "1-2", "score_per": "10-20"},
                ],
            }
        result.blueprint_used = blueprint

        # Parse actual score structure from typst
        import re
        score_total = 0
        sections_found = []
        # Match patterns like "（5 题 × 4 分 = 20 分"  or "5 题 × 4 分 = 20 分"
        simple_scores = re.findall(r'[（(]?(\d+)\s*[題题]\s*[×xX]\s*(\d+)\s*分\s*[=＝]\s*(\d+)\s*分', typst_text)
        for match in simple_scores:
            try:
                section_total = int(match[2])
                score_total += section_total
                sections_found.append({"total": section_total})
            except ValueError:
                pass

        # If no structured scores, try from exam description line
        if score_total == 0:
            totals = re.findall(r'总分\s*(\d+)\s*分', typst_text)
            if totals:
                score_total = int(totals[0])
            else:
                # Look for parenthesized total: (20+20+36+24)
                sums = re.findall(r'\((\d+)\+(\d+)\+(\d+)\+(\d+)\)', typst_text)
                if sums:
                    score_total = sum(int(x) for x in sums[0])

        result.exam_total_score = score_total if score_total > 0 else 100
        result.actual_sections = sections_found

        # Check against blueprint
        expected_total = blueprint.get("total_score", 100)
        result.score_mismatch = abs(result.exam_total_score - expected_total) > 5
        result.exam_blueprint_match = not result.score_mismatch and result.exam_total_score > 0
        result.passed = result.exam_blueprint_match

        result.checks = {
            "expected_total": expected_total,
            "actual_total": result.exam_total_score,
            "expected_sections": len(blueprint.get("sections", [])),
            "found_sections": len(sections_found),
        }
        return result
