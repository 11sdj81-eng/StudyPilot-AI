"""Professional StudyPilot lecture PDF renderer."""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.config import METADATA_FILE, ROOT_DIR
from core.formula_renderer import is_complex_formula, render_formula_image
from core.symbol_mapper import (
    build_symbol_policy,
    formula_to_readable_text,
    normalize_generated_content,
    normalize_text_symbols,
)


TEMPLATE_DIR = ROOT_DIR / "templates" / "pdf"

# v3.0: task-type → PDF template mapping
TASK_TO_TEMPLATE = {
    "single_chapter": "lecture_deep",
    "chapter_review": "lecture_deep",
    "exam_sprint": "sprint_notes",
    "hotspots": "lecture_deep",
    "mock_exam": "exam_paper",
    "past_paper": "lecture_deep",
    "learning_plan": "study_plan",
    "qa": "qa_notes",
    "custom": "lecture_deep",
}

# v3.0: user-selectable PDF styles
PDF_STYLES = {
    "textbook": {"name": "教辅讲义风", "css": "lecture_style.css", "body_class": "style-textbook"},
    "goodnotes": {"name": "GoodNotes 笔记风", "css": "lecture_style.css", "body_class": "style-goodnotes"},
    "kaoyan": {"name": "考研讲义风", "css": "lecture_style.css", "body_class": "style-kaoyan"},
    "print": {"name": "简洁黑白打印风", "css": "lecture_style.css", "body_class": "style-print"},
    "exam": {"name": "试卷风", "css": "lecture_style.css", "body_class": "style-exam"},
}

SECTION_ORDER = [
    ("position", "本章定位"),
    ("goals", "学习目标"),
    ("map", "知识地图"),
    ("core", "核心知识精讲"),
    ("formulas", "公式总结表"),
    ("examples", "典型例题"),
    ("hotspots", "高频考点"),
    ("truth", "真题关联"),
    ("memory", "考前速记"),
    ("self_test", "自测题"),
]

SECTION_ALIASES = {
    "position": ["本章定位", "章节定位"],
    "goals": ["学习目标", "本章学习目标"],
    "map": ["知识地图", "思维导图"],
    "core": ["核心知识精讲", "核心知识点"],
    "formulas": ["公式总结表", "公式总结"],
    "examples": ["典型例题", "例题"],
    "hotspots": ["高频考点"],
    "truth": ["真题关联", "往年题关联", "真题/往年题关联"],
    "memory": ["考前速记", "速记"],
    "self_test": ["自测题", "练习题"],
}

SECTION_CLASS = {
    "position": "section-position",
    "goals": "section-goals",
    "map": "section-map",
    "core": "section-core",
    "formulas": "section-formulas",
    "examples": "section-examples",
    "hotspots": "section-hotspots",
    "truth": "section-truth",
    "memory": "section-memory",
    "self_test": "section-self-test",
    "other": "section-other",
}


@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    alt: str = ""
    path: str = ""


@dataclass
class Section:
    key: str
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class RenderContext:
    textbook_style: dict
    symbol_policy: dict
    formula_index: int = 0
    simple_formula_count: int = 0
    complex_formula_count: int = 0
    formula_image_count: int = 0
    max_formula_images: int = 12
    figure_index: int = 0

    def next_formula_number(self) -> str:
        self.formula_index += 1
        return f"1-{self.formula_index}"

    def next_figure_number(self) -> str:
        self.figure_index += 1
        return f"图 {self.figure_index}"


def render_professional_pdf(
    content: str,
    output_path: str | Path,
    title: str,
    course: dict | None = None,
    task_type: str = "",
    sources: list[dict] | None = None,
    figures: list[dict] | None = None,
    textbook_style: dict | None = None,
    template_type: str = "",
    pdf_style: str = "textbook",
) -> Path:
    _prepare_weasyprint_env()
    try:
        from weasyprint import CSS, HTML
    except Exception as exc:
        raise RuntimeError(_weasyprint_help(exc)) from exc

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # v3.0: resolve template type
    if not template_type:
        template_type = TASK_TO_TEMPLATE.get(task_type, "lecture_deep")

    # v3.0: resolve style
    style_cfg = PDF_STYLES.get(pdf_style, PDF_STYLES["textbook"])

    lecture = build_lecture_model(
        content, course or {}, title, task_type,
        sources or [], figures or [],
        textbook_style=textbook_style or {},
        template_type=template_type,
    )

    # Select HTML template based on template_type
    template_file = _template_for_type(template_type)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "xml"]))
    html_text = env.get_template(template_file).render(**lecture, body_class=style_cfg["body_class"])
    HTML(string=html_text, base_url=str(ROOT_DIR)).write_pdf(
        str(output),
        stylesheets=[CSS(filename=str(TEMPLATE_DIR / style_cfg["css"]))],
    )
    return output


