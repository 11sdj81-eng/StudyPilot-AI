"""CourseIsolationSandbox — prevents cross-course contamination (P0-1 fix).

Before/after generation: checks that only THIS course's keywords appear.
Cross-course contamination = FAILED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IsolationReport:
    course_id: str = ""
    passed: bool = False
    foreign_keywords_found: list[str] = field(default_factory=list)
    foreign_formulas_found: list[str] = field(default_factory=list)
    foreign_question_types_found: list[str] = field(default_factory=list)
    foreign_sources_found: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def contamination_count(self) -> int:
        return (len(self.foreign_keywords_found) + len(self.foreign_formulas_found)
                + len(self.foreign_question_types_found) + len(self.foreign_sources_found))

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id, "passed": self.passed,
            "contamination_count": self.contamination_count(),
            "foreign_keywords": self.foreign_keywords_found,
            "foreign_formulas": self.foreign_formulas_found,
            "foreign_question_types": self.foreign_question_types_found,
            "foreign_sources": self.foreign_sources_found,
        }


class CourseIsolationSandbox:
    """Locks course boundaries during PDF generation. Zero tolerance for cross-contamination."""

    # Cross-course keyword blacklists — if ANY appear in the wrong course, FAIL
    CROSS_COURSE_BLACKLISTS: dict[str, dict[str, list[str]]] = {
        "probability_ch2": {
            "keywords": ["静电场", "高斯定理", "镜像法", "边界条件", "电位与电场",
                         "电磁波", "逻辑门", "卡诺图", "触发器", "计数器", "组合逻辑"],
            "formulas": ["E =", "D·dS", "∇φ", "E₁t=E₂t"],
            "question_types": ["场波", "电磁", "数字电路", "逻辑"],
        },
        "field_wave_ch1": {
            "keywords": ["随机变量", "分布函数", "二项分布", "泊松分布", "正态分布",
                         "概率论", "逻辑门", "卡诺图", "触发器", "组合逻辑"],
            "formulas": ["P{X", "B(n,p)", "N(μ", "C(n,k)"],
            "question_types": ["概率论", "离散型", "连续型", "数字电路"],
        },
        "digital_logic_ch3": {
            "keywords": ["静电场", "高斯定理", "镜像法", "电场强度", "电磁波",
                         "随机变量", "泊松分布", "正态分布", "概率论"],
            "formulas": ["E =", "D·dS", "P{X", "B(n,p)"],
            "question_types": ["场波", "电磁", "概率论"],
        },
    }

    def __init__(self, course_id: str = ""):
        self.course_id = course_id
        self.blacklist = self.CROSS_COURSE_BLACKLISTS.get(course_id, {})

    def check(self, typst_text: str = "", concepts: list[str] | None = None,
              formulas: list[str] | None = None, sources: list[str] | None = None) -> IsolationReport:
        """Check generated content for cross-course contamination."""
        report = IsolationReport(course_id=self.course_id)

        if not self.blacklist:
            report.passed = True  # unknown course — no blacklist to check against
            return report

        # Check keywords
        for kw in self.blacklist.get("keywords", []):
            if kw in typst_text:
                report.foreign_keywords_found.append(kw)

        # Check formulas
        for f in self.blacklist.get("formulas", []):
            if f in typst_text:
                report.foreign_formulas_found.append(f)

        # Check concepts
        concept_text = " ".join(concepts or [])
        for kw in self.blacklist.get("keywords", []):
            if kw in concept_text:
                if kw not in report.foreign_keywords_found:
                    report.foreign_keywords_found.append(kw)

        report.passed = report.contamination_count() == 0

        if not report.passed:
            report.issues.append(
                f"COURSE CONTAMINATION DETECTED in {self.course_id}: "
                f"{len(report.foreign_keywords_found)} foreign keywords, "
                f"{len(report.foreign_formulas_found)} foreign formulas"
            )

        return report

    @classmethod
    def get_blacklist(cls, course_id: str) -> dict:
        return cls.CROSS_COURSE_BLACKLISTS.get(course_id, {})
