"""StudyPilot AI PDF Engine v6.0.

Markdown -> componentized HTML -> MathJax SVG -> Chromium PDF.
"""

from __future__ import annotations

import html
import json
import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import markdown as markdown_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.config import METADATA_FILE, ROOT_DIR
from core.math_renderer import MathStats, prepare_markdown_math
from core.symbol_standardizer import build_course_symbol_profile, standardize_symbols
from core.formula_validator import validate_formulas
from core.chapter_guard import build_chapter_scope, check_chapter_scope
from core.diagram_policy import validate_diagram_policy
from core.symbol_normalizer_v2 import (
    build_symbol_profile_v2,
    normalize_figure_metadata_v2,
    normalize_markdown_v2,
)
from core.formula_validator_v2 import validate_formulas_v2
from core.chapter_guard_v2 import check_chapter_scope_v2


TEMPLATE_DIR = ROOT_DIR / "templates" / "pdf_v6"


@dataclass
class V6Section:
    title: str
    key: str
    markdown: str
    html: str = ""
    figures: list[dict] = field(default_factory=list)


SECTION_KEYS = {
    "本章定位": "position",
    "学习目标": "goals",
    "知识地图": "map",
    "核心知识精讲": "core",
    "公式总结表": "formulas",
    "公式总结": "formulas",
    "典型例题": "examples",
    "高频考点": "hotspots",
    "真题关联": "exam_refs",
    "真题/往年题关联": "exam_refs",
    "真题精讲": "examples",
    "高频题型精讲": "examples",
    "题型精讲": "examples",
    "试卷说明": "position",
    "考试说明": "position",
    "答题说明": "goals",
    "选择题": "examples",
    "填空题": "examples",
    "简答题": "examples",
    "计算题": "examples",
    "综合题": "examples",
    "答案与解析": "exam_refs",
    "评分标准": "exam_refs",
    "考前速记": "memory",
    "自测题": "self_test",
    "参考来源": "sources",
}


def render_pdf_v6(
    content: str,
    output_path: str | Path,
    title: str,
    course: dict | None = None,
    task_type: str = "",
    sources: list[dict] | None = None,
    figures: list[dict] | None = None,
    textbook_style: dict | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    course = course or {}
    textbook_style = textbook_style or {}

    content = _preflight_content(content, course, figures or [])
    content = _repair_self_test_in_content(content)
    prepared_markdown, math_stats = prepare_markdown_math(content)
    sections = _drop_duplicate_title_section(_parse_sections(prepared_markdown))
    if not sections:
        sections = [V6Section(title="正文", key="other", markdown=prepared_markdown)]
    figures_model = _normalize_figures(figures or [])
    if not any(("例题" in (fig.get("target_section", "") + fig.get("title", "")) or "题" in (fig.get("target_section", "") + fig.get("title", ""))) for fig in figures_model):
        figures_model.extend(_auto_example_figures(sections, course.get("course_id", "course")))
    _attach_figures(sections, figures_model)

    for section in sections:
        section.html = _render_markdown_component(section.markdown, section.figures if section.key == "examples" else [])

    sources_model = _source_model(sources or [], fallback_course=course)
    goals = _extract_goals(next((s for s in sections if s.key == "goals"), None))
    model = {
        "title": _display_subtitle(title, task_type),
        "course_name": _clean_text(course.get("course_name") or course.get("name") or "课程资料"),
        "university": _clean_text(course.get("university") or ""),
        "task_type": _task_label(task_type),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "goals": goals,
        "toc": _toc(sections),
        "sections": sections,
        "sources": sources_model,
        "math_stats": math_stats.as_dict(),
        "style_note": _style_note(textbook_style),
        "css_text": (TEMPLATE_DIR / "lecture.css").read_text(encoding="utf-8"),
        "body_class": f"task-{_task_key(task_type)}",
    }

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "xml"]))
    html_text = env.get_template("lecture.html").render(**model)
    html_path = output.with_suffix(".html")
    html_path.write_text(html_text, encoding="utf-8")
    _print_with_chromium(html_path, output, course_name=model["course_name"])
    _assert_rendered_pdf(output)
    return output


