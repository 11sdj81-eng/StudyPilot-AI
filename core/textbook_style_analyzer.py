"""v2.2: Textbook style analyzer — extract per-course writing conventions.

Scans uploaded course materials to build a ``TextbookStyle`` profile that
drives symbol normalisation, formula rendering, and prompt tone so every
generated PDF stays aligned with what the student actually studies.
"""

from __future__ import annotations

import re
from collections import Counter


def analyze_textbook_style(chunks: list[dict], course: dict | None = None) -> dict:
    """Build a textbook-style constraint profile from retrieved chunks.

    Returns a dict with keys:
        textbook_names, chapter_style, symbol_preferences, formula_style,
        term_preferences, style_category, confidence, fallback_reason
    """
    course = course or {}
    if not chunks:
        return _fallback_style("无教材资料可用于分析，采用通用课程规范。")

    all_text = "\n".join(c.get("text", "") for c in chunks[:30])
    if len(all_text) < 500:
        return _fallback_style("教材资料文本不足，采用通用课程规范。")

    return {
        "textbook_names": _extract_textbook_names(all_text),
        "chapter_style": _detect_chapter_style(all_text),
        "symbol_preferences": _detect_symbol_preferences(all_text),
        "formula_style": _detect_formula_style(all_text),
        "term_preferences": _detect_term_preferences(all_text),
        "example_style": _detect_example_style(all_text),
        "chapter_structure": _detect_chapter_structure(all_text),
        "style_category": _classify_style(all_text),
        "confidence": _compute_confidence(all_text),
        "source_text_length": len(all_text),
        "course_name": course.get("course_name", ""),
    }


# ---- internal detectors ----------------------------------------------------

def _extract_textbook_names(text: str) -> list[str]:
    """Heuristic textbook name extraction from first-page-like content."""
    names: list[str] = []
    for line in text.splitlines()[:20]:
        line = line.strip()
        if 6 <= len(line) <= 50 and any(
            kw in line for kw in ["学", "论", "原理", "技术", "基础", "导论", "教程", "概论", "电磁", "电路"]
        ):
            if not any(skip in line for skip in ["出版社", "ISBN", "http", "www.", "@", "SS号"]):
                names.append(line)
    return list(dict.fromkeys(names))[:3]  # dedup, top 3


def _detect_chapter_style(text: str) -> str:
    """Classify chapter heading style."""
    patterns = {
        "numbered_decimal": r"^第[一二三四五六七八九十\d]+章",
        "numbered_chinese": r"^[一二三四五六七八九十]、",
        "section_dot": r"^\d+\.\d+",
        "topic_only": r"^#+\s+\S",
    }
    scores: dict[str, int] = {}
    for style, pat in patterns.items():
        scores[style] = len(re.findall(pat, text, flags=re.M))
    if not scores or max(scores.values()) == 0:
        return "topic_only"
    return max(scores, key=lambda k: scores[k])


def _detect_symbol_preferences(text: str) -> dict[str, str]:
    """Detect preferred symbol variants from the textbook."""
    prefs: dict[str, str] = {}

    # φ vs ϕ
    phi_count = text.count("φ") + text.count("\\varphi")
    varphi_count = text.count("ϕ") + text.count("\\phi")
    if phi_count > varphi_count:
        prefs["phi_variant"] = "varphi"
    elif varphi_count > phi_count:
        prefs["phi_variant"] = "phi"

    # ε vs ϵ
    eps_count = text.count("ε") + text.count("\\varepsilon")
    vareps_count = text.count("ϵ") + text.count("\\epsilon")
    if eps_count > vareps_count:
        prefs["epsilon_variant"] = "varepsilon"
    elif vareps_count > eps_count:
        prefs["epsilon_variant"] = "epsilon"

    # ρ with subscripts
    if re.search(r"ρ[_\s]*[vs]", text):
        prefs["rho_subscript"] = "yes"
    if re.search(r"ρ[_\s]*s", text):
        prefs["rho_s"] = "yes"
    if re.search(r"ρ[_\s]*v", text):
        prefs["rho_v"] = "yes"

    # D vs E for Gauss law
    d_count = len(re.findall(r"(?<!\w)D(?!\w)", text))
    e_count = len(re.findall(r"(?<!\w)E(?!\w)", text))
    if d_count > e_count * 1.5:
        prefs["gauss_form"] = "D_form"
    elif e_count > d_count * 1.5:
        prefs["gauss_form"] = "E_form"

    # unit vectors
    for uv in ["e_r", "e_θ", "e_φ", "e_ρ", "e_z", "a_r", "a_θ", "a_φ",
               "\\hat{r}", "\\hat{θ}", "\\hat{φ}"]:
        if uv in text:
            prefs.setdefault("unit_vectors", []).append(uv)  # type: ignore[attr-defined]
    if "unit_vectors" in prefs:
        prefs["unit_vectors"] = "，".join(prefs["unit_vectors"][:4])  # type: ignore[call-overload]

    return prefs


