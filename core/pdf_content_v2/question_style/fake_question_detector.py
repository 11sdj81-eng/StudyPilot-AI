"""FakeQuestionDetector — identifies non-exam-style questions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeQuestionResult:
    is_fake: bool
    fake_reasons: list[str] = field(default_factory=list)
    severity: str = "none"       # none / low / medium / high / critical
    suggestion: str = ""
    can_rewrite: bool = True

    def to_dict(self) -> dict:
        return {
            "is_fake": self.is_fake, "fake_reasons": self.fake_reasons,
            "severity": self.severity, "suggestion": self.suggestion,
            "can_rewrite": self.can_rewrite,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Fake question patterns — categorized by type
# ═══════════════════════════════════════════════════════════════════════════

GENERIC_PROMPT_PATTERNS = [
    (r"请填写.*公式", "题干为指令式填空，非真实考试题格式", "high"),
    (r"请说明.*重要性", "说明题非客观题格式", "high"),
    (r"请谈谈.*理解", "开放式问答不适合客观题", "high"),
    (r"请掌握.*公式", "指令式题目非考题", "medium"),
    (r"请列举.*概念", "列举题缺少考试上下文", "medium"),
    (r"请简述.*内容", "简述题非标准题型", "medium"),
    (r"请计算一个.*概率", "缺少具体数据，题干笼统", "medium"),
    (r"请判断.*是否正确", "缺少具体条件和选项", "medium"),
]

NO_SPECIFIC_DATA_PATTERNS = [
    (r"^设.*分布.*求概率$", "缺少具体参数和数据", "medium"),
    (r"^已知.*随机变量.*求.*分布$", "缺少分布类型和参数", "medium"),
]

TEMPLATE_OPTION_PATTERNS = [
    (r"必须核对公式适用条件.*来源", "选项为元认知模板，非知识考查", "critical"),
    (r"考频可以无来源估计", "选项无实际考查意义", "high"),
    (r"只写结论不需要步骤", "选项为规范宣导，非知识题", "high"),
    (r"与教材例题无关", "选项无区分度", "high"),
]

OPEN_ENDED_IN_OBJECTIVE = [
    (r"请回答.*看法", "客观题中不应出现开放式回答", "critical"),
    (r"你认为.*如何", "主观题格式不适合 MockExam", "critical"),
]

NO_SCORE_SIGNIFICANCE = [
    (r"^\s*$", "空白题目", "critical"),
]


class FakeQuestionDetector:
    """Detect questions that don't look like real exam questions.

    Checks 13 categories of fake question patterns.
    """

    def detect(self, question: dict | str, qtype: str = "") -> FakeQuestionResult:
        """Detect if a question is fake. Returns FakeQuestionResult."""
        if isinstance(question, dict):
            stem = str(question.get("stem", question.get("problem", "")))
            qtype = str(question.get("type", question.get("question_type", qtype)))
            answer = str(question.get("answer", question.get("standard_answer", "")))
        else:
            stem = str(question)
            answer = ""

        reasons: list[str] = []
        severity = "none"

        # ── 1. Generic prompt patterns ──
        for pattern, reason, sev in GENERIC_PROMPT_PATTERNS:
            if re.search(pattern, stem):
                reasons.append(reason)
                if _severity_gt(sev, severity):
                    severity = sev

        # ── 2. No specific data ──
        has_numbers = bool(re.search(r'\d+', stem))
        has_condition = bool(re.search(r'设|已知|若|当|其中', stem))
        has_goal = bool(re.search(r'求|计算|判断|证明|写出', stem))
        if not has_numbers and not has_condition and len(stem) > 15:
            reasons.append("缺少具体数据和条件")
            if _severity_gt("medium", severity):
                severity = "medium"
        if not has_goal and len(stem) > 15 and qtype not in ["填空题"]:
            reasons.append("缺少明确求解目标")
            if _severity_gt("medium", severity):
                severity = "medium"

        # ── 3. Template option patterns (choice questions) ──
        if "选择" in qtype:
            for pattern, reason, sev in TEMPLATE_OPTION_PATTERNS:
                if re.search(pattern, stem):
                    reasons.append(reason)
                    if _severity_gt(sev, severity):
                        severity = sev

        # ── 4. Open-ended in objective ──
        for pattern, reason, sev in OPEN_ENDED_IN_OBJECTIVE:
            if re.search(pattern, stem):
                reasons.append(reason)
                if _severity_gt(sev, severity):
                    severity = sev

        # ── 5. Keyword-only stem (no context) ──
        # If the stem is just a concept name with no conditions
        if len(stem) < 10 and not has_numbers:
            reasons.append("题干过短，缺少上下文")
            if _severity_gt("medium", severity):
                severity = "medium"

        # ── 6. Answer check: blank or self-referential ──
        if answer and len(answer.strip()) < 3:
            reasons.append("答案过短或为空")
            if _severity_gt("high", severity):
                severity = "high"

        # ── 7. Prompt-like question (starts with imperative) ──
        if re.match(r'^(请|应该|必须|可以|不要)', stem):
            reasons.append("题干以指令动词开头，像 prompt 不像试卷")
            if _severity_gt("medium", severity):
                severity = "medium"

        is_fake = len(reasons) > 0
        suggestion = self._build_suggestion(reasons, qtype) if is_fake else ""
        can_rewrite = severity != "critical"  # critical may need human review

        return FakeQuestionResult(
            is_fake=is_fake, fake_reasons=reasons,
            severity=severity, suggestion=suggestion,
            can_rewrite=can_rewrite,
        )

    def detect_all(self, questions: list[dict]) -> tuple[list[dict], list[FakeQuestionResult]]:
        """Detect fake questions in a list. Returns (all_results, fake_only)."""
        results = []
        fakes = []
        for q in questions:
            r = self.detect(q)
            results.append({"question": q, "result": r})
            if r.is_fake:
                fakes.append(r)
        return results, fakes

    def _build_suggestion(self, reasons: list[str], qtype: str) -> str:
        """Build rewrite suggestion based on fake reasons."""
        if any("指令" in r for r in reasons):
            return "改写为以'设'/'已知'/'若'开头的条件+求解句式"
        if any("数据" in r for r in reasons):
            return f"增加具体数值参数和明确求解目标（{qtype}需具体条件）"
        if any("选项" in r for r in reasons):
            return "将选项替换为考查知识点判断的具体内容（4个互斥选项）"
        if any("模板" in r for r in reasons):
            return "将模板句式替换为具体数学/物理条件描述"
        return "增加具体数据、条件和明确求解目标"


def _severity_gt(a: str, b: str) -> bool:
    order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return order.get(a, 0) > order.get(b, 0)
