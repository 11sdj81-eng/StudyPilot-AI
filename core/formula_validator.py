"""Formula sanity checks for high-frequency StudyPilot physics content."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FormulaValidationResult:
    passed: bool
    warnings: list[str]
    checked_types: list[str]

    def as_dict(self) -> dict:
        return {"passed": self.passed, "warnings": self.warnings, "checked_types": self.checked_types}


def validate_formulas(content: str) -> FormulaValidationResult:
    text = str(content or "")
    warnings: list[str] = []
    checked: list[str] = []

    checks = [
        ("电位与电场关系", [r"\\mathbf\{E\}\s*=\s*-\\nabla\\varphi", "E = -∇ φ", "E=-∇φ"]),
        ("高斯定理", [r"\\int_S\\mathbf\{D\}\\cdot d\\mathbf\{S\}", "∫_S D · dS", "∫SD·dS"]),
        ("边界条件", ["D_{1n}-D_{2n}", "D1n - D2n", "D₁n"]),
        ("镜像法", ["Q'=-Q", "Q' = -Q", "-Q"]),
        ("静电能量", [r"\\frac\{1\}\{2\}\\mathbf\{D\}\\cdot\\mathbf\{E\}", "1/2"]),
    ]
    for name, patterns in checks:
        if any(re.search(p, text) if p.startswith("\\") else p in text for p in patterns):
            checked.append(name)
        elif name in ["电位与电场关系", "高斯定理"] and any(key in text for key in name):
            warnings.append(f"{name} 出现但未检测到标准公式")

    if re.search(r"Q\s*√|Q\\sqrt|Q\s*\\sqrt", text):
        warnings.append("疑似镜像法/点电荷公式分母丢失：出现 Q√")
    if "frac" in text and r"\frac" not in text:
        warnings.append("出现 frac 残留")
    if "sqrt" in text and r"\sqrt" not in text:
        warnings.append("出现 sqrt 残留")
    if "(a)/(D)" in text:
        warnings.append("出现程序化分式 (a)/(D)")

    return FormulaValidationResult(passed=not warnings, warnings=warnings, checked_types=checked)