def _detect_formula_style(text: str) -> dict:
    """Detect formula rendering conventions."""
    style: dict = {
        "numbered": False,
        "boxed": False,
        "derivation_heavy": False,
        "integral_style": "ordinary",
        "allowed_integrals": [],
    }

    # Formula numbering like (1-1), (2.3), (1)
    if re.search(r"\(\d+[\.-]\d+\)", text):
        style["numbered"] = True
    if re.search(r"推导|证明|可得|因此|代入", text):
        style["derivation_heavy"] = len(re.findall(r"推导|证明", text)) >= 2

    integrals = _detect_integral_style(text)
    style.update(integrals)

    return style


def _detect_integral_style(text: str) -> dict:
    """Detect which integral symbols actually appear in the textbook text."""
    counts = Counter({
        "ordinary": text.count("∫") + len(re.findall(r"\\int(?![A-Za-z])", text)),
        "closed_line": text.count("∮") + len(re.findall(r"\\oint(?![A-Za-z])", text)),
        "surface": text.count("∯") + len(re.findall(r"\\iint(?![A-Za-z])|\\oiint(?![A-Za-z])", text)),
        "volume": text.count("∰") + len(re.findall(r"\\iiint(?![A-Za-z])", text)),
    })
    allowed = [name for name, count in counts.items() if count > 0]
    if not allowed:
        allowed = ["ordinary"]
    integral_style = counts.most_common(1)[0][0] if counts else "ordinary"
    if counts[integral_style] == 0:
        integral_style = "ordinary"
    return {
        "integral_style": integral_style,
        "allowed_integrals": allowed,
        "integral_counts": dict(counts),
    }


def _detect_term_preferences(text: str) -> dict[str, str]:
    """Detect terminology preferences."""
    prefs: dict[str, str] = {}

    mappings = [
        ("电场强度", "电场强度", "场强"),
        ("电位移矢量", "电位移矢量", "电位移", "D矢量"),
        ("介电常数", "介电常数", "电容率", "介电系数"),
        ("极化强度", "极化强度", "电极化强度"),
        ("电势", "电势", "电位"),
        ("电通量", "电通量", "E通量"),
        ("导体", "导体", "导电体"),
        ("介质", "介质", "电介质"),
    ]
    for term, *aliases in mappings:  # type: ignore[assignment]
        counts = {a: text.count(a) for a in [term] + list(aliases)}
        best = max(counts, key=lambda k: counts[k])
        if counts[best] > 0:
            prefs[term] = best

    return prefs


def _detect_example_style(text: str) -> str:
    """Classify example style."""
    if re.search(r"例\s*\d+[\.\、]", text):
        return "numbered_examples"
    if re.search(r"例题\s*\d+", text):
        return "titled_examples"
    if re.search(r"题目[：:]|解题思路|解答", text):
        return "structured_examples"
    return "inline_examples"


def _detect_chapter_structure(text: str) -> list[str]:
    """Extract chapter-level headings."""
    headings: list[str] = []
    for m in re.finditer(r"^(?:第[一二三四五六七八九十\d]+章|Chapter\s+\d+)[\s\.\：:]+(.+)$", text, flags=re.M):
        headings.append(m.group(1).strip()[:40])
    return list(dict.fromkeys(headings))[:8]


