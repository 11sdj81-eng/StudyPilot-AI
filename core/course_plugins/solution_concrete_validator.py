"""SolutionConcreteValidator — P0-4 fix. Rejects template/generic answers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TEMPLATE_ANSWER_PATTERNS = [
    "按题型识别、公式选择、逐步推导、标准答案四步作答",
    "逐步推导",
    "见教材",
    "参考教材",
    "自行推导",
    "略",
    "同上",
]

CONCRETE_REQUIREMENTS = [
    "有具体公式代入",
    "有具体数值结论",
    "有评分点",
    "不能只有套路话",
]


@dataclass
class SolutionConcreteReport:
    checked: int = 0
    template_answers: int = 0
    concrete_answers: int = 0
    issues: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "checked": self.checked, "template_answers": self.template_answers,
            "concrete_answers": self.concrete_answers, "issues": self.issues,
            "passed": self.passed,
        }


class SolutionConcreteValidator:
    """Validates that answers are concrete, not template/generic text.

    P0-4: "按题型识别、公式选择、逐步推导、标准答案四步作答" is rejected.
    """

    def validate(self, questions: list[dict]) -> SolutionConcreteReport:
        report = SolutionConcreteReport()
        for q in questions:
            answer = str(q.get("answer", q.get("standard_answer", "")))
            qtype = str(q.get("type", q.get("question_type", "")))
            report.checked += 1

            is_template = False
            for pattern in TEMPLATE_ANSWER_PATTERNS:
                if pattern in answer and len(answer) < 50:
                    report.template_answers += 1
                    report.issues.append({
                        "question": str(q.get("stem", q.get("problem", "")))[:60],
                        "answer": answer[:60], "issue": f"模板答案: {pattern}",
                    })
                    is_template = True
                    break

            if not is_template:
                # Check concreteness
                has_numbers = any(c.isdigit() for c in answer)
                has_formula = any(kw in answer for kw in ["=", "P{", "F(", "f(", "∫", "E(", "D("])
                if has_numbers or has_formula or len(answer) > 40:
                    report.concrete_answers += 1

        report.passed = report.template_answers == 0
        return report
