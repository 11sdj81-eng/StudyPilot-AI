"""Formula correctness checks for v1.1 rebuilt PDFs."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from core.symbol_normalizer_v2 import scan_forbidden_visible_tokens


@dataclass
class FormulaCheckV2:
    passed: bool
    errors: list[str]
    warnings: list[str]
    checked_types: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def validate_formulas_v2(content: str, task_type: str = "") -> FormulaCheckV2:
    text = str(content or "")
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    if re.search(r"Q\s*√|Q\\sqrt|Q\s*\\sqrt", text):
        errors.append("镜像法/点电荷电位疑似分母丢失：出现 Q√ 或 Q\\sqrt")
    if re.search(r"\\frac\s*\{\s*Q\s*\}\s*\{\s*\\sqrt\{[^{}]+\}\s*\}", text):
        checked.append("点电荷电位/镜像法分母")
    if re.search(r"\\frac\s*\{\s*Q\s*\}\s*\{\s*4\\pi\\varepsilon_0\s*R\^?2?\s*\}", text) or "点电荷" in text:
        checked.append("点电荷电场")
    if "\\int_S" in text and "\\mathbf{D}" in text:
        checked.append("高斯定理")
    if "Q_r=Q r^3/a^3" in text or "Qr/(4" in text:
        checked.append("均匀带电球体内外场强")
    if "\\mathbf{E}=-\\nabla\\varphi" in text:
        checked.append("电位与电场关系")
    if "E_{1t}=E_{2t}" in text and "D_{1n}-D_{2n}=\\rho_s" in text:
        checked.append("边界条件")
    if "Q'=-Q" in text and "z=-h" in text:
        checked.append("镜像法平面问题")
    if "b = a²/d" in text or "b=a²/d" in text or "\\frac{a^2}{d}" in text:
        checked.append("镜像法导体球问题")
    if "\\frac{1}{2}\\mathbf{D}\\cdot\\mathbf{E}" in text:
        checked.append("静电能量密度")

    visible_without_math = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    visible_without_math = re.sub(r"(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)", " ", visible_without_math, flags=re.S)
    forbidden = scan_forbidden_visible_tokens(visible_without_math)
    if forbidden:
        errors.append("可见文本存在禁用符号：" + "、".join(forbidden))

    required_by_task = {
        "exam_sprint": ["高斯定理", "电位与电场关系", "边界条件", "镜像法平面问题", "静电能量密度"],
        "past_paper": ["高斯定理", "边界条件", "镜像法平面问题"],
        "mock_exam": ["高斯定理", "电位与电场关系", "边界条件", "镜像法平面问题"],
        "single_chapter": ["点电荷电场", "高斯定理", "电位与电场关系", "边界条件", "镜像法平面问题", "静电能量密度"],
        "chapter_review": ["点电荷电场", "高斯定理", "电位与电场关系", "边界条件", "镜像法平面问题", "静电能量密度"],
    }.get(task_type, [])
    for formula_type in required_by_task:
        if formula_type not in checked:
            warnings.append(f"未检测到关键公式类型：{formula_type}")

    return FormulaCheckV2(passed=not errors, errors=errors, warnings=warnings, checked_types=sorted(set(checked)))