def build_lecture_model(
    content: str,
    course: dict,
    title: str,
    task_type: str,
    sources: list[dict],
    figures: list[dict],
    textbook_style: dict | None = None,
    template_type: str = "lecture_deep",
) -> dict:
    textbook_style = textbook_style or {}
    context = RenderContext(
        textbook_style=textbook_style,
        symbol_policy=build_symbol_policy(textbook_style),
    )
    content = normalize_generated_content(content, textbook_style)
    sections = _parse_sections(content)
    section_map = _merge_sections(sections)
    source_rows, source_groups = _format_sources_grouped(sources)
    source_badges = _source_badges_from_groups(source_groups)
    figures_model = _normalize_figures(figures, content)
    figures_by_section = _group_figures_by_section(figures_model, section_map)

    # v2.2: textbook-style disclaimer
    from core.textbook_style_analyzer import style_summary_for_display
    style_note = style_summary_for_display(textbook_style) if textbook_style.get("confidence", 0) > 0 else (
        "符号体系采用通用课程规范，建议上传教材以提高一致性。"
    )

    ordered_sections: list[dict] = []
    toc: list[dict] = []
    index = 1
    for key, display_title in SECTION_ORDER:
        section = section_map.get(key)
        if not isinstance(section, Section):
            continue
        section_toc = _section_toc(section.blocks)
        html_text = _render_blocks(
            section.blocks,
            figures=figures_by_section.get(key, []),
            source_badges=source_badges if key in {"position", "core", "examples", "truth"} else [],
            context=context,
        )
        ordered_sections.append(
            {
                "key": key,
                "title": display_title,
                "class_name": SECTION_CLASS[key],
                "html": html_text,
                "source_badges": source_badges if key in {"position", "core", "examples", "truth"} else [],
            }
        )
        toc.append({"level": 1, "title": display_title, "index": f"{index:02d}"})
        for item in section_toc[:10]:
            toc.append(item)
        index += 1

    for section in section_map.get("other", []):
        if not isinstance(section, Section):
            continue
        ordered_sections.append(
            {
                "key": "other",
                "title": section.title,
                "class_name": SECTION_CLASS["other"],
                "html": _render_blocks(section.blocks, figures=[], source_badges=[], context=context),
                "source_badges": [],
            }
        )
        toc.append({"level": 1, "title": section.title, "index": f"{index:02d}"})
        index += 1

    return {
        "title": _clean_plain(title),
        "course_name": _clean_plain(course.get("course_name", title)),
        "university": _clean_plain(course.get("university", "")),
        "task_type": _clean_plain(_resolve_task_label(task_type) or _guess_task_type(title)),
        "template_type": template_type,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "style_note": style_note,
        "goals": _extract_goal_items(section_map.get("goals")),
        "toc": toc,
        "sections": ordered_sections,
        "sources": source_rows,
        "source_groups": source_groups,
        "formula_stats": {
            "simple": context.simple_formula_count,
            "complex": context.complex_formula_count,
            "images": context.formula_image_count,
        },
    }


def _template_for_type(template_type: str) -> str:
    """Map logical template type to an HTML template file."""
    mapping = {
        "lecture_deep": "lecture_template.html",
        "exam_paper": "exam_paper_template.html",
        "sprint_notes": "sprint_notes_template.html",
        "study_plan": "study_plan_template.html",
        "qa_notes": "lecture_template.html",  # reuse lecture for QA
    }
    return mapping.get(template_type, "lecture_template.html")


