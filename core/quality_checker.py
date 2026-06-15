"""Final PDF quality gate for StudyPilot AI outputs."""

from __future__ import annotations

import re
from pathlib import Path

from core.config import ROOT_DIR
from core.formula_renderer import is_complex_formula
from core.symbol_mapper import BANNED_TOKENS, contains_banned_tokens, textbook_forbidden_symbols


SOURCE_POLLUTION = [
    "OCR异常", "编码异常", "General Information", "SS号", "placeholder",
    "tag1-1", "tag1-2", "sqrtr", "hatz", "乱码方块",
]


def run_quality_checks(
    content: str,
    sources: list[dict] | None = None,
    figures: list[dict] | None = None,
    pdf_path: str | Path | None = None,
    textbook_style: dict | None = None,
    template_type: str = "lecture_deep",
) -> dict:
    sources = sources or []
    figures = figures or []
    textbook_style = textbook_style or {}
    markdown_stats = _markdown_stats(content, figures, sources)
    pdf_stats = inspect_final_pdf(pdf_path, textbook_style, figures)
    is_lecture = template_type in {"lecture_deep", "single_chapter", "chapter_review", ""}
    is_sprint = template_type == "exam_sprint"
    is_mock = template_type == "mock_exam"
    is_past = template_type == "past_paper"

    score = 100
    penalties: list[str] = []

    def penalize(points: int, reason: str) -> None:
        nonlocal score
        score -= points
        penalties.append(reason)

    if pdf_stats["forbidden_hits"]:
        penalize(30, "最终 PDF 出现禁用 token：" + "、".join(pdf_stats["forbidden_hits"]))
    if pdf_stats["latex_leak_hits"]:
        penalize(30, "最终 PDF 出现 LaTeX 原文：" + "、".join(pdf_stats["latex_leak_hits"][:6]))
    if pdf_stats["textbook_forbidden_symbols"]:
        penalize(18, "最终 PDF 出现教材未使用符号：" + "、".join(pdf_stats["textbook_forbidden_symbols"]))
    if pdf_stats["blank_page_count"] > 0:
        penalize(12, f"最终 PDF 存在疑似空白页 {pdf_stats['blank_page_count']} 页")
    if pdf_stats["source_pollution_hits"]:
        penalize(16, "来源页或正文出现污染文本：" + "、".join(pdf_stats["source_pollution_hits"]))
    if pdf_stats["cover_empty_bullets"]:
        penalize(8, "封面学习目标摘要存在空 bullet")
    if pdf_stats["toc_abnormal"]:
        penalize(8, "目录分页或目录密度异常")
    if pdf_stats["image_count"] > 900 and pdf_stats["pdf_size_bytes"] > 3_500_000:
        penalize(8, f"最终 PDF 图片数异常偏多：{pdf_stats['image_count']}")
    if pdf_stats["formula_image_count"] > max(16, markdown_stats["complex_formula_count"] + 6):
        penalize(8, f"公式图片数异常：{pdf_stats['formula_image_count']}")
    if is_lecture and markdown_stats["knowledge_point_count"] < 5:
        penalize(12, "核心知识点不足")
    if is_lecture and markdown_stats["example_count"] < 3:
        penalize(10, "典型例题不足")
    if is_lecture and markdown_stats["complete_example_count"] < 3:
        penalize(18, f"完整例题结构不足：{markdown_stats['complete_example_count']}/3")
    if is_lecture and markdown_stats["formula_summary_count"] == 0:
        penalize(8, "缺少公式总结表")
    if is_sprint and not (5 <= pdf_stats["page_count"] <= 10):
        penalize(12, f"考前冲刺页数不在 5-10 页：{pdf_stats['page_count']}")
    if is_sprint and not all(token in content for token in ["怎么考", "常见错误", "10 秒提醒"]):
        penalize(12, "考前冲刺缺少应急手册字段")
    if is_mock and not (8 <= pdf_stats["page_count"] <= 14):
        penalize(12, f"模拟试卷页数不在 8-14 页：{pdf_stats['page_count']}")
    if is_mock and not all(token in content for token in ["选择题", "填空题", "计算题", "答案与解析", "评分标准"]):
        penalize(16, "模拟试卷结构不完整")
    if is_past and not all(token in content for token in ["来源可靠性", "完整题干", "标准答案", "易错提醒"]):
        penalize(16, "真题精讲缺少题目优先结构或来源可靠性")
    if len(sources) == 0:
        penalize(8, "缺少参考来源")
    if pdf_stats["mismatch_warnings"]:
        penalize(10, "疑似图文错配：" + "、".join(pdf_stats["mismatch_warnings"]))
    if pdf_stats["duplicate_title_warnings"]:
        penalize(8, "疑似重复标题或断裂：" + "、".join(pdf_stats["duplicate_title_warnings"][:3]))

    score = max(0, score)
    checks = {
        **markdown_stats,
        **pdf_stats,
        "total_score": score,
        "grade": _grade(score),
        "penalties": penalties,
        "warnings": penalties,
        "is_complete": score >= 90 and not pdf_stats["forbidden_hits"] and not pdf_stats["source_pollution_hits"],
        "is_teaching_grade": score >= 92 and not penalties,
        "template_type": template_type,
    }
    return checks


