import re
from datetime import datetime
from pathlib import Path

from core.config import OUTPUT_DIR, RUNS_DIR


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", text).strip("_")
    return slug[:60] or "studypilot_output"


def save_markdown(content: str, title: str, run_id: str | None = None) -> Path:
    if run_id:
        dest = RUNS_DIR / run_id
        dest.mkdir(parents=True, exist_ok=True)
    else:
        dest = OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = dest / f"{timestamp}_{safe_slug(title)}.md"
    path.write_text(content, encoding="utf-8")
    return path


def markdown_to_pdf(
    content: str,
    title: str,
    course: dict | None = None,
    task_type: str = "",
    sources: list[dict] | None = None,
    figures: list[dict] | None = None,
    run_id: str | None = None,
    **kwargs: object,
) -> Path:
    """Render a professional lecture PDF, preferring the v6 Chromium engine."""
    if run_id:
        dest = RUNS_DIR / run_id
        dest.mkdir(parents=True, exist_ok=True)
    else:
        dest = OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = dest / f"{timestamp}_{safe_slug(title)}.pdf"
    try:
        from core.pdf_engine_v6 import render_pdf_v6

        return render_pdf_v6(
            content=content,
            output_path=path,
            title=title,
            course=course,
            task_type=task_type,
            sources=sources,
            figures=figures,
            textbook_style=kwargs.get("textbook_style"),
        )
    except Exception:
        from core.pdf_renderer import render_professional_pdf

        return render_professional_pdf(
            content=content,
            output_path=path,
            title=title,
            course=course,
            task_type=task_type,
            sources=sources,
            figures=figures,
            textbook_style=kwargs.get("textbook_style"),
            template_type=str(kwargs.get("template_type", "")),
            pdf_style=str(kwargs.get("pdf_style", "textbook")),
        )


def study_document_to_pdf(document: object, output_path: str | Path) -> Path:
    """Render a v2.0 StudyDocument through the object-first PDF pipeline."""
    from core.study_object_renderer import render_study_document_pdf

    return render_study_document_pdf(document, output_path)


def list_outputs() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = [path for path in OUTPUT_DIR.glob("*") if path.is_file() and not path.name.startswith(".")]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