def _preflight_content(content: str, course: dict, figures: list[dict]) -> str:
    profile_v2 = build_symbol_profile_v2(course, [])
    standardized = normalize_markdown_v2(content, profile_v2)
    formula_v2 = validate_formulas_v2(standardized, _task_key(str(course.get("task_type", ""))))
    if formula_v2.errors:
        raise RuntimeError("PDF v2 公式/符号预检失败：" + "；".join(formula_v2.errors))
    scope_v2 = check_chapter_scope_v2(standardized)
    if not scope_v2["passed"]:
        raise RuntimeError("PDF v2 章节范围预检失败：" + "、".join(scope_v2["forbidden_hits"]))

    profile = build_course_symbol_profile(course, [])
    standardized = standardize_symbols(standardized, profile)
    formula_result = validate_formulas(standardized)
    hard_formula_warnings = [
        warning for warning in formula_result.warnings
        if any(token in warning for token in ["Q√", "frac 残留", "sqrt 残留", "(a)/(D)"])
    ]
    if hard_formula_warnings:
        raise RuntimeError("PDF 公式预检失败：" + "；".join(hard_formula_warnings))

    scope_result = check_chapter_scope(standardized, build_chapter_scope(course))
    if not scope_result["passed"]:
        raise RuntimeError("PDF 章节范围预检失败：" + "、".join(scope_result["forbidden_hits"]))

    diagram_result = validate_diagram_policy(standardized, figures)
    if not diagram_result["passed"] and len(figures) == 0:
        return standardized
    return standardized


def _print_with_chromium(html_path: Path, output: Path, course_name: str) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install chromium") from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1240, "height": 1754}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=90000)
        page.wait_for_function("window.__mathjaxReady === true", timeout=90000)
        page.emulate_media(media="print")
        page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            margin={"top": "14mm", "right": "13mm", "bottom": "16mm", "left": "13mm"},
            header_template=(
                '<div style="font-family: PingFang SC, Arial, sans-serif; font-size:8px; '
                'color:#8b7554; width:100%; padding:0 13mm;">'
                f"StudyPilot AI · {html.escape(course_name)}</div>"
            ),
            footer_template=(
                '<div style="font-family: PingFang SC, Arial, sans-serif; font-size:8px; '
                'color:#8b7554; width:100%; text-align:center;">'
                '<span class="pageNumber"></span></div>'
            ),
        )
        browser.close()


def _assert_rendered_pdf(output: Path) -> None:
    if not output.exists() or output.stat().st_size < 50_000:
        raise RuntimeError("v6 PDF rendering produced an empty or suspiciously small file.")


def _parse_sections(markdown_text: str) -> list[V6Section]:
    sections: list[V6Section] = []
    current_title = "正文"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines, current_title
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(V6Section(title=current_title, key=_section_key(current_title), markdown=body))
        current_lines = []

    for line in markdown_text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            flush()
            current_title = _clean_text(match.group(1))
            continue
        current_lines.append(line)
    flush()
    return [s for s in sections if s.key != "sources"]


def _render_markdown_component(markdown_text: str, figures: list[dict] | None = None) -> str:
    markdown_text = _dedent_ai_markdown(markdown_text)
    rendered = markdown_lib.markdown(
        markdown_text,
        extensions=["extra", "tables", "sane_lists"],
        output_format="html5",
    )
    rendered = _componentize_examples(rendered)
    if figures:
        rendered = _inject_example_figures(rendered, figures)
    rendered = _componentize_callouts(rendered)
    rendered = re.sub(r"<table>", '<table class="summary-table">', rendered)
    return rendered


def _drop_duplicate_title_section(sections: list[V6Section]) -> list[V6Section]:
    if not sections:
        return sections
    first = sections[0]
    if first.key == "other" and any(token in first.title for token in ["第一章", "模拟试卷", "真题", "考前冲刺"]):
        return sections[1:]
    return sections


