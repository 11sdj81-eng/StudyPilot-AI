"""OptionAnswerConsistencyValidator — P0-3 fix.

Checks that choice options, question stem, and answer all belong to the same course+concept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OptionAnswerReport:
    checked: int = 0
    failed: int = 0
    mismatches: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {"checked": self.checked, "failed": self.failed, "mismatches": self.mismatches, "passed": self.passed}


class OptionAnswerConsistencyValidator:
    """Validates that choice options match the question's course and concept.

    P0-3: Blocks field-wave MockExam from using probability options.
    P0-2: Ensures stem, options, and answer all belong to the same course.
    """

    # Known wrong option-answer pairs that indicate cross-course contamination
    CROSS_COURSE_OPTION_SIGNATURES = {
        "分布函数三性质": "概率论",
        "端点极限必须为 0 和 1": "概率论",
        "概率由密度积分求得": "概率论",
        "线性变换保持正态性不变": "概率论",
        "必须核对公式适用条件和来源": "概率论",
        "考频可以无来源估计": "概率论",
        "F(-∞)=0": "概率论",
        "F(x) 左连续": "概率论",
        "泊松": "概率论",
        "正态": "概率论",
        "密度": "概率论",
        "二项分布": "概率论",
        "高斯定理": "电磁场",
        "电位": "电磁场",
        "边界条件": "电磁场",
        "镜像法": "电磁场",
        "静电场": "电磁场",
        "逻辑门": "数字电路",
        "卡诺图": "数字电路",
        "触发器": "数字电路",
        "组合逻辑": "数字电路",
    }

    # Concept keywords that should match between stem and answer
    STEM_ANSWER_BRIDGE_KEYWORDS = {
        "概率论": ["随机变量", "分布", "概率", "密度", "期望", "方差", "二项", "泊松", "正态", "指数", "均匀", "F(x)", "P{X"],
        "电磁场": ["电场", "磁场", "电荷", "高斯", "电位", "镜像", "边界", "导体", "介质", "通量", "静电场"],
        "数字电路": ["逻辑", "门", "卡诺", "真值表", "触发器", "计数器", "状态机", "组合", "时序", "化简", "译码", "加法"],
    }

    def __init__(self, course_id: str = ""):
        self.course_id = course_id
        # Determine the expected course from course_id
        self.expected_course = ""
        if "probability" in course_id or "概率" in course_id:
            self.expected_course = "概率论"
        elif "field_wave" in course_id or "电磁" in course_id or "场波" in course_id:
            self.expected_course = "电磁场"
        elif "digital" in course_id or "数电" in course_id or "数字" in course_id:
            self.expected_course = "数字电路"

    def validate(self, questions: list[dict]) -> OptionAnswerReport:
        report = OptionAnswerReport()
        for q in questions:
            stem = str(q.get("stem", q.get("problem", "")))
            answer = str(q.get("answer", q.get("standard_answer", "")))
            options = str(q.get("options", ""))
            qtype = str(q.get("type", q.get("question_type", "")))

            if "选择" not in qtype:
                continue

            report.checked += 1

            # P0-2: Check if answer/options contain cross-course signatures
            for sig, course in self.CROSS_COURSE_OPTION_SIGNATURES.items():
                if (sig in answer or sig in options):
                    # If we know the expected course, check for mismatch
                    if self.expected_course and course != self.expected_course:
                        report.failed += 1
                        report.mismatches.append({
                            "question": stem[:80],
                            "issue": f"跨课程污染：答案/选项包含{sig}（属于{course}，非{self.expected_course}）",
                            "severity": "P0_CROSS_COURSE_CONTAMINATION",
                        })

            # P0-2: Check stem-keyword-to-answer consistency
            # Only flag if answer contains keywords from a DIFFERENT course (true contamination)
            if self.expected_course:
                bridge_kw = self.STEM_ANSWER_BRIDGE_KEYWORDS.get(self.expected_course, [])
                # Check if answer has keywords from OTHER courses
                for other_course, other_kw in self.STEM_ANSWER_BRIDGE_KEYWORDS.items():
                    if other_course == self.expected_course:
                        continue
                    answer_has_other_kw = any(kw in answer for kw in other_kw)
                    if answer_has_other_kw and len(answer) > 2:
                        report.failed += 1
                        report.mismatches.append({
                            "question": stem[:80],
                            "issue": f"跨课程污染：答案包含{other_course}关键词",
                            "severity": "P0_CROSS_COURSE_CONTAMINATION",
                        })

            # Check that answer letter actually exists in options
            letter_match = re.search(r'\b([A-D])\b', answer)
            if letter_match:
                letter = letter_match.group(1)
                if letter not in options and len(options) > 5:
                    report.failed += 1
                    report.mismatches.append({
                        "question": stem[:60], "answer_letter": letter,
                        "issue": f"答案字母 {letter} 不在选项中",
                    })

        report.passed = report.failed == 0
        return report