def _classify_style(text: str) -> str:
    """Classify overall textbook style category."""
    scores = {
        "engineering": len(re.findall(r"工程|应用|设计|电路|器件|系统", text)),
        "theory": len(re.findall(r"推导|证明|定理|引理|定义|公理|严格", text)),
        "exam_prep": len(re.findall(r"真题|考题|试卷|考点|得分|选择题|填空题|计算题", text)),
    }
    if max(scores.values()) == 0:
        return "general"
    return max(scores, key=lambda k: scores[k])


def _compute_confidence(text: str) -> float:
    """Estimate confidence in the detected style (0.0–1.0)."""
    length = len(text)
    if length < 1000:
        return 0.3
    if length < 5000:
        return 0.5
    if length < 20000:
        return 0.7
    if length < 50000:
        return 0.85
    return 0.95


def _fallback_style(reason: str) -> dict:
    return {
        "textbook_names": [],
        "chapter_style": "topic_only",
        "symbol_preferences": {},
        "formula_style": {"numbered": False, "boxed": False, "derivation_heavy": False},
        "term_preferences": {},
        "example_style": "titled_examples",
        "chapter_structure": [],
        "style_category": "general",
        "confidence": 0.0,
        "fallback_reason": reason,
        "source_text_length": 0,
        "course_name": "",
    }


# ---- per-course symbol map builder -----------------------------------------

def build_course_symbol_map(chunks: list[dict], course: dict | None = None) -> dict:
    """Build a complete per-course symbol mapping for the rendering pipeline."""
    style = analyze_textbook_style(chunks, course)
    prefs = style.get("symbol_preferences", {})

    symbol_map: dict[str, str] = {
        # defaults (general engineering)
        "inline_phi": "φ",
        "inline_epsilon": "ε",
        "inline_rho": "ρ",
        "display_phi": "\\varphi",
        "display_epsilon": "\\varepsilon",
        "display_rho": "\\rho",
        "gauss_law_form": "E",
        "gauss_law_note": "真空条件下",
        "integral_style": style.get("formula_style", {}).get("integral_style", "ordinary"),
        "allowed_integrals": "，".join(style.get("formula_style", {}).get("allowed_integrals", ["ordinary"])),
        "confidence": str(style.get("confidence", 0.5)),
    }

    if prefs.get("phi_variant") == "phi":
        symbol_map["inline_phi"] = "ϕ"
        symbol_map["display_phi"] = "\\phi"
    if prefs.get("epsilon_variant") == "epsilon":
        symbol_map["inline_epsilon"] = "ϵ"
        symbol_map["display_epsilon"] = "\\epsilon"
    if prefs.get("gauss_form") == "D_form":
        symbol_map["gauss_law_form"] = "D"
        symbol_map["gauss_law_note"] = "含介质（D 形式）"

    return symbol_map


def style_summary_for_display(style: dict) -> str:
    """Human-readable one-paragraph summary for PDF / UI."""
    if style.get("fallback_reason"):
        return f"符号体系采用通用课程规范。（{style['fallback_reason']}）"

    parts: list[str] = []
    if style.get("textbook_names"):
        parts.append(f"参考教材：{'、'.join(style['textbook_names'][:2])}")
    parts.append(f"风格类型：{_style_category_cn(style.get('style_category', 'general'))}")
    parts.append(f"置信度：{style.get('confidence', 0):.0%}")

    prefs = style.get("symbol_preferences", {})
    if prefs:
        details = []
        if "phi_variant" in prefs:
            details.append("φ" if prefs["phi_variant"] == "varphi" else "ϕ")
        if "epsilon_variant" in prefs:
            details.append("ε" if prefs["epsilon_variant"] == "varepsilon" else "ϵ")
        if "gauss_form" in prefs:
            details.append(f"高斯用{prefs['gauss_form']}")
        if details:
            parts.append("符号：" + "、".join(details))
    return "本讲义符号体系已尽量对齐上传教材。" + "；".join(parts) + "。"


def _style_category_cn(cat: str) -> str:
    return {
        "engineering": "工程应用型", "theory": "理论推导型",
        "exam_prep": "考试导向型", "general": "通用型",
    }.get(cat, cat)
