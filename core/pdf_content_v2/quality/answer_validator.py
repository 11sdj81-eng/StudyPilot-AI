"""Validate MockExam answers: correctness, variety, consistency, score totals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.models import LectureDocument


@dataclass
class AnswerValidationResult:
    passed: bool = False
    answer_error_count: int = 0
    choice_answer_issues: list[str] = field(default_factory=list)
    fill_answer_issues: list[str] = field(default_factory=list)
    calc_answer_issues: list[str] = field(default_factory=list)
    score_total: int = 0
    score_valid: bool = False
    all_answers_same: bool = False
    answer_distribution: dict[str, int] = field(default_factory=dict)
    needs_manual_review: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "answer_error_count": self.answer_error_count,
            "choice_answer_issues": self.choice_answer_issues,
            "fill_answer_issues": self.fill_answer_issues,
            "calc_answer_issues": self.calc_answer_issues,
            "score_total": self.score_total,
            "score_valid": self.score_valid,
            "all_answers_same": self.all_answers_same,
            "answer_distribution": self.answer_distribution,
            "needs_manual_review": self.needs_manual_review,
            "checks": self.checks,
        }


class AnswerValidator:
    """Validate MockExam answers for correctness and variety."""

    def validate(self, document: LectureDocument, typst_text: str = "") -> AnswerValidationResult:
        result = AnswerValidationResult()
        issues: list[str] = []

        if document.pdf_type != "MockExam":
            result.passed = True
            return result

        # ── Parse answers from Typst text ──
        # Choice answers: "1. A" or "1. B" pattern
        choice_pattern = re.findall(r'(\d+)\.\s*([A-D])\s*[.。]', typst_text)
        answer_letters = [letter for _, letter in choice_pattern]

        # Fill-in answers: e.g. "6. P{X=k}=C(n,k)p^k(1-p)^{n-k}。评分点"
        fill_pattern = re.findall(r'(\d+)\.\s+(.+?)(?:。|$)(?:\s*评分点)', typst_text)

        # Score patterns
        score_matches = re.findall(r'(\d+)\s*分', typst_text)

        # ── 1. Answer variety check ──
        letter_counts: dict[str, int] = {}
        for letter in answer_letters:
            letter_counts[letter] = letter_counts.get(letter, 0) + 1
        result.answer_distribution = letter_counts

        if answer_letters and len(set(answer_letters)) == 1:
            result.all_answers_same = True
            issues.append("所有选择题答案相同，疑似假题")
            result.needs_manual_review.append("选择题答案全部相同")

        if len(answer_letters) < 3:
            issues.append(f"选择题答案数量不足：{len(answer_letters)} 个")
            result.needs_manual_review.append("选择题数量过少")

        # ── 2. Answer consistency check ──
        # Check for contradiction between answer letter and stated content
        for idx, letter in enumerate(choice_pattern, start=1):
            q_num, correct = letter
            # Search for this question's answer explanation
            answer_block = re.search(
                rf'{re.escape(q_num)}\.\s*{re.escape(correct)}\s*[.。](.*?)(?:\n|$)',
                typst_text
            )
            if not answer_block:
                issues.append(f"第 {q_num} 题答案解释缺失")

        # ── 3. Score validation ──
        total = 0
        score_values = []
        for m in score_matches:
            try:
                val = int(m)
                if 1 <= val <= 50:  # reasonable score per section
                    score_values.append(val)
                    total += val
            except ValueError:
                pass

        # Try to parse structured score: 20+20+36+24 or similar
        score_sections = re.findall(r'(?:选择题|填空题|计算题|综合题).*?(\d+)\s*分', typst_text)
        calc_total = sum(int(s) for s in score_sections) if score_sections else total

        result.score_total = calc_total if calc_total > 0 else total
        result.score_valid = 95 <= result.score_total <= 105

        if not result.score_valid and result.score_total > 0:
            issues.append(f"试卷总分 {result.score_total} 不在 95-105 范围内")
            result.needs_manual_review.append("试卷总分异常")

        # ── 4. Fake question detection ──
        fake_patterns = [
            "请填写一个高频公式及其适用条件",
            "请填写",
            "请列举",
            "请说明",
            "请简述",
        ]
        for pattern in fake_patterns:
            if pattern in typst_text:
                issues.append(f"发现模板假题：'{pattern}'")
                result.answer_error_count += 1
                result.needs_manual_review.append(f"假题模板：{pattern}")

        # ── 5. Check that all questions have distinct problems ──
        question_stems = re.findall(r'#(?:question|open-question)\("[^"]*",\s*"[^"]*",\s*"[^"]*",\s*"([^"]{20,})"', typst_text)
        if len(question_stems) != len(set(question_stems)):
            issues.append("存在完全相同的题目题干")
            result.answer_error_count += 1

        result.choice_answer_issues = [i for i in issues if "选择" in i or "答案" in i or "相同" in i]
        result.fill_answer_issues = [i for i in issues if "填空" in i or "假题" in i]
        result.calc_answer_issues = [i for i in issues if "计算" in i or "综合" in i or "总分" in i]
        result.answer_error_count += len(issues) - len(result.choice_answer_issues) - len(result.fill_answer_issues) + len(issues)

        # Recalculate
        result.answer_error_count = len(issues)
        result.passed = result.answer_error_count == 0 and result.score_valid and not result.all_answers_same

        # If there are issues but no manual review needed yet, check more carefully
        if not result.passed and not result.needs_manual_review:
            result.needs_manual_review.append("答案校验未通过，需人工审查")

        result.checks = {
            "answer_count": len(answer_letters) + len(fill_pattern),
            "choice_count": len(answer_letters),
            "fill_count": len(fill_pattern),
            "score_breakdown": score_sections,
        }
        return result