def inspect_final_pdf(
    pdf_path: str | Path | None,
    textbook_style: dict | None = None,
    figures: list[dict] | None = None,
) -> dict:
    figures = figures or []
    path = Path(pdf_path) if pdf_path else None
    if not path or not path.exists():
        return {
            "pdf_exists": False,
            "page_count": 0,
            "pdf_size_bytes": 0,
            "image_count": 0,
            "formula_image_count": 0,
            "textbook_asset_image_count": 0,
            "blank_page_count": 0,
            "forbidden_hits": ["PDF_MISSING"],
            "source_pollution_hits": [],
            "latex_leak_hits": [],
            "textbook_forbidden_symbols": [],
            "cover_empty_bullets": False,
            "toc_abnormal": True,
            "mismatch_warnings": [],
            "duplicate_title_warnings": [],
            "pdf_text": "",
        }
    try:
        import fitz
    except Exception:
        return {
            "pdf_exists": True,
            "page_count": 0,
            "pdf_size_bytes": path.stat().st_size,
            "image_count": 0,
            "formula_image_count": 0,
            "textbook_asset_image_count": _count_textbook_assets(figures),
            "blank_page_count": 0,
            "forbidden_hits": [],
            "source_pollution_hits": [],
            "latex_leak_hits": [],
            "textbook_forbidden_symbols": [],
            "cover_empty_bullets": False,
            "toc_abnormal": False,
            "mismatch_warnings": [],
            "duplicate_title_warnings": [],
            "pdf_text": "",
        }

    text_parts: list[str] = []
    image_count = 0
    formula_image_count = 0
    blank_pages = 0
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc):
            page_text = page.get_text("text")
            text_parts.append(page_text)
            images = page.get_images(full=True)
            image_count += len(images)
            for img in images:
                w = img[2] if len(img) > 2 else 0
                h = img[3] if len(img) > 3 else 0
                if w > 120 and h < 120:
                    formula_image_count += 1
            if len(page_text.strip()) < 8 and not images and len(page.get_drawings()) < 2:
                blank_pages += 1
    pdf_text = "\n".join(text_parts)
    visible_text = _strip_page_furniture(pdf_text)
    forbidden = _scan_forbidden_pdf_text(visible_text)
    latex_leaks = _scan_latex_leaks(visible_text)
    pollution = [token for token in SOURCE_POLLUTION if token.lower() in visible_text.lower()]
    textbook_forbidden = [sym for sym in textbook_forbidden_symbols(textbook_style) if sym in visible_text]

    return {
        "pdf_exists": True,
        "page_count": len(text_parts),
        "pdf_size_bytes": path.stat().st_size,
        "image_count": image_count,
        "formula_image_count": formula_image_count,
        "textbook_asset_image_count": _count_textbook_assets(figures),
        "blank_page_count": blank_pages,
        "forbidden_hits": forbidden,
        "source_pollution_hits": pollution,
        "latex_leak_hits": latex_leaks,
        "textbook_forbidden_symbols": textbook_forbidden,
        "cover_empty_bullets": _has_cover_empty_bullets(pdf_text),
        "toc_abnormal": _toc_abnormal(pdf_text),
        "mismatch_warnings": _detect_figure_mismatch(pdf_text, figures),
        "duplicate_title_warnings": _detect_duplicate_titles(pdf_text),
        "pdf_text": pdf_text[:5000],
    }


def get_quality_warnings(checks: dict) -> list[str]:
    return list(checks.get("warnings", []))


def _markdown_stats(content: str, figures: list[dict], sources: list[dict]) -> dict:
    formulas = _extract_formula_sources(content)
    simple = sum(1 for f in formulas if not is_complex_formula(f))
    complex_count = sum(1 for f in formulas if is_complex_formula(f))
    return {
        "has_no_banned_tokens": not contains_banned_tokens(content),
        "banned_tokens": contains_banned_tokens(content),
        "knowledge_point_count": _count_knowledge_points(content),
        "has_min_knowledge_points": _count_knowledge_points(content) >= 5,
        "example_count": _count_examples(content),
        "has_min_examples": _count_examples(content) >= 3,
        "complete_example_count": _count_complete_examples(content),
        "valid_figure_count": _count_valid_figures(figures),
        "has_min_figures": _count_valid_figures(figures) >= 3,
        "formula_summary_count": len(re.findall(r"公式总结表|公式总结", content)),
        "has_references": bool(sources),
        "simple_formula_count": simple,
        "complex_formula_count": complex_count,
    }


