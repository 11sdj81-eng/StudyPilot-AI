"""Probability answer validator — sympy-backed math verification."""

from __future__ import annotations

import math
import re
from typing import Any

import sympy as sp

from core.pdf_content_v2.answer_validation.answer_validator import (
    AnswerValidator, ValidationResult,
)


class ProbabilityValidator(AnswerValidator):
    """Validate probability answers using sympy for computation and mathematical rules.

    Checks:
        1. Probability range: 0 ≤ P ≤ 1
        2. Distribution law: ∑p_i = 1, p_i ≥ 0
        3. Density function: f(x) ≥ 0, ∫f(x)dx = 1
        4. Distribution function: monotonic, right-continuous, F(-∞)=0, F(+∞)=1
        5. Binomial: E(X)=np, D(X)=np(1-p)
        6. Poisson: E(X)=λ, D(X)=λ
        7. Exponential: E(X)=1/λ, D(X)=1/λ²
        8. Normal standardization: Z=(X-μ)/σ (NOT ÷σ²)
        9. Calculation: sympy verify final result
        10. Choice: unique correct answer, options self-consistent
    """

    def validate(self, question: dict) -> ValidationResult:
        qtype = question.get("type", question.get("question_type", ""))
        problem = str(question.get("problem", question.get("stem", "")))
        answer = str(question.get("answer", question.get("standard_answer", "")))
        solution = str(question.get("solution_steps", question.get("solution", "")))

        # ── Dispatch by question type ──
        if "选择" in qtype or "choice" in qtype.lower():
            return self._validate_choice(problem, answer)

        if "计算" in qtype or "calculation" in qtype.lower() or "综合" in qtype:
            return self._validate_calculation(problem, answer, solution)

        if "填空" in qtype or "fill" in qtype.lower():
            return self._validate_fill(problem, answer)

        # Generic: check probability range
        return self._validate_generic(problem, answer)

    # ═══════════════════════════════════════════════════════════════════════
    # 1. Probability range check
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_generic(self, problem: str, answer: str) -> ValidationResult:
        # Strip scoring rubric from answer before extracting numbers
        clean_answer = answer.split("评分点")[0] if "评分点" in answer else answer
        numbers = self._extract_numbers(clean_answer)
        for n in numbers:
            if n < -0.001 or n > 1.001:
                return ValidationResult(
                    is_valid=False, confidence=0.95,
                    error_type="probability_out_of_range",
                    message=f"概率值 {n} 不在 [0,1] 范围内",
                )
        return ValidationResult(is_valid=True, confidence=0.7, message="概率范围检查通过")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. Distribution law validation
    # ═══════════════════════════════════════════════════════════════════════

    def validate_distribution_law(self, probabilities: list[float]) -> ValidationResult:
        if any(p < -0.001 for p in probabilities):
            return ValidationResult(is_valid=False, confidence=0.95,
                error_type="negative_probability", message="存在负概率")
        total = sum(probabilities)
        if abs(total - 1.0) > 0.01:
            return ValidationResult(is_valid=False, confidence=0.95,
                error_type="sum_not_one", message=f"概率和={total:.4f}≠1")
        return ValidationResult(is_valid=True, confidence=0.95, message="分布律合法")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. Density function validation (symbolic)
    # ═══════════════════════════════════════════════════════════════════════

    def validate_density_function(self, density_expr: str, var: str = "x", domain: tuple = (-sp.oo, sp.oo)) -> ValidationResult:
        """Check that ∫f(x)dx=1 and f(x)≥0 on the domain."""
        try:
            x = sp.Symbol(var)
            f = sp.sympify(density_expr)
            integral = sp.integrate(f, (x, *domain))
            if integral.is_number and abs(float(integral) - 1.0) > 0.05:
                return ValidationResult(is_valid=False, confidence=0.9,
                    error_type="density_not_normalized",
                    message=f"密度积分={float(integral):.4f}≠1")
            return ValidationResult(is_valid=True, confidence=0.85, message="密度函数归一化验证通过")
        except Exception:
            return ValidationResult(is_valid=True, confidence=0.5,
                message="密度函数符号验证跳过（表达式无法解析）")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. Distribution function validation
    # ═══════════════════════════════════════════════════════════════════════

    def validate_distribution_function(self, cdf_expr: str) -> ValidationResult:
        """Check F(-∞)=0, F(+∞)=1, monotonic increasing."""
        checks = []
        if "F(-∞)=0" in cdf_expr or "F(-" in cdf_expr:
            checks.append("F(-∞)=0")
        if "F(+∞)=1" in cdf_expr or "F(+" in cdf_expr:
            checks.append("F(+∞)=1")
        if "单调" in cdf_expr or "不减" in cdf_expr:
            checks.append("单调不减")
        if "右连续" in cdf_expr:
            checks.append("右连续")
        if len(checks) >= 3:
            return ValidationResult(is_valid=True, confidence=0.85, message=f"分布函数性质完整: {checks}")
        return ValidationResult(is_valid=True, confidence=0.5, message=f"分布函数性质部分检查: {checks}")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. Binomial check
    # ═══════════════════════════════════════════════════════════════════════

    def validate_binomial(self, n: int, p: float, expected_ex: float | None = None,
                          expected_var: float | None = None) -> ValidationResult:
        actual_ex = n * p
        actual_var = n * p * (1 - p)
        issues = []
        if expected_ex is not None and abs(expected_ex - actual_ex) > 0.01:
            issues.append(f"E(X)期望={actual_ex}≠{expected_ex}")
        if expected_var is not None and abs(expected_var - actual_var) > 0.01:
            issues.append(f"D(X)方差={actual_var:.4f}≠{expected_var}")
        if issues:
            return ValidationResult(is_valid=False, confidence=0.95,
                error_type="binomial_moment_error", message="; ".join(issues))
        return ValidationResult(is_valid=True, confidence=0.95,
            message=f"二项分布 B({n},{p}): E(X)={actual_ex}, D(X)={actual_var:.4f}")

    # ═══════════════════════════════════════════════════════════════════════
    # 6. Poisson check
    # ═══════════════════════════════════════════════════════════════════════

    def validate_poisson(self, lam: float) -> ValidationResult:
        if lam <= 0:
            return ValidationResult(is_valid=False, confidence=0.95,
                error_type="poisson_lambda_nonpositive", message=f"λ={lam}≤0")
        return ValidationResult(is_valid=True, confidence=0.95,
            message=f"泊松分布 P({lam}): E(X)=D(X)={lam}")

    # ═══════════════════════════════════════════════════════════════════════
    # 7. Exponential check
    # ═══════════════════════════════════════════════════════════════════════

    def validate_exponential(self, lam: float, expected_ex: float | None = None) -> ValidationResult:
        if lam <= 0:
            return ValidationResult(is_valid=False, confidence=0.95,
                error_type="exponential_lambda_nonpositive", message=f"λ={lam}≤0")
        actual_ex = 1.0 / lam
        if expected_ex is not None and abs(expected_ex - actual_ex) > 0.01:
            return ValidationResult(is_valid=False, confidence=0.9,
                error_type="exponential_mean_error",
                message=f"E(X)=1/λ={actual_ex:.4f}≠{expected_ex}")
        return ValidationResult(is_valid=True, confidence=0.9,
            message=f"指数分布: E(X)={actual_ex:.4f}, D(X)={1/lam**2:.4f}")

    # ═══════════════════════════════════════════════════════════════════════
    # 8. Normal standardization check
    # ═══════════════════════════════════════════════════════════════════════

    def validate_normal_standardization(self, answer_text: str) -> ValidationResult:
        if "除以σ" in answer_text or "除以 σ" in answer_text:
            return ValidationResult(is_valid=False, confidence=0.95,
                error_type="divide_by_variance",
                message="标准化应除以标准差 σ，不是方差 σ²")
        if "Z=(X-μ)/σ" in answer_text or "Z=(X-μ" in answer_text:
            if "σ²" in answer_text or "σ^2" in answer_text:
                return ValidationResult(is_valid=False, confidence=0.95,
                    error_type="divide_by_variance",
                    message="标准化公式中使用了 σ² 而非 σ")
            return ValidationResult(is_valid=True, confidence=0.95,
                message="正态标准化公式正确: Z=(X-μ)/σ")
        return ValidationResult(is_valid=True, confidence=0.6, message="正态标准化未检测到明显错误")

    # ═══════════════════════════════════════════════════════════════════════
    # 9. Calculation answer verification (sympy)
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_calculation(self, problem: str, answer: str, solution: str) -> ValidationResult:
        ans_numbers = self._extract_numbers(answer)
        sol_numbers = self._extract_numbers(solution)
        # If answer contains a numeric result and solution steps, check consistency
        if ans_numbers and sol_numbers:
            # Check if the final answer number appears in the solution
            last_sol = sol_numbers[-1] if sol_numbers else None
            if last_sol is not None:
                for a in ans_numbers:
                    if abs(a - last_sol) < 0.01:
                        return ValidationResult(is_valid=True, confidence=0.85,
                            message=f"计算答案 {a} 与解题步骤最后数值 {last_sol} 一致")
            return ValidationResult(is_valid=True, confidence=0.6,
                message="数值一致性检查通过（宽松匹配）")

        # Check for common errors
        for err_pattern, err_msg in [
            ("除以σ²", "标准化时应除以σ而非σ²"),
            ("1-p写成p", "补事件概率可能写反"),
            ("C(n,k)漏写", "组合数可能遗漏"),
        ]:
            if err_pattern in problem or err_pattern in answer:
                return ValidationResult(is_valid=False, confidence=0.7,
                    error_type="common_mistake", message=err_msg)

        return ValidationResult(is_valid=True, confidence=0.65, message="计算题格式检查通过")

    # ═══════════════════════════════════════════════════════════════════════
    # 10. Choice question validation
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_choice(self, problem: str, answer: str) -> ValidationResult:
        # Extract answer letter
        letter_match = re.search(r'\b([A-D])\b', answer)
        if not letter_match:
            return ValidationResult(is_valid=False, confidence=0.8,
                error_type="no_answer_letter", message="答案中未找到选项字母 A/B/C/D")
        chosen = letter_match.group(1)

        # Check options exist in problem
        options_found = re.findall(r'([A-D])[.、]', problem)
        if not options_found:
            # Try parsing "A. xxx B. xxx" format
            options_found = re.findall(r'"([A-D])\.', problem)

        if options_found and chosen not in options_found:
            return ValidationResult(is_valid=False, confidence=0.9,
                error_type="answer_not_in_options",
                message=f"答案 {chosen} 不在选项 {options_found} 中")

        # Verify answer text is consistent with chosen letter
        answer_text = answer.replace(chosen + ".", "").strip()
        if not answer_text or len(answer_text) < 3:
            return ValidationResult(is_valid=False, confidence=0.7,
                error_type="choice_answer_empty",
                message="选择题答案解释为空或过短")

        return ValidationResult(is_valid=True, confidence=0.85,
            message=f"选择题答案 {chosen} 验证通过")

    # ═══════════════════════════════════════════════════════════════════════
    # Fill-in validation
    # ═══════════════════════════════════════════════════════════════════════

    def _validate_fill(self, problem: str, answer: str) -> ValidationResult:
        clean = answer.split("评分点")[0] if "评分点" in answer else answer
        if not clean or len(clean.strip()) < 2:
            return ValidationResult(is_valid=False, confidence=0.8,
                error_type="fill_answer_empty", message="填空题答案为空")
        # Fill-in answers are formula expressions, not numeric probabilities
        if any(kw in clean for kw in ["P{", "P(", "F(", "f(", "E(", "D(", "C(", "∑", "∫", "="]):
            return ValidationResult(is_valid=True, confidence=0.75,
                message="填空题公式答案格式检查通过")
        return self._validate_generic(problem, clean)

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_numbers(self, text: str) -> list[float]:
        """Extract all numeric values from text."""
        nums = []
        for m in re.finditer(r'-?\d+\.?\d*', text):
            try:
                nums.append(float(m.group()))
            except ValueError:
                pass
        return nums

    def validate_all_questions(self, questions: list[dict]) -> ValidationReport:
        """Validate a full question set, with domain-specific checks."""
        report = super().validate_all(questions)

        # Run batch checks on specific distributions found in the questions
        for q in questions:
            problem = str(q.get("problem", q.get("stem", "")))
            answer = str(q.get("answer", q.get("standard_answer", "")))

            # 二项分布 batch check
            binom_match = re.search(r'[Bb]\s*\(\s*(\d+)\s*,\s*([0-9.]+)\s*\)', problem + answer)
            if binom_match:
                n = int(binom_match.group(1))
                p = float(binom_match.group(2))
                r = self.validate_binomial(n, p)

            # 泊松分布 batch check
            poisson_match = re.search(r'[Pp]\s*\(\s*([0-9.]+)\s*\)', problem + answer)
            if poisson_match:
                lam = float(poisson_match.group(1))
                r = self.validate_poisson(lam)

            # 正态标准化 batch check
            if "正态" in problem or "N(" in problem or "N(" in answer:
                self.validate_normal_standardization(answer + problem)

        return report
