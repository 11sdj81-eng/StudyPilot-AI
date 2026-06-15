"""Symbol normalization for textbook-style physics notes.

Generated text sometimes contains programmatic tokens such as ``epsilon_0``
or ``hatz``. This module normalizes them before Markdown/PDF export.
"""

from __future__ import annotations

import re


BANNED_TOKENS = ["phi", "epsilon", "rho", "sqrtr", "hatz", "hatx", "haty", "<font", "placeholder"]
DEFAULT_SYMBOL_POLICY = {
    "inline_phi": "φ",
    "inline_epsilon": "ε",
    "inline_rho": "ρ",
    "display_phi": r"\varphi",
    "display_epsilon": r"\varepsilon",
    "display_rho": r"\rho",
    "integral_style": "ordinary",
    "allowed_integrals": ["ordinary"],
}

SUBSCRIPT_MAP = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
}

TEXT_REPLACEMENTS = [
    (r"\bepsilon_0\b", "ε₀"),
    (r"\bepsilon\b", "ε"),
    (r"\brho_s\b", "ρₛ"),
    (r"\brho_v\b", "ρᵥ"),
    (r"\brho\b", "ρ"),
    (r"\bphi\b", "φ"),
    (r"\bvarphi\b", "φ"),
    (r"\btheta\b", "θ"),
    (r"\bnabla\b", "∇"),
    (r"\bhatz\b", "ẑ"),
    (r"\bhatx\b", "x̂"),
    (r"\bhaty\b", "ŷ"),
    (r"\bD_1n\b", "D₁ₙ"),
    (r"\bE_1t\b", "E₁ₜ"),
    (r"\bcos\s*θ\b", "cos θ"),
    (r"\bcos\s*theta\b", "cos θ"),
]

FORMULA_REPLACEMENTS = [
    (r"(?<!\\)\bepsilon_0\b", r"\\varepsilon_0"),
    (r"(?<!\\)\bepsilon\b", r"\\varepsilon"),
    (r"(?<!\\)\brho_s\b", r"\\rho_s"),
    (r"(?<!\\)\brho_v\b", r"\\rho_v"),
    (r"(?<!\\)\brho\b", r"\\rho"),
    (r"(?<!\\)\bvarphi\b", r"\\varphi"),
    (r"(?<!\\)\bphi\b", r"\\varphi"),
    (r"(?<!\\)\btheta\b", r"\\theta"),
    (r"(?<!\\)\bnabla\b", r"\\nabla"),
    (r"(?<!\\)\bhatz\b", r"\\hat{z}"),
    (r"(?<!\\)\bhatx\b", r"\\hat{x}"),
    (r"(?<!\\)\bhaty\b", r"\\hat{y}"),
    (r"(?<!\\)\bD_1n\b", r"D_{1n}"),
    (r"(?<!\\)\bE_1t\b", r"E_{1t}"),
]


def build_symbol_policy(textbook_style: dict | None = None) -> dict:
    """Build a rendering policy from textbook_style_analyzer output."""
    policy = dict(DEFAULT_SYMBOL_POLICY)
    if not textbook_style:
        return policy
    prefs = textbook_style.get("symbol_preferences", {}) or {}
    formula_style = textbook_style.get("formula_style", {}) or {}
    if prefs.get("phi_variant") == "phi":
        policy["inline_phi"] = "ϕ"
        policy["display_phi"] = r"\phi"
    if prefs.get("epsilon_variant") == "epsilon":
        policy["inline_epsilon"] = "ϵ"
        policy["display_epsilon"] = r"\epsilon"
    allowed = formula_style.get("allowed_integrals") or ["ordinary"]
    policy["allowed_integrals"] = allowed
    policy["integral_style"] = formula_style.get("integral_style") or allowed[0]
    return policy