def _extract_formula_sources(content: str) -> list[str]:
    formulas = re.findall(r"\$\$(.*?)\$\$", content, flags=re.S)
    formulas.extend(re.findall(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", content, flags=re.S))
    return [f.strip() for f in formulas if f.strip()]


def _scan_forbidden_pdf_text(text: str) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for token in BANNED_TOKENS + ["tag1-1", "tag1-2", "4pi", "frac", "□", "�"]:
        if token == "<font":
            hit = token in lower
        elif token in {"□", "�"}:
            hit = token in text
        else:
            hit = re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", lower) is not None
        if hit:
            found.append(token)
    return sorted(set(found))


def _scan_latex_leaks(text: str) -> list[str]:
    hits = re.findall(r"\\(?:frac|mathbf|nabla|varepsilon|rho|varphi|theta|tag|quad|cdot|hat|int)\b|\$[^$]*\$", text)
    return sorted(set(hits))


def _strip_page_furniture(text: str) -> str:
    return re.sub(r"StudyPilot AI · .+|\n\d+\n", "\n", text)


def _has_cover_empty_bullets(text: str) -> bool:
    cover = text.split("CONTENTS", 1)[0]
    goal_text_lines = [
        line.strip() for line in cover.splitlines()
        if line.strip() and line.strip() not in {"•", "·"} and not re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", line.strip())
    ]
    if len(goal_text_lines) >= 8:
        return False
    return bool(re.search(r"^[•·]\s*$", cover, flags=re.M))


def _toc_abnormal(text: str) -> bool:
    if "目录" not in text:
        return True
    toc = text.split("目录", 1)[1].split("本章定位", 1)[0] if "本章定位" in text else ""
    entries = len(re.findall(r"^\d{2}\s*$", toc, flags=re.M))
    section_hits = sum(1 for title in ["本章定位", "学习目标", "知识地图", "核心知识精讲", "公式总结", "典型例题", "高频考点", "考前速记", "自测题", "参考来源"] if title in text)
    return (entries < 6 and section_hits < 8) or len(toc) > 2800


def _detect_figure_mismatch(pdf_text: str, figures: list[dict]) -> list[str]:
    warnings: list[str] = []
    for fig in figures:
        title = str(fig.get("title", ""))
        target = str(fig.get("target_section", ""))
        if not title or not target or title not in pdf_text:
            continue
        pos = pdf_text.find(title)
        window = pdf_text[max(0, pos - 900): pos + 900]
        key = _semantic_key(title + target)
        if key and key not in window:
            warnings.append(f"{title} 未贴近 {target}")
    return warnings[:5]


def _detect_duplicate_titles(pdf_text: str) -> list[str]:
    warnings: list[str] = []
    for title in ["本章定位", "学习目标", "知识地图", "核心知识精讲", "公式总结表", "典型例题", "参考来源"]:
        if pdf_text.count(f"\n{title}\n") > 2:
            warnings.append(title)
    if re.search(r"\n---\n", pdf_text):
        warnings.append("Markdown 分隔线残留")
    return warnings


def _semantic_key(text: str) -> str:
    for key in ["高斯", "边界", "电位", "镜像", "库仑"]:
        if key in text:
            return key
    return ""


def _count_knowledge_points(content: str) -> int:
    matches = re.findall(r"^##\s*知识点\s*\d+", content, flags=re.M)
    if matches:
        return len(matches)
    core = re.search(r"^#\s*核心知识精讲\s*(.*?)(?=^#\s+|\Z)", content, flags=re.M | re.S)
    return len(re.findall(r"^##\s+", core.group(1), flags=re.M)) if core else 0


def _count_examples(content: str) -> int:
    matches = re.findall(r"^##\s*(?:例题|典型例题)\s*\d*", content, flags=re.M)
    if matches:
        return len(matches)
    examples = re.search(r"^#\s*典型例题\s*(.*?)(?=^#\s+|\Z)", content, flags=re.M | re.S)
    return len(re.findall(r"题目[：:]", examples.group(1))) if examples else 0


def _count_complete_examples(content: str) -> int:
    examples_section = re.search(r"^#\s*典型例题\s*(.*?)(?=^#\s+|\Z)", content, flags=re.M | re.S)
    if not examples_section:
        return 0
    chunks = re.split(r"^##\s*例题\s*\d+", examples_section.group(1), flags=re.M)[1:]
    required = ["题目", "考点", "难度", "常见考法", "解题模板", "思路分析", "标准解答", "易错提醒", "题型总结"]
    complete = 0
    for chunk in chunks:
        if all(key in chunk for key in required) and len(chunk) > 900:
            complete += 1
    return complete


def _count_valid_figures(figures: list[dict]) -> int:
    count = 0
    for figure in figures:
        path_text = str(figure.get("path", "") or figure.get("image_path", ""))
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_absolute():
            path = ROOT_DIR / path
        if path.exists() and path.stat().st_size > 1000:
            count += 1
    return count


def _count_textbook_assets(figures: list[dict]) -> int:
    count = 0
    for fig in figures:
        path = str(fig.get("path", "") or fig.get("image_path", ""))
        if "data/assets/" in path or "/data/assets/" in path:
            count += 1
    return count


def _grade(total: int) -> str:
    if total >= 95:
        return "封版候选 (A+)"
    if total >= 90:
        return "教辅级 (A)"
    if total >= 80:
        return "良好 (B)"
    if total >= 70:
        return "合格 (C)"
    return "不合格 (D)"
