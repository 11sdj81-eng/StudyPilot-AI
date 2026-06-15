"""v1.1 full-chain visible symbol normalization.

This module is intentionally conservative: TeX inside math delimiters remains
TeX for MathJax, while all user-visible prose, captions, options, source text
and figure metadata are normalized to textbook-readable symbols.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


FORBIDDEN_VISIBLE_TOKENS = [
    "Q_enc",
    "Delta",
    "frac",
    "sqrt",
    "tag",
    "quad",
    "^",
    "(a)/(D)",
    "(1)/(",
    "UAB",
]


@dataclass
class SymbolProfileV2:
    course_name: str = ""
    enclosed_charge: str = "Q"
    voltage_ab: str = "Uab"
    phi_text: str = "φ"
    epsilon0_text: str = "ε₀"
    rho_s_text: str = "ρₛ"
    integral_style: str = "ordinary"

    def as_dict(self) -> dict:
        return asdict(self)


SUPERSCRIPT = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")


def build_symbol_profile_v2(course: dict | None = None, chunks: list[dict] | None = None) -> SymbolProfileV2:
    course = course or {}
    text = "\n".join(str(c.get("text", "")) for c in (chunks or []))
    profile = SymbolProfileV2(course_name=str(course.get("course_name", "")))
    if "UAB" in text:
        profile.voltage_ab = "Uab"
    if "∮" in text:
        profile.integral_style = "closed"
    return profile


def normalize_visible_text_v2(text: str, profile: SymbolProfileV2 | None = None) -> str:
    profile = profile or SymbolProfileV2()
    text = str(text or "")
    text = re.sub(r"</?font[^>]*>", "", text, flags=re.I)
    replacements = [
        (r"\bQ_enc\b|Q_\{\\mathrm\{enc\}\}|Q_\{enc\}|Qenc", profile.enclosed_charge),
        (r"\bUAB\b", profile.voltage_ab),
        (r"\bDelta\s*S\b", "ΔS"),
        (r"\bDelta\s*l\b", "Δl"),
        (r"\bepsilon_0\b|ε0", profile.epsilon0_text),
        (r"\brho_s\b|ρs", profile.rho_s_text),
        (r"\bE1t\b", "E₁t"),
        (r"\bE2t\b", "E₂t"),
        (r"\bD1n\b", "D₁n"),
        (r"\bD2n\b", "D₂n"),
        (r"\(a\)/\(D\)", "a/D"),
        (r"\(1\)/\(2\)", "1/2"),
        (r"\bsqrt\s*\(([^)]+)\)", r"√(\1)"),
        (r"\bfrac\b", ""),
        (r"\bquad\b", ""),
        (r"\btag\s*\{?([0-9]+[-.][0-9]+)\}?", r"(\1)"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.I)
    text = re.sub(r"(?<!\\)\b([a-zA-Z])\^([0-9n])\b", lambda m: m.group(1) + m.group(2).translate(SUPERSCRIPT), text)
    text = re.sub(r"(?<!\\)\b([A-Z])\^([0-9n])\b", lambda m: m.group(1) + m.group(2).translate(SUPERSCRIPT), text)
    return re.sub(r"\s+", " ", text).strip() if "\n" not in text else text


def normalize_math_source_v2(tex: str, profile: SymbolProfileV2 | None = None) -> str:
    profile = profile or SymbolProfileV2()
    tex = str(tex or "").strip()
    tex = re.sub(r"\\tag\s*([0-9]+[-.][0-9]+)", r"\\tag{\1}", tex)
    tex = re.sub(r"(?<!\\)tag\s*\{?([0-9]+[-.][0-9]+)\}?", r"\\tag{\1}", tex)
    tex = tex.replace(r"\quad", r"\;").replace(r"\qquad", r"\;")
    tex = re.sub(r"\bQ_enc\b|Q_\{\\mathrm\{enc\}\}|Q_\{enc\}|Qenc", profile.enclosed_charge, tex)
    tex = re.sub(r"\bDelta\s*S\b", r"\\Delta S", tex)
    tex = re.sub(r"\bDelta\s*l\b", r"\\Delta l", tex)
    tex = re.sub(r"\bepsilon_0\b|ε0", r"\\varepsilon_0", tex)
    tex = re.sub(r"\brho_s\b|ρs", r"\\rho_s", tex)
    tex = re.sub(r"\bE1t\b", "E_{1t}", tex)
    tex = re.sub(r"\bE2t\b", "E_{2t}", tex)
    tex = re.sub(r"\bD1n\b", "D_{1n}", tex)
    tex = re.sub(r"\bD2n\b", "D_{2n}", tex)
    tex = re.sub(r"\bsqrt\s*\(([^)]+)\)", r"\\sqrt{\1}", tex)
    tex = re.sub(r"\(a\)/\(D\)", r"\\frac{a}{D}", tex)
    tex = re.sub(r"\(1\)/\(2\)", r"\\frac{1}{2}", tex)
    return re.sub(r"\s+", " ", tex).strip()


def normalize_markdown_v2(content: str, profile: SymbolProfileV2 | None = None) -> str:
    profile = profile or SymbolProfileV2()
    content = str(content or "")
    parts: list[str] = []
    pos = 0
    pattern = re.compile(r"(\$\$.*?\$\$|(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$))", re.S)
    for match in pattern.finditer(content):
        parts.append(normalize_visible_text_v2(content[pos:match.start()], profile))
        token = match.group(0)
        if token.startswith("$$"):
            parts.append("$$\n" + normalize_math_source_v2(token[2:-2], profile) + "\n$$")
        else:
            parts.append("$" + normalize_math_source_v2(token[1:-1], profile) + "$")
        pos = match.end()
    parts.append(normalize_visible_text_v2(content[pos:], profile))
    return "".join(parts)


def normalize_figure_metadata_v2(figures: list[dict] | None, profile: SymbolProfileV2 | None = None) -> list[dict]:
    normalized: list[dict] = []
    for fig in figures or []:
        item = dict(fig)
        for key in ["title", "caption", "target_section", "source", "purpose", "why_needed", "linked_knowledge_point"]:
            if key in item:
                item[key] = normalize_visible_text_v2(str(item[key]), profile)
        item["symbol_check_passed"] = not scan_forbidden_visible_tokens(" ".join(str(item.get(k, "")) for k in item))
        normalized.append(item)
    return normalized


def scan_forbidden_visible_tokens(text: str) -> list[str]:
    visible = str(text or "")
    lower = visible.lower()
    hits: list[str] = []
    for token in FORBIDDEN_VISIBLE_TOKENS:
        if token == "^":
            if "^" in visible:
                hits.append(token)
        elif token.lower() in lower:
            hits.append(token)
    return sorted(set(hits))


def assert_no_catastrophic_formula_v2(text: str) -> None:
    if re.search(r"Q\s*√|Q\\sqrt|Q\s*\\sqrt", str(text or "")):
        raise ValueError("疑似公式分母丢失：出现 Q√ 或 Q\\sqrt")


def normalize_question_metadata_v2(metadata: dict[str, Any], profile: SymbolProfileV2 | None = None) -> dict:
    return {key: normalize_visible_text_v2(value, profile) if isinstance(value, str) else value for key, value in metadata.items()}
