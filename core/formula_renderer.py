"""Render LaTeX formulas to local PNG images before WeasyPrint runs."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.config import ROOT_DIR
from core.symbol_mapper import build_symbol_policy, formula_to_readable_text, normalize_formula_symbols


FORMULA_DIR = ROOT_DIR / "assets" / "generated" / "formulas"


def is_complex_formula(formula: str) -> bool:
    """Return True only for formulas that benefit from image rendering."""
    f = formula.strip()
    complex_tokens = [
        r"\frac", r"\sqrt", r"\sum", r"\prod", r"\lim", r"\begin",
        r"\matrix", r"\cases", r"\over", r"\partial", r"\nabla",
    ]
    if any(token in f for token in complex_tokens):
        return True
    if len(f) > 48:
        return True
    if f.count("_") + f.count("^") >= 4:
        return True
    return False


def render_formula_image(
    formula: str,
    display: bool = True,
    textbook_style: dict | None = None,
) -> Path | None:
    """Render formula to a cached PNG path.

    Matplotlib mathtext gives stable static output for PDF engines such as
    WeasyPrint, which do not execute MathJax JavaScript.
    """
    policy = build_symbol_policy(textbook_style)
    normalized = _sanitize_for_mathtext(normalize_formula_symbols(formula, policy))
    digest = hashlib.sha1(f"{display}:{normalized}".encode("utf-8")).hexdigest()[:16]
    output = FORMULA_DIR / f"formula_{digest}.png"
    if output.exists():
        return output
    FORMULA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        return _render_with_matplotlib(normalized, output, display=display)
    except Exception:
        try:
            return _render_readable_fallback(normalized, output, display=display)
        except Exception:
            return None


def _render_with_matplotlib(formula: str, output: Path, display: bool) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cleaned = formula.strip().strip("$")
    math_text = f"${cleaned}$"
    fontsize = 22 if display else 16
    fig = plt.figure(figsize=(8.0 if display else 3.8, 1.05 if display else 0.45), dpi=220)
    fig.patch.set_facecolor("#fbf8ff")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.5, 0.5, math_text, ha="center", va="center", fontsize=fontsize, color="#342a45")
    fig.savefig(output, bbox_inches="tight", pad_inches=0.08, facecolor="#fbf8ff")
    plt.close(fig)
    return output


def _sanitize_for_mathtext(formula: str) -> str:
    formula = formula.strip().strip("$").strip()
    formula = re.sub(r"\\+\s*$", "", formula).strip()
    formula = re.sub(r"\\hat\s*\{\s*\\mathbf\s*\{([^{}]+)\}\s*\}", r"\\hat{\1}", formula)
    formula = re.sub(r"\\tag\s*\{?[^{}]+\}?", "", formula)
    formula = re.sub(r"\\text\s*\{[\u4e00-\u9fff，。；：、（）()\sA-Za-z0-9_\-+*/=]*\}", "", formula)
    formula = re.sub(r"[\u4e00-\u9fff，。；：、（）]", "", formula)
    formula = formula.replace(r"\quad", " ").replace(r"\qquad", " ")
    return re.sub(r"\s+", " ", formula).strip()


def _render_readable_fallback(formula: str, output: Path, display: bool) -> Path:
    text = formula_to_readable_text(formula)
    font = _font(30 if display else 20)
    padding_x, padding_y = (42, 24) if display else (18, 10)
    dummy = Image.new("RGB", (10, 10), "#fbf8ff")
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = max(260, bbox[2] - bbox[0] + padding_x * 2)
    height = max(72 if display else 36, bbox[3] - bbox[1] + padding_y * 2)
    img = Image.new("RGB", (width, height), "#fbf8ff")
    draw = ImageDraw.Draw(img)
    draw.text((padding_x, padding_y), text, fill="#342a45", font=font)
    img.save(output)
    return output


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()