def _prepare_weasyprint_env() -> None:
    homebrew_lib = "/opt/homebrew/lib"
    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if Path(homebrew_lib).exists() and homebrew_lib not in current.split(":"):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{homebrew_lib}:{current}" if current else homebrew_lib


def _weasyprint_help(exc: Exception) -> str:
    return (
        "WeasyPrint native libraries are unavailable.\n"
        "On macOS with Homebrew, install them with:\n"
        "  brew install glib pango gdk-pixbuf libffi\n"
        f"Original error: {exc}"
    )


def _parse_sections(content: str) -> list[Section]:
    content = _strip_raw_html(_normalize_display_math(content))
    sections: list[Section] = []
    current: Section | None = None
    paragraph: list[str] = []
    in_formula = False
    formula_lines: list[str] = []

    def ensure_current() -> Section:
        nonlocal current
        if current is None:
            current = Section("other", "正文")
            sections.append(current)
        return current

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            ensure_current().blocks.append(Block("paragraph", "\n".join(paragraph).strip()))
        paragraph = []

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped == "$$":
            if in_formula:
                ensure_current().blocks.append(Block("formula", "\n".join(formula_lines).strip()))
                formula_lines = []
                in_formula = False
            else:
                flush_paragraph()
                in_formula = True
            continue
        if in_formula:
            formula_lines.append(stripped)
            continue
        heading = re.match(r"^(#{1,3})\s+(.+?)\s*$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            heading_text = _clean_plain(heading.group(2))
            if level == 1:
                current = Section(_section_key(heading_text), heading_text)
                sections.append(current)
            else:
                ensure_current().blocks.append(Block("heading", heading_text, level=level))
            continue
        image = re.match(r"!\[(.*?)\]\((.*?)\)", stripped)
        if image:
            flush_paragraph()
            path = image.group(2).strip()
            if "placeholder" not in path.lower():
                ensure_current().blocks.append(Block("image", alt=_clean_plain(image.group(1)), path=path))
            continue
        if not stripped:
            flush_paragraph()
            continue
        paragraph.append(stripped)

    if in_formula and formula_lines:
        ensure_current().blocks.append(Block("formula", "\n".join(formula_lines).strip()))
    flush_paragraph()
    return sections


def _merge_sections(sections: list[Section]) -> dict:
    merged: dict[str, Section | list[Section]] = {"other": []}
    for section in sections:
        if section.key == "other":
            merged["other"].append(section)
        elif section.key in merged and isinstance(merged[section.key], Section):
            merged[section.key].blocks.extend(section.blocks)
        else:
            merged[section.key] = section
    return merged


def _section_key(title: str) -> str:
    normalized = re.sub(r"\s+", "", title)
    for key, aliases in SECTION_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return key
    return "other"


def _section_toc(blocks: list[Block]) -> list[dict]:
    items: list[dict] = []
    for block in blocks:
        if block.kind == "heading":
            items.append({"level": min(block.level, 3), "title": block.text, "index": ""})
    return items


def _render_blocks(
    blocks: list[Block],
    figures: list[dict],
    source_badges: list[str],
    context: RenderContext | None = None,
) -> str:
    context = context or RenderContext({}, build_symbol_policy({}))
    html_parts: list[str] = []
    pending_list: list[str] = []
    remaining_figures = list(figures)

    def flush_list() -> None:
        nonlocal pending_list
        if pending_list:
            items = "".join(f"<li>{_render_inline(item, context)}</li>" for item in pending_list)
            html_parts.append(f"<ul>{items}</ul>")
        pending_list = []

    if source_badges:
        badges = "".join(f"<span>{html.escape(ref)}</span>" for ref in source_badges)
        html_parts.append(f'<div class="source-badges">参考依据：{badges}</div>')

    for block in blocks:
        if block.kind == "heading":
            flush_list()
            tag = "h3" if block.level >= 3 else "h2"
            html_parts.append(f"<{tag}>{html.escape(block.text)}</{tag}>")
            matched = [fig for fig in remaining_figures if _heading_matches_figure(block.text, [fig])]
            if matched:
                html_parts.extend(_render_figure(fig, context) for fig in matched)
                remaining_figures = [fig for fig in remaining_figures if fig not in matched]
        elif block.kind == "formula":
            flush_list()
            html_parts.append(_render_formula(block.text, context, display=True))
        elif block.kind == "image":
            flush_list()
            image_html = _render_image(block.path, block.alt)
            if image_html:
                html_parts.append(image_html)
        elif block.kind == "paragraph":
            if _looks_like_table(block.text):
                flush_list()
                html_parts.append(_render_table(block.text, context))
                continue
            for line in block.text.splitlines():
                line = line.strip()
                list_match = re.match(r"^[-*]\s+(.+)$", line) or re.match(r"^\d+[.)、]\s+(.+)$", line)
                if list_match:
                    pending_list.append(list_match.group(1))
                else:
                    flush_list()
                    html_parts.append(f"<p>{_render_inline(line, context)}</p>")
    flush_list()

    if remaining_figures:
        insert_at = min(3, len(html_parts))
        figure_html = [_render_figure(fig, context) for fig in remaining_figures]
        html_parts[insert_at:insert_at] = figure_html
    return "\n".join(part for part in html_parts if part)


def _render_inline(text: str, context: RenderContext | None = None) -> str:
    context = context or RenderContext({}, build_symbol_policy({}))
    text = normalize_text_symbols(_strip_raw_html(text), context.symbol_policy)
    formulas: list[str] = []

    def stash_formula(match: re.Match) -> str:
        formulas.append(match.group(1))
        return f"@@INLINE_FORMULA_{len(formulas) - 1}@@"

    text = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", stash_formula, text)
    escaped = html.escape(text)
    for index, formula in enumerate(formulas):
        if is_complex_formula(formula):
            img = render_formula_image(formula, display=False, textbook_style=context.textbook_style)
            if img:
                context.complex_formula_count += 1
                context.formula_image_count += 1
                replacement = f'<img class="formula-inline-img" src="{img.resolve().as_uri()}" alt="formula">'
            else:
                context.complex_formula_count += 1
                replacement = f'<span class="formula-inline formula-inline-wide">{html.escape(formula_to_readable_text(formula, context.symbol_policy))}</span>'
        else:
            context.simple_formula_count += 1
            replacement = f'<span class="formula-inline">{html.escape(formula_to_readable_text(formula, context.symbol_policy))}</span>'
        escaped = escaped.replace(f"@@INLINE_FORMULA_{index}@@", replacement)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _looks_like_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return len(lines) >= 2 and all(line.startswith("|") and line.endswith("|") for line in lines[:2]) and re.search(r"\|\s*:?-{3,}:?\s*\|", lines[1])


def _render_table(text: str, context: RenderContext) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return ""
    headers = _split_table_row(lines[0])
    rows = [_split_table_row(line) for line in lines[2:]]
    head_html = "".join(f"<th>{_render_inline(cell, context)}</th>" for cell in headers)
    body_rows = []
    for row in rows:
        cells = (row + [""] * len(headers))[: len(headers)]
        body_rows.append("<tr>" + "".join(f"<td>{_render_inline(cell, context)}</td>" for cell in cells) + "</tr>")
    return f'<table class="content-table"><thead><tr>{head_html}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _render_formula(formula: str, context: RenderContext, display: bool) -> str:
    formula, explicit_number = _extract_formula_number(formula)
    number = explicit_number or context.next_formula_number()
    formula_text = formula_to_readable_text(formula, context.symbol_policy)
    if is_complex_formula(formula) and context.formula_image_count < context.max_formula_images and not re.search(r"[\u4e00-\u9fff]", formula):
        img = render_formula_image(formula, display=display, textbook_style=context.textbook_style)
        if img:
            context.complex_formula_count += 1
            context.formula_image_count += 1
            return (
                '<figure class="formula-figure complex-formula">'
                f'<img src="{img.resolve().as_uri()}" alt="formula">'
                f'<figcaption>({html.escape(number)})</figcaption>'
                '</figure>'
            )
    if is_complex_formula(formula):
        context.complex_formula_count += 1
    else:
        context.simple_formula_count += 1
    return (
        '<div class="formula-card simple-formula">'
        f'<div class="formula-body">{html.escape(formula_text)}</div>'
        f'<div class="formula-number">({html.escape(number)})</div>'
        '</div>'
    )


def _render_image(path_text: str, alt: str) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT_DIR / path
    if not path.exists():
        return ""
    caption = html.escape(normalize_text_symbols(alt.replace("图：", "") or "教材参考图"))
    note = _asset_note(path_text, alt)
    return f'<figure class="lecture-figure textbook-asset"><img src="{path.resolve().as_uri()}" alt="{caption}"><figcaption>图：{caption}{note}</figcaption></figure>'


def _render_figure(fig: dict, context: RenderContext) -> str:
    caption = html.escape(fig.get("caption") or fig.get("title") or "教学插图")
    title = html.escape(fig.get("title") or "教学插图")
    number = context.next_figure_number()
    purpose = _figure_purpose(fig)
    return (
        f'<figure class="lecture-figure"><img src="{fig["uri"]}" alt="{title}">'
        f'<figcaption><strong>{html.escape(number)}：{title}</strong><br>'
        f'{caption}<br><span>用途：{html.escape(purpose)}</span></figcaption></figure>'
    )


def _figure_purpose(fig: dict) -> str:
    target = fig.get("target_section") or fig.get("title") or "相关知识点"
    if "高斯" in target:
        return "帮助判断高斯面的选取、电场方向与通量关系。"
    if "边界" in target:
        return "帮助区分切向分量连续与法向分量跳变。"
    if "电位" in target:
        return "帮助理解等位面、电场线和负梯度方向。"
    if "镜像" in target:
        return "帮助理解等效电荷只在求解区域内成立。"
    return "帮助建立本章知识结构和解题顺序。"


def _extract_formula_number(formula: str) -> tuple[str, str]:
    match = re.search(r"\\tag\s*\{?(\d+[-.]\d+)\}?", formula)
    if not match:
        match = re.search(r"\btag\s*\{?(\d+[-.]\d+)\}?", formula)
    number = match.group(1).replace(".", "-") if match else ""
    formula = re.sub(r"\\?tag\s*\{?\d+[-.]\d+\}?", "", formula)
    return formula.strip(), number


def _asset_note(path_text: str, alt: str) -> str:
    lower = f"{path_text} {alt}".lower()
    if "page_" in lower or "页级" in alt:
        return "｜教材页级参考，非精确子图裁剪。"
    return ""


def _heading_matches_figure(heading: str, figures: list[dict]) -> bool:
    heading_norm = re.sub(r"\s+", "", heading)
    for fig in figures:
        target = re.sub(r"\s+", "", fig.get("target_section", ""))
        title = re.sub(r"\s+", "", fig.get("title", ""))
        template = fig.get("template", "")
        if target and (target in heading_norm or heading_norm in target):
            return True
        if "gauss" in template and "高斯" in heading_norm:
            return True
        if "image" in template and "镜像" in heading_norm:
            return True
        if template == "boundary" and "边界" in heading_norm:
            return True
        if template == "potential_field" and ("电位" in heading_norm or "电场关系" in heading_norm):
            return True
    return False


def _normalize_figures(figures: list[dict], content: str) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()

    def add(title: str, caption: str, path_text: str, template: str = "", target_section: str = "") -> None:
        if "placeholder" in path_text.lower():
            return
        path = Path(path_text or "")
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists():
            return
        key = str(path.resolve())
        if key in seen:
            return
        seen.add(key)
        results.append(
            {
                "title": _clean_plain(title or "教学插图"),
                "caption": _clean_plain(caption),
                "uri": path.resolve().as_uri(),
                "template": template,
                "target_section": target_section,
            }
        )

    for fig in figures:
        add(
            str(fig.get("title", "")),
            str(fig.get("caption", "")),
            str(fig.get("path", "")),
            str(fig.get("template", "")),
            str(fig.get("target_section", "")),
        )
    for alt, path_text in re.findall(r"!\[(.*?)\]\((.*?)\)", content):
        add(alt.replace("图：", ""), "", path_text)
    return results[:8]


def _group_figures_by_section(figures: list[dict], section_map: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for fig in figures:
        key = _best_section_for_figure(fig, section_map)
        grouped.setdefault(key, []).append(fig)
    return grouped


def _best_section_for_figure(fig: dict, section_map: dict) -> str:
    target = re.sub(r"\s+", "", fig.get("target_section", "") + fig.get("title", "") + fig.get("template", ""))
    if "knowledge_map" in target or "知识地图" in target:
        return "map"
    if "gauss" in target or "boundary" in target or "potential" in target or "image" in target:
        return "core"
    return "core"


def _format_sources(sources: list[dict]) -> list[dict]:
    """Legacy flat source list — kept for backward compat."""
    rows, _ = _format_sources_grouped(sources)
    return rows


def _format_sources_grouped(sources: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    """Format sources into a flat list AND a grouped dict by resource type.

    Returns (flat_rows, groups) where groups is {group_label: [row, ...]}.
    """
    metadata = _load_metadata()
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    groups: dict[str, list[dict]] = {"教材来源": [], "往年题来源": [], "上传资料": []}

    for source in sources:
        filename = str(source.get("filename", "") or "未知文件")
        page = str(source.get("page", "?"))
        key = (filename, page)
        if key in seen:
            continue
        seen.add(key)

        # v2.2: filter cross-course pollution
        text_sample = str(source.get("text", ""))[:300]
        if _is_likely_cross_course(text_sample, source):
            continue

        meta = _metadata_for_source(source, metadata)
        raw_type = meta.get("resource_type") or source.get("resource_type") or "?"
        resource_type = _display_resource_type(filename, raw_type)
        summary = _source_summary(str(source.get("text", "")))

        # Skip bibliographic/database noise in display.
        if "SS号" in summary or "General Information" in summary:
            continue

        row = {
            "ref": _source_ref_label(resource_type, len(rows) + 1, groups),
            "filename": _clean_plain(filename),
            "page": page,
            "resource_type": resource_type,
            "summary": summary,
        }
        rows.append(row)

        # Group
        if resource_type in ("教材", "textbook"):
            groups["教材来源"].append(row)
        elif resource_type in ("往年题", "past_exam"):
            groups["往年题来源"].append(row)
        else:
            groups["上传资料"].append(row)

        if len(rows) >= 15:
            break

    # Clean empty groups
    groups = {k: v for k, v in groups.items() if v}
    return rows, groups


def _source_ref_label(resource_type: str, index: int, groups: dict) -> str:
    """Generate [教材N], [真题N], or [资料N] labels."""
    if resource_type in ("教材", "textbook"):
        n = len(groups.get("教材来源", [])) + 1
        return f"[教材{n}]"
    if resource_type in ("往年题", "past_exam"):
        n = len(groups.get("往年题来源", [])) + 1
        return f"[真题{n}]"
    n = len(groups.get("上传资料", [])) + 1
    return f"[资料{n}]"


def _source_badges_from_groups(groups: dict[str, list[dict]]) -> list[str]:
    """Create badge strings from source groups for section headers."""
    badges: list[str] = []
    for label, rows in groups.items():
        if rows:
            refs = "、".join(r["ref"] for r in rows[:3])
            badges.append(f"{label}：{refs}")
    return badges[:4]


def _is_likely_cross_course(text: str, source: dict) -> bool:
    """Return True if the source text appears to belong to a different subject."""
    resource_type = source.get("resource_type", "")
    filename = (source.get("filename", "") or "").lower()

    # Detect subject from text
    subjects: dict[str, list[str]] = {
        "电磁场": ["电场", "磁场", "电磁波", "静电场", "高斯定理", "麦克斯韦"],
        "概率论": ["概率", "随机变量", "分布函数", "期望", "方差", "大数定律"],
        "高等数学": ["极限", "导数", "微分", "积分", "级数", "泰勒"],
        "电路": ["电路", "电压", "电流", "电阻", "基尔霍夫", "戴维宁"],
        "信号": ["信号", "系统", "傅里叶", "拉普拉斯", "卷积", "频域"],
    }

    text_subjects: set[str] = set()
    for subj, keywords in subjects.items():
        if any(kw in text for kw in keywords):
            text_subjects.add(subj)

    file_subjects: set[str] = set()
    for subj, keywords in subjects.items():
        if any(kw in filename for kw in keywords):
            file_subjects.add(subj)

    # If text and filename suggest different subjects, flag as cross-course
    if text_subjects and file_subjects and not (text_subjects & file_subjects):
        return True
    return False


def _load_metadata() -> list[dict]:
    try:
        return __import__("json").loads(METADATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _metadata_for_source(source: dict, metadata: list[dict]) -> dict:
    resource_id = source.get("resource_id")
    if resource_id:
        found = next((item for item in metadata if item.get("resource_id") == resource_id), None)
        if found:
            return found
    filename = source.get("filename")
    if filename:
        found = next((item for item in metadata if item.get("filename") == filename), None)
        if found:
            return found
    return {}


def _display_resource_type(filename: str, resource_type: str) -> str:
    if re.search(r"期末|试卷|真题|往年题|考试|exam|paper", filename, flags=re.I):
        return "往年题"
    return _clean_plain(resource_type)


def _source_summary(text: str) -> str:
    text = normalize_text_symbols(_strip_raw_html(text))
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or _looks_like_ocr_noise(cleaned):
        return "来源文本质量较低，已略去摘要。"
    readable = sum(1 for char in cleaned if char.isalpha() or "\u4e00" <= char <= "\u9fff")
    digits = sum(1 for char in cleaned if char.isdigit())
    symbols = sum(1 for char in cleaned if not char.isalnum() and not char.isspace() and not ("\u4e00" <= char <= "\u9fff"))
    length = len(cleaned)
    if length > 20 and (readable / length < 0.25 or digits / length > 0.55 or symbols / length > 0.45):
        return "来源文本质量较低，已略去摘要。"
    cleaned = re.sub(r"(?:\d[\d\s.,，。:：;-]{8,})", "", cleaned).strip()
    if len(cleaned) < 8:
        return "来源文本质量较低，已略去摘要。"
    return cleaned[:120] + ("..." if len(cleaned) > 120 else "")


def _looks_like_ocr_noise(text: str) -> bool:
    if re.search(r"[\ue000-\uf8ff]", text):
        return True
    if any(mark in text for mark in ["�", "□", "▯"]):
        return True
    if text.count("?") >= 3 or text.count("？") >= 3:
        return True
    if re.search(r"(?:[A-Za-z]\s+){6,}", text):
        return True
    return False


def _normalize_display_math(content: str) -> str:
    return re.sub(r"\\\[\s*(.*?)\s*\\\]", r"\n$$\n\1\n$$\n", content, flags=re.S)


def _strip_raw_html(text: str) -> str:
    text = re.sub(r"</?font[^>]*>", "", str(text or ""), flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def _clean_plain(text: object) -> str:
    return normalize_text_symbols(_strip_raw_html(str(text or ""))).strip()


def _extract_goal_items(section: Section | None) -> list[str]:
    if not isinstance(section, Section):
        return ["围绕课程资料构建结构化复习讲义。"]
    items: list[str] = []
    for block in section.blocks:
        if block.kind != "paragraph":
            continue
        for line in block.text.splitlines():
            cleaned = re.sub(r"^[•·\-*\d.、)\s]+", "", line).strip()
            if not cleaned or cleaned in {"•", "·"} or cleaned.endswith("：") or cleaned.endswith(":"):
                continue
            if cleaned:
                cleaned = re.sub(
                    r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)",
                    lambda match: formula_to_readable_text(match.group(1)),
                    cleaned,
                )
                cleaned = cleaned.replace("**", "")
                items.append(_clean_plain(re.sub(r"\$+", "", cleaned)))
            if len(items) >= 5:
                return items
    return items or ["围绕课程资料构建结构化复习讲义。"]


def _resolve_task_label(task_type: str) -> str:
    """Convert internal task_type key to human-readable Chinese label."""
    from core.prompt_templates import TASK_LABELS
    return TASK_LABELS.get(task_type, task_type)


def _guess_task_type(title: str) -> str:
    parts = [part for part in re.split(r"[_\-\s]+", title) if part]
    return parts[-1] if parts else "单章精学"
