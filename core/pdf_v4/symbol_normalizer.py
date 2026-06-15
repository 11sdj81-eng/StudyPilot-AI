"""Symbol normalization for StudyPilot PDF v4."""

from __future__ import annotations

import re


FORBIDDEN_TOKENS = [
    "^",
    "epsilon0",
    "rho_s",
    "Q_enc",
    "frac",
    "sqrt",
    "tag",
    "quad",
    "None",
    "null",
    "暂无",
    "concept_id",
    "formula_id",
    "source_basis",
]


TEXT_REPLACEMENTS = {
    "r^2": "r²",
    "r^3": "r³",
    "a^2": "a²",
    "epsilon0": "ε₀",
    "ε0": "ε₀",
    "rho_s": "ρₛ",
    "ρs": "ρₛ",
    "E1t": "E₁t",
    "E2t": "E₂t",
    "D1n": "D₁n",
    "D2n": "D₂n",
    "phi": "φ",
    "nabla": "∇",
    "Q_enc": "包围电荷 Q",
}


MATH_REPLACEMENTS = {
    "epsilon0": "epsilon_0",
    "ε0": "epsilon_0",
    "rho_s": "rho_s",
    "phi": "phi",
    "nabla": "nabla",
}


def normalize_text(text: object) -> str:
    value = "" if text is None else str(text)
    for old, new in TEXT_REPLACEMENTS.items():
        value = value.replace(old, new)
    value = re.sub(r"sqrt\(([^)]+)\)", r"√(\1)", value)
    value = value.replace("None", "").replace("null", "").replace("暂无", "")
    return value


def normalize_math(math: object) -> str:
    value = "" if math is None else str(math)
    value = value.replace("\\", "")
    for old, new in MATH_REPLACEMENTS.items():
        value = value.replace(old, new)
    value = value.replace("varepsilon_0", "epsilon_0")
    value = value.replace("varphi", "phi")
    value = value.replace("mathbf", "")
    value = value.replace("hat{R}", "hat(R)")
    value = value.replace("hat R", "hat(R)")
    value = re.sub(r"\\?frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", value)
    value = value.replace("quad", " ")
    value = value.replace("tag", "")
    return value.strip()


def forbidden_hits(text: str) -> list[str]:
    return sorted({token for token in FORBIDDEN_TOKENS if token in text})