def normalize_text_symbols(text: str, symbol_policy: dict | None = None) -> str:
    """Normalize ordinary prose to readable Unicode math symbols."""
    policy = symbol_policy or DEFAULT_SYMBOL_POLICY
    text = _strip_font_tags(text)
    text = re.sub(r"\bsqrtr\^2\s*\+\s*d\^2\b", "√(r² + d²)", text)
    text = re.sub(r"\bsqrt\s*\(\s*r\^2\s*\+\s*d\^2\s*\)", "√(r² + d²)", text)
    text = _normalize_integral_text(text, policy)
    for pattern, replacement in TEXT_REPLACEMENTS:
        if replacement == "φ":
            replacement = str(policy.get("inline_phi", "φ"))
        elif replacement == "ε":
            replacement = str(policy.get("inline_epsilon", "ε"))
        elif replacement == "ρ":
            replacement = str(policy.get("inline_rho", "ρ"))
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def normalize_formula_symbols(formula: str, symbol_policy: dict | None = None) -> str:
    """Normalize formula source to standard LaTeX before rendering."""
    policy = symbol_policy or DEFAULT_SYMBOL_POLICY
    formula = _strip_font_tags(formula).strip()
    formula = formula.strip("$").strip()
    formula = re.sub(r"\\+\s*$", "", formula).strip()
    formula = formula.replace("\\left", "").replace("\\right", "")
    formula = re.sub(r"\\tag\s*\{?([^{}\s]+)\}?", "", formula)
    formula = re.sub(r"\bsqrtr\^2\s*\+\s*d\^2\b", r"\\sqrt{r^2+d^2}", formula)
    formula = re.sub(r"\bsqrt\s*\(\s*([^)]+)\s*\)", r"\\sqrt{\1}", formula)
    formula = re.sub(r"\bcos\s*θ\b", r"\\cos\\theta", formula)
    for pattern, replacement in FORMULA_REPLACEMENTS:
        if replacement == r"\\varphi":
            replacement = str(policy.get("display_phi", r"\varphi")).replace("\\", r"\\")
        elif replacement == r"\\varepsilon":
            replacement = str(policy.get("display_epsilon", r"\varepsilon")).replace("\\", r"\\")
        elif replacement == r"\\rho":
            replacement = str(policy.get("display_rho", r"\rho")).replace("\\", r"\\")
        formula = re.sub(pattern, replacement, formula)
    formula = _normalize_integral_formula(formula, policy)
    formula = re.sub(r"(?<!\\)\bcos\s*\\theta\b", r"\\cos\\theta", formula)
    formula = re.sub(r"\\{2,}", r"\\", formula)
    return formula


def normalize_generated_content(content: str, textbook_style: dict | None = None) -> str:
    """Normalize a mixed Markdown document while preserving formula syntax."""
    policy = build_symbol_policy(textbook_style)
    content = _remove_visible_pollution(_strip_font_tags(content))
    content = re.sub(r"tag\s*\{?(\d+[-.]\d+)\}?", r"\\tag{\1}", content)
    parts: list[str] = []
    pos = 0
    pattern = re.compile(r"(\$\$.*?\$\$|(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$))", re.S)
    for match in pattern.finditer(content):
        parts.append(normalize_text_symbols(content[pos:match.start()], policy))
        token = match.group(0)
        if token.startswith("$$"):
            inner = normalize_formula_symbols(token[2:-2], policy)
            parts.append(f"$$\n{inner.strip()}\n$$")
        else:
            inner = normalize_formula_symbols(token[1:-1], policy)
            parts.append(f"${inner.strip()}$")
        pos = match.end()
    parts.append(normalize_text_symbols(content[pos:], policy))
    return "".join(parts)


def contains_banned_tokens(text: str) -> list[str]:
    """Check for banned tokens OUTSIDE of LaTeX formula regions.

    Tokens that appear only as LaTeX commands (e.g. \\varphi, \\Phi) inside
    formula blocks are NOT banned — they are valid LaTeX.
    """
    # First strip formula regions
    clean = re.sub(r'\$\$.*?\$\$', ' ', text, flags=re.S)
    clean = re.sub(r'(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)', ' ', clean, flags=re.S)
    # Also strip LaTeX commands (backslash + letters) from non-formula regions
    # since \varphi etc. are valid in plain text
    clean = re.sub(r'\\[a-zA-Z]+\b', ' ', clean)

    haystack = clean.lower()
    found: list[str] = []
    for token in BANNED_TOKENS:
        if token == "<font":
            present = token in haystack
        else:
            # word-boundary check: token must not be part of a longer word
            present = re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", haystack) is not None
        if present:
            found.append(token)
    return found