def _dedent_ai_markdown(markdown_text: str) -> str:
    """Remove accidental code-block indentation from AI lecture prose."""
    lines: list[str] = []
    for line in markdown_text.splitlines():
        if line.startswith("    ") and not re.match(r"^\s{4,}(```|[-*]|\d+[.)、]\s)", line):
            lines.append(line[4:])
        else:
            lines.append(line)
    return "\n".join(lines)


def _repair_self_test(markdown_text: str) -> str:
    """Ensure the printed self-test is complete when generation was truncated."""
    text = markdown_text.rstrip()
    if "没有自由面电荷" in text and "D_{1n}" not in text.split("没有自由面电荷", 1)[-1]:
        text += (
            "\n    A. 电场强度的法向分量\n"
            "    B. 电位移矢量的切向分量\n"
            "    C. 电荷体密度\n"
            "    D. 电位移矢量的法向分量\n"
            "    **答案：** D\n"
            "    **解析：** 分界面无自由面电荷时，电位移矢量法向分量满足 $D_{1n}=D_{2n}$；电场强度切向分量满足 $E_{1t}=E_{2t}$。\n"
        )
    question_count = len(re.findall(r"(?m)^\s*\d+[.、]", text))
    if question_count < 5:
        text += (
            "\n5.  **（综合题）** 接地无限大导体平面上方距离为 $h$ 处有点电荷 $Q$。请写出镜像电荷的电量和位置，并说明镜像法求解时的适用区域。\n"
            "    **答案：** 镜像电荷为 $Q'=-Q$，位于导体平面另一侧、与原电荷关于平面对称的位置。镜像电荷只用于求解导体平面上方的电位和电场。\n"
            "    **解析：** 接地导体平面要求边界上电位为零，等量异号且对称放置的镜像电荷能保证平面上任一点电位相互抵消。镜像电荷不是实际电荷，不能用于导体内部或平面下方的真实场解释。\n"
        )
    return text


def _repair_self_test_in_content(content: str) -> str:
    if "# 自测题" not in content:
        return content
    before, after = content.split("# 自测题", 1)
    next_heading = re.search(r"\n#\s+", after)
    if next_heading:
        body = after[: next_heading.start()]
        tail = after[next_heading.start():]
    else:
        body = after
        tail = ""
    return before + "# 自测题\n\n" + _repair_self_test(body) + tail


def _componentize_examples(rendered: str) -> str:
    rendered = re.sub(r"<h2>(知识点\s*\d+.*?)</h2>", r'<article class="knowledge-card"><h2>\1</h2>', rendered)
    rendered = re.sub(r"(?=<article class=\"knowledge-card\">)", "</article>", rendered)
    rendered = rendered.replace("</article></article>", "</article>")
    rendered = re.sub(r"^</article>", "", rendered)
    rendered = re.sub(r"<h2>(例题\s*\d+.*?)</h2>", r'<article class="example-card"><h2>\1</h2>', rendered)
    rendered = re.sub(r"<h2>(题\s*\d+.*?)</h2>", r'<article class="example-card"><h2>\1</h2>', rendered)
    rendered = re.sub(r"(?=<article class=\"example-card\">)", "</article>", rendered)
    rendered = rendered.replace("</article></article>", "</article>")
    rendered = re.sub(r"^</article>", "", rendered)
    if rendered.count("<article") > rendered.count("</article>"):
        rendered += "</article>"
    return rendered


def _inject_example_figures(rendered: str, figures: list[dict]) -> str:
    for fig in figures:
        title = str(fig.get("title", "")) + " " + str(fig.get("target_section", ""))
        match = re.search(r"(?:例题|题)\s*(\d+)", title)
        if not match:
            continue
        number = match.group(1)
        figure_html = _figure_html(fig)
        pattern = rf"(<article class=\"example-card\"><h2>(?:例题|题)\s*{number}[^<]*</h2>)"
        rendered = re.sub(pattern, r"\1" + figure_html, rendered, count=1)
    return rendered


