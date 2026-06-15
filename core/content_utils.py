"""v2.0 Step 2: Content quality utilities.

LaTeX cleaning, source text sanitisation, source display formatting,
and generated-content quality validation.
"""

import re


# ---- LaTeX ----------------------------------------------------------------

def clean_latex(content: str) -> str:
    """Convert LaTeX delimiters so Streamlit's st.markdown renders them.

    Streamlit supports ``$...$`` and ``$$...$$`` but NOT ``\\[...\\]``.
    """
    # Replace \[ ... \] with $$ ... $$ (display math)
    content = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'\n$$\n\1\n$$\n', content, flags=re.DOTALL)
    return content


# ---- Source text ----------------------------------------------------------

def clean_source_text(text: str, max_length: int = 80) -> str:
    """Remove garbled / control characters and truncate for display."""
    if not text:
        return ""

    original_len = len(text)

    # Remove C0/C1 control chars (keep tab, newline)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Collapse repeated non-word / non-CJK symbols (typical garbled patterns)
    cleaned = re.sub(
        r'([^\w一-鿿\s　-〿＀-￯])\1{4,}',
        r'\1',
        cleaned,
    )

    # Edge case: everything was control chars → nothing left
    if not cleaned and original_len > 10:
        return "该来源文本疑似 OCR/编码异常，建议检查原始 PDF。"

    # Heuristic: if readable-char ratio is too low, flag it
    if cleaned:
        readable = sum(
            1 for c in cleaned
            if c.isalnum() or '一' <= c <= '鿿' or c in ' .,;:!?()[]{}，。；：！？（）【】'
        )
        if readable / len(cleaned) < 0.3 and len(cleaned) > 20:
            return "该来源文本疑似 OCR/编码异常，建议检查原始 PDF。"

    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length] + '...'


def format_sources_for_display(sources: list[dict]) -> list[dict]:
    """Convert raw chunk dicts into a display-friendly table format."""
    formatted = []
    for s in sources:
        formatted.append({
            '文件名': s.get('filename', '未知'),
            '页码': s.get('page', '?'),
            '资料类型': s.get('resource_type', '?'),
            '相似度': f"{s.get('score', 0):.2f}",
            '摘要（前80字）': clean_source_text(s.get('text', ''), 80),
        })
    return formatted


# ---- Quality validation ---------------------------------------------------

def validate_content_quality(content: str) -> dict:
    """Compatibility wrapper around the v2.1 quality checker."""
    from core.quality_checker import run_quality_checks

    return run_quality_checks(content)


def get_quality_warnings(checks: dict) -> list[str]:
    """Human-readable warnings for each failed quality check."""
    from core.quality_checker import get_quality_warnings as _warnings

    return _warnings(checks)