def formula_to_readable_text(formula: str, symbol_policy: dict | None = None) -> str:
    """Last-resort readable text when image formula rendering fails."""
    policy = symbol_policy or DEFAULT_SYMBOL_POLICY
    formula = normalize_formula_symbols(formula, policy)
    replacements = {
        r"\varphi": str(policy.get("inline_phi", "φ")),
        r"\phi": str(policy.get("inline_phi", "φ")),
        r"\varepsilon": str(policy.get("inline_epsilon", "ε")),
        r"\epsilon": str(policy.get("inline_epsilon", "ε")),
        r"\rho": str(policy.get("inline_rho", "ρ")),
        r"\theta": "θ",
        r"\pi": "π",
        r"\nabla": "∇",
        r"\partial": "∂",
        r"\oint": _integral_symbol(policy),
        r"\int": "∫",
        r"\sum": "∑",
        r"\prod": "∏",
        r"\times": "×",
        r"\cdot": "·",
        r"\infty": "∞",
        r"\rightarrow": "→",
        r"\Rightarrow": "⇒",
        r"\sqrt": "√",
        r"\approx": "≈",
        r"\equiv": "≡",
        r"\neq": "≠",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\ll": "≪",
        r"\gg": "≫",
        r"\propto": "∝",
        r"\sim": "∼",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\lambda": "λ",
        r"\mu": "μ",
        r"\sigma": "σ",
        r"\omega": "ω",
        r"\Omega": "Ω",
        r"\mathbf": "",
    }
    # v3.0: also handle \text{...} BEFORE brace-content subscripting
    formula = re.sub(r"\\text\s*\{([^{}]+)\}", r"\1", formula)
    formula = re.sub(r"\\mathbf\s*\{\s*\\hat\s*\{([^{}]+)\}\s*\}", r"\\hat{\1}", formula)
    formula = re.sub(r"\\mathbf\s*\{\s*([^{}]+)\s*\}", r"\1", formula)
    for source, target in replacements.items():
        formula = formula.replace(source, target)
    formula = re.sub(r"\\hat\s*\{\s*\\mathbf\s*\{([^{}]+)\}\s*\}", r"\1̂", formula)
    formula = re.sub(r"\\hat\s*\{([^{}]+)\}", r"\1̂", formula)
    for _ in range(6):
        new_formula = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"(\1)/(\2)", formula)
        if new_formula == formula:
            break
        formula = new_formula
    formula = re.sub(r"\\(?:mathbf|mathrm|mathit|text|vec)\s*\{([^{}]+)\}", r"\1", formula)
    formula = re.sub(r"_\{([^{}]+)\}", lambda m: _subscript(m.group(1)), formula)
    formula = re.sub(r"_([A-Za-z0-9])", lambda m: _subscript(m.group(1)), formula)
    formula = re.sub(r"\^\{([^{}]+)\}", r"^(\1)", formula)
    formula = re.sub(r"[{}$\\]", "", formula)
    formula = formula.replace("frac", "")
    return normalize_text_symbols(re.sub(r"\s+", " ", formula).strip(), policy)


def textbook_forbidden_symbols(textbook_style: dict | None = None) -> list[str]:
    policy = build_symbol_policy(textbook_style)
    allowed = set(policy.get("allowed_integrals", ["ordinary"]))
    forbidden: list[str] = []
    if "closed_line" not in allowed:
        forbidden.append("∮")
    if "surface" not in allowed:
        forbidden.append("∯")
    if "volume" not in allowed:
        forbidden.append("∰")
    return forbidden


def _subscript(text: str) -> str:
    # Only digits and operators are rendered as Unicode subscripts.
    # Letter subscripts such as E_1t are kept as stable plain text (E1t)
    # because many PDF fonts render Unicode subscript letters as boxes.
    return "".join(SUBSCRIPT_MAP.get(char, char) for char in text)


def _strip_font_tags(text: str) -> str:
    return re.sub(r"</?font[^>]*>", "", str(text or ""), flags=re.I)


def _remove_visible_pollution(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        if re.search(r"SS号|General Information|OCR异常|编码异常|placeholder", line, flags=re.I):
            continue
        lines.append(line)
    return "\n".join(lines)


def _normalize_integral_formula(formula: str, policy: dict) -> str:
    allowed = set(policy.get("allowed_integrals", ["ordinary"]))
    if "closed_line" not in allowed:
        formula = re.sub(r"\\oint(?![A-Za-z])", r"\\int", formula)
    if "surface" not in allowed:
        formula = re.sub(r"\\oiint(?![A-Za-z])|\\iint(?![A-Za-z])", r"\\int", formula)
    if "volume" not in allowed:
        formula = re.sub(r"\\iiint(?![A-Za-z])", r"\\int", formula)
    return formula


def _normalize_integral_text(text: str, policy: dict) -> str:
    symbol = _integral_symbol(policy)
    allowed = set(policy.get("allowed_integrals", ["ordinary"]))
    if "closed_line" not in allowed:
        text = text.replace("∮", symbol)
    if "surface" not in allowed:
        text = text.replace("∯", symbol)
    if "volume" not in allowed:
        text = text.replace("∰", symbol)
    return text


def _integral_symbol(policy: dict) -> str:
    style = policy.get("integral_style", "ordinary")
    if style == "closed_line" and "closed_line" in set(policy.get("allowed_integrals", [])):
        return "∮"
    if style == "surface" and "surface" in set(policy.get("allowed_integrals", [])):
        return "∯"
    if style == "volume" and "volume" in set(policy.get("allowed_integrals", [])):
        return "∰"
    return "∫"