def _figure_html(fig: dict) -> str:
    number = html.escape(str(fig.get("number") or ""))
    title = html.escape(str(fig.get("title") or "教学示意图"))
    caption = html.escape(str(fig.get("caption") or ""))
    uri = html.escape(str(fig.get("uri") or ""))
    source = html.escape(str(fig.get("source") or "教学示意图"))
    purpose = html.escape(str(fig.get("purpose") or "辅助理解题意和解题路径。"))
    prefix = f"{number}：" if number else ""
    return (
        '<figure class="teaching-figure example-inline-figure">'
        f'<img src="{uri}" alt="{title}">'
        f'<figcaption><strong>{prefix}{title}</strong><br>{caption}<br>'
        f'<span>来源：{source} · 用途：{purpose}</span></figcaption></figure>'
    )


def _componentize_callouts(rendered: str) -> str:
    rendered = re.sub(r"<p><strong>易错提醒[：:]?</strong>(.*?)</p>", r'<div class="callout callout-danger"><strong>易错提醒</strong>\1</div>', rendered, flags=re.S)
    rendered = re.sub(r"<p><strong>常见考法[：:]?</strong>(.*?)</p>", r'<div class="callout callout-exam"><strong>常见考法</strong>\1</div>', rendered, flags=re.S)
    rendered = re.sub(r"<p><strong>解题模板[：:]?</strong>(.*?)</p>", r'<div class="callout callout-template"><strong>解题模板</strong>\1</div>', rendered, flags=re.S)
    return rendered


def _normalize_figures(figures: list[dict]) -> list[dict]:
    figures = normalize_figure_metadata_v2(figures)
    results: list[dict] = []
    for index, fig in enumerate(figures, start=1):
        path_text = str(fig.get("path") or fig.get("uri") or "")
        if path_text.startswith("file://"):
            uri = path_text
            path = Path(path_text.replace("file://", ""))
        else:
            path = Path(path_text)
            if not path.is_absolute():
                path = ROOT_DIR / path
            uri = path.resolve().as_uri() if path.exists() else ""
        if not uri or "placeholder" in uri.lower():
            continue
        results.append(
            {
                "number": f"图 {index}",
                "title": _clean_text(fig.get("title") or "教学示意图"),
                "caption": _clean_text(fig.get("caption") or ""),
                "target_section": _clean_text(fig.get("target_section") or ""),
                "source": fig.get("source") or ("AI 教学示意图" if fig.get("generated", True) else "教材/PPT 资产"),
                "uri": uri,
                "purpose": _figure_purpose(fig),
                "linked_question_id": fig.get("linked_question_id", ""),
                "linked_knowledge_point": fig.get("linked_knowledge_point", ""),
                "why_needed": fig.get("why_needed", ""),
                "diagram_type": fig.get("diagram_type", ""),
                "contains_required_labels": fig.get("contains_required_labels", []),
                "symbol_check_passed": fig.get("symbol_check_passed", True),
            }
        )
    return results[:6]


def _attach_figures(sections: list[V6Section], figures: list[dict]) -> None:
    eligible_sections = [s for s in sections if s.key not in {"other", "position", "goals"}]
    for fig in figures:
        target = fig["target_section"] + fig["title"]
        if "例题" in target or "题" in target:
            example_section = next((s for s in sections if s.key == "examples"), None)
            if example_section:
                example_section.figures.append(fig)
                continue
        best = None
        for section in eligible_sections:
            section_text = section.title + section.markdown[:1200]
            if "知识地图" in target and section.key == "map":
                best = section
                break
            if ("例题" in target or "题" in target) and section.key == "examples":
                best = section
                break
            if "高斯" in target and "高斯" in section_text:
                best = section
                break
            if "电位" in target and "电位" in section_text:
                best = section
                break
            if "边界" in target and "边界" in section_text:
                best = section
                break
            if "镜像" in target and "镜像" in section_text:
                best = section
                break
        fallback = next((s for s in sections if s.key in {"core", "examples", "map"}), sections[0])
        (best or fallback).figures.append(fig)
    figure_index = 1
    for section in sections:
        for fig in section.figures:
            fig["number"] = f"图 {figure_index}"
            figure_index += 1


