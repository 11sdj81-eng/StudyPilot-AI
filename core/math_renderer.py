"""Math preparation utilities for the v6 Chromium PDF engine."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from core.symbol_mapper import formula_to_readable_text


COMPLEX_TEX_TOKENS = (
    r"\frac",
    r"\sqrt",
    r"\sum",
    r"\prod",
    r"\lim",
    r"\int",
    r"\iint",
    r"\iiint",
    r"\oint",
    r"\partial",
    r"\nabla",
    r"\begin",
    r"\cases",
    r"\matrix",
)


@dataclass
class MathStats:
    inline_formula_count: int = 0
    display_formula_count: int = 0
    simple_formula_count: int = 0
    complex_formula_count: int = 0
    numbered_formula_count: int = 0

    def as_dict(self) -> dict:
        return {
            "inline_formula_count": self.inline_formula_count,
            "display_formula_count": self.display_formula_count,
            "simple_formula_count": self.simple_formula_count,
            "complex_formula_count": self.complex_formula_count,
            "numbered_formula_count": self.numbered_formula_count,
        }


def prepare_markdown_math(content: str) -> tuple[str, MathStats]:
    """Convert Markdown math to MathJax-ready delimiters.

    The v6 engine deliberately keeps formulas as TeX until the browser phase.
    MathJax then turns them into SVG during rendering, so the final PDF does
    not expose raw ``\\frac`` / ``\\nabla`` text to readers.
    """
    stats = MathStats()
    formula_index = 0

    content = _strip_unsafe_html(str(content or ""))
    content = re.sub(r"\\\[\s*(.*?)\s*\\\]", lambda m: f"\n$$\n{m.group(1).strip()}\n$$\n", content, flags=re.S)
    content = re.sub(r"\\\(\s*(.*?)\s*\\\)", lambda m: f"${m.group(1).strip()}$", content, flags=re.S)

    def display_repl(match: re.Match) -> str:
        nonlocal formula_index
        formula_index += 1
        formula = sanitize_tex(match.group(1))
        formula, had_number = ensure_formula_number(formula, formula_index)
        stats.display_formula_count += 1
        stats.numbered_formula_count += 1 if had_number or formula_index else 0
        if is_complex_tex(formula):
            stats.complex_formula_count += 1
        else:
            stats.simple_formula_count += 1
        return (
            '\n<div class="math-display-card">'
            f'<div class="math-display" data-tex="{html.escape(formula, quote=True)}"></div>'
            '</div>\n'
        )

    prepared = re.sub(r"\$\$(.*?)\$\$", display_repl, content, flags=re.S)

    def inline_repl(match: re.Match) -> str:
        formula = sanitize_tex(match.group(1), inline=True)
        stats.inline_formula_count += 1
        if is_complex_tex(formula):
            stats.complex_formula_count += 1
            return f'<span class="math-inline" data-tex="{html.escape(formula, quote=True)}"></span>'
        else:
            stats.simple_formula_count += 1
        readable = inline_formula_text(formula)
        return f'<span class="math-inline-text">{html.escape(readable)}</span>'

    prepared = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", inline_repl, prepared, flags=re.S)
    return prepared, stats


def inline_formula_text(formula: str) -> str:
    """Return stable printable text for inline math."""
    text = formula_to_readable_text(sanitize_tex(formula, inline=True))
    text = text.replace("mathrm", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("Q₍enc₎", "Q_enc").replace("Qenc", "Q_enc")
    text = text.replace("Q_enc", "Q")
    text = re.sub(r"\^\(([^)]+)\)", lambda m: _superscript_text(m.group(1)), text)
    text = re.sub(r"\^([0-9n])", lambda m: _superscript_text(m.group(1)), text)
    return text or "公式"


def _superscript_text(value: str) -> str:
    table = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
    return str(value).translate(table)


def sanitize_tex(formula: str, inline: bool = False) -> str:
    """Make model-produced TeX acceptable for MathJax without changing notation."""
    formula = str(formula or "").strip().strip("$").strip()
    formula = formula.replace("\u00a0", " ")
    formula = re.sub(r"\\+\s*$", "", formula).strip()
    formula = re.sub(r"\\tag\s*([0-9]+[-.][0-9]+)", r"\\tag{\1}", formula)
    formula = re.sub(r"(?<!\\)tag\s*\{?([0-9]+[-.][0-9]+)\}?", r"\\tag{\1}", formula)
    formula = formula.replace(r"\quad", r"\;").replace(r"\qquad", r"\;")
    formula = re.sub(r"\\text\s*\{([^{}]*)\}", lambda m: _clean_text_command(m.group(1)), formula)
    formula = re.sub(
        r"\\hat\s*\{\s*\\mathbf\s*\{([^{}]+)\}\s*\}",
        lambda m: rf"\hat{{\mathbf{{{m.group(1)}}}}}",
        formula,
    )
    formula = re.sub(
        r"\\mathbf\s*\{\s*\\hat\s*\{([^{}]+)\}\s*\}",
        lambda m: rf"\hat{{\mathbf{{{m.group(1)}}}}}",
        formula,
    )
    formula = re.sub(r"\s+", " ", formula).strip()
    if inline:
        formula = re.sub(r"\\tag\s*\{[^{}]+\}", "", formula).strip()
    return formula


def ensure_formula_number(formula: str, index: int) -> tuple[str, bool]:
    if re.search(r"\\tag\s*\{[^{}]+\}", formula):
        formula = re.sub(r"\\tag\s*\{([0-9]+)[-.]([0-9]+)\}", r"\\tag{\1-\2}", formula)
        return formula, True
    return f"{formula} \\tag{{1-{index}}}", False


def is_complex_tex(formula: str) -> bool:
    formula = str(formula or "")
    if any(token in formula for token in COMPLEX_TEX_TOKENS):
        return True
    if len(formula) > 48:
        return True
    if formula.count("_") + formula.count("^") >= 4:
        return True
    return False


def _strip_unsafe_html(text: str) -> str:
    text = re.sub(r"</?font[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    return text


def _clean_text_command(text: str) -> str:
    text = re.sub(r"[<>]", "", text).strip()
    return r"\mathrm{" + text + "}" if text and not re.search(r"[\u4e00-\u9fff]", text) else ""