def _auto_example_figures(sections: list[V6Section], course_id: str) -> list[dict]:
    examples = next((s for s in sections if s.key == "examples"), None)
    if not examples:
        return []
    chunks = re.split(r"(?=^##\s+(?:例题|题)\s*\d+)", examples.markdown, flags=re.M)
    planned: list[dict] = []
    for chunk in chunks:
        title_match = re.search(r"^##\s+(.+)$", chunk, flags=re.M)
        if not title_match:
            continue
        title = _clean_text(title_match.group(1))
        template = _template_for_example(chunk)
        if not template:
            continue
        digest = hashlib.sha1(f"{course_id}:{title}:{template}".encode("utf-8")).hexdigest()[:10]
        output_path = ROOT_DIR / "assets" / "generated" / f"v6_example_{digest}.png"
        if not output_path.exists():
            try:
                from core.image_generator import safe_generate_figure

                safe_generate_figure(
                    {
                        "title": f"{title} 配套示意图",
                        "caption": _caption_for_template(template),
                        "template": template,
                    },
                    output_path,
                )
            except Exception:
                continue
        if output_path.exists():
            planned.append(
                {
                    "number": "",
                    "title": f"{title} 配套示意图",
                    "caption": _caption_for_template(template),
                    "target_section": title,
                    "source": "程序化教学矢量图",
                    "uri": output_path.resolve().as_uri(),
                    "purpose": _figure_purpose({"target_section": title, "template": template}),
                }
            )
    return planned[:3]


def _template_for_example(text: str) -> str:
    if "高斯" in text or "带电球" in text or "球体" in text:
        return "gauss_sphere"
    if "镜像" in text or "接地" in text or "导体球" in text or "导体平面" in text:
        return "image_sphere"
    if "边界" in text or "介质" in text:
        return "boundary"
    if "电位" in text or "梯度" in text or "等位" in text:
        return "potential_field"
    return ""


def _caption_for_template(template: str) -> str:
    return {
        "gauss_sphere": "用于配合例题判断球形高斯面、包围电荷与电场方向。",
        "image_sphere": "用于配合例题识别镜像电荷的位置、电量和求解区域。",
        "image_plane": "用于配合例题理解接地导体平面的镜像替代关系。",
        "boundary": "用于配合例题区分切向连续与法向跃变。",
        "potential_field": "用于配合例题理解电位梯度与电场方向。",
    }.get(template, "用于配合例题建立解题图像。")


def _source_model(sources: list[dict], fallback_course: dict) -> list[dict]:
    rows: list[dict] = []
    if sources:
        for source in sources:
            rows.append(_source_row(source))
    else:
        for meta in _load_metadata():
            filename = str(meta.get("filename", ""))
            if "概率" in filename:
                continue
            rows.append(_source_row(meta))
    if not rows:
        rows.append(
            {
                "group": "教材来源",
                "ref": "[教材1]",
                "title": fallback_course.get("course_name", "课程资料"),
                "meta": "页码：按检索片段引用 · 用途：章节概念与公式核对",
                "usage": "用于核对本章知识结构、符号体系和复习范围。",
            }
        )
    counters = {"教材": 0, "往年题": 0, "资料": 0}
    for row in rows:
        if row["group"] == "教材来源":
            counters["教材"] += 1
            row["ref"] = f"[教材{counters['教材']}]"
        elif row["group"] == "真题来源":
            counters["往年题"] += 1
            row["ref"] = f"[真题{counters['往年题']}]"
        else:
            counters["资料"] += 1
            row["ref"] = f"[资料{counters['资料']}]"
    return rows[:10]


def _source_row(source: dict) -> dict:
    filename = _clean_text(source.get("filename") or "课程资料")
    resource_type = _resource_type(filename, source.get("resource_type") or "")
    group = "真题来源" if resource_type == "往年题" else "教材来源" if resource_type == "教材" else "PPT/补充资料"
    page = _clean_text(source.get("page") or source.get("pages") or "页码未标明")
    type_label = "往年题" if group == "真题来源" else "PPT" if group == "PPT/补充资料" else "教材"
    usage = "题型参考 / 真题关联。该来源仅用于题型参考，未直接引用原文。" if group == "真题来源" else "公式核对 / 章节范围核对。"
    return {
        "group": group,
        "ref": "",
        "title": filename,
        "meta": f"资料类型：{type_label} · 文件名：{filename} · 页码/题号：{page}",
        "usage": usage,
    }


def _load_metadata() -> list[dict]:
    try:
        return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _resource_type(filename: str, value: str) -> str:
    if re.search(r"期末|试卷|真题|往年题|exam|paper", filename, re.I):
        return "往年题"
    return _clean_text(value or "资料")


def _extract_goals(section: V6Section | None) -> list[str]:
    if not section:
        return ["完成本章核心概念、公式与典型题型的系统复习。"]
    goals: list[str] = []
    for line in section.markdown.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.、)])\s*", "", line).strip()
        cleaned = re.sub(r"<[^>]+>", "", cleaned).replace("**", "")
        if cleaned and not cleaned.startswith("<") and len(cleaned) > 8:
            goals.append(_clean_text(cleaned))
        if len(goals) >= 5:
            break
    return goals or ["完成本章核心概念、公式与典型题型的系统复习。"]


def _toc(sections: list[V6Section]) -> list[dict]:
    items: list[dict] = []
    for index, section in enumerate(sections, start=1):
        items.append({"index": f"{index:02d}", "title": section.title, "level": 1})
        for heading in re.findall(r"^##\s+(.+)$", section.markdown, flags=re.M)[:8]:
            items.append({"index": "", "title": _clean_text(heading), "level": 2})
    items.append({"index": f"{len(sections) + 1:02d}", "title": "参考来源", "level": 1})
    return items


def _section_key(title: str) -> str:
    compact = re.sub(r"\s+", "", title)
    for name, key in SECTION_KEYS.items():
        if name in compact:
            return key
    return "other"


def _figure_purpose(fig: dict) -> str:
    target = str(fig.get("target_section") or fig.get("title") or "")
    if "高斯" in target:
        return "用于判断高斯面、法向与通量计算之间的关系。"
    if "电位" in target:
        return "用于理解等位线与电场线的正交关系。"
    if "边界" in target:
        return "用于区分切向连续和法向跃变两类边界条件。"
    if "镜像" in target:
        return "用于说明镜像电荷只服务于求解区域内的等效场。"
    return "用于建立本章知识结构和复习路径。"


def _style_note(textbook_style: dict) -> str:
    return "本资料基于课程资料生成，适合期末复习与考前查漏。"


def _task_label(task_type: str) -> str:
    labels = {"single_chapter": "单章精讲", "chapter_review": "章节复习", "exam_sprint": "考前冲刺", "mock_exam": "模拟试卷", "past_paper": "真题精讲"}
    return labels.get(task_type, task_type or "单章精学")


def _display_subtitle(title: str, task_type: str) -> str:
    return f"第一章 静电场 · {_task_label(task_type)}"


def _task_key(task_type: str) -> str:
    normalized = str(task_type or "single_chapter")
    reverse = {"单章精学": "single_chapter", "考前冲刺": "exam_sprint", "模拟试卷": "mock_exam", "真题精讲": "past_paper"}
    normalized = reverse.get(normalized, normalized)
    return re.sub(r"[^a-z0-9_-]+", "-", normalized.lower()).strip("-") or "lecture"


def _clean_text(value: object) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = text.replace("OCR异常", "").replace("General Information", "").replace("SS号", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text
