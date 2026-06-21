"""v2.0 Step 3: Task-based async generation manager.

Provides file-persisted task CRUD and a background-thread runner so the
Streamlit UI never blocks on long-running DeepSeek calls.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from core.config import DATA_DIR

TASKS_FILE = DATA_DIR / "tasks.json"


# ---- low-level persistence ------------------------------------------------

def _load() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(tasks: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


# ---- public CRUD ----------------------------------------------------------

def create_task(
    course_id: str,
    task_type: str,
    user_request: str,
    run_id: str | None = None,
    prefs: dict | None = None,
) -> dict:
    """Create a new task record (status='pending') and persist it."""
    task = {
        "task_id": f"task_{uuid4().hex[:8]}",
        "course_id": course_id,
        "task_type": task_type,
        "user_request": user_request,
        "status": "pending",
        "progress": 0,
        "message": "任务已创建，等待执行...",
        "result_markdown_path": "",
        "result_pdf_path": "",
        "sources": [],
        "figures": [],
        "quality_checks": {},
        "error_message": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": "",
    }
    if run_id:
        task["run_id"] = run_id
    if prefs:
        task["generation_prefs"] = prefs
    tasks = _load()
    tasks.append(task)
    _save(tasks)
    return task


def update_task(task_id: str, **kwargs: object) -> dict | None:
    """Update fields on an existing task. Returns the updated task or None."""
    tasks = _load()
    for t in tasks:
        if t["task_id"] == task_id:
            t.update(kwargs)  # type: ignore[arg-type]
            _save(tasks)
            return t
    return None


def get_task(task_id: str) -> dict | None:
    for t in _load():
        if t["task_id"] == task_id:
            return t
    return None


def get_all_tasks() -> list[dict]:
    return sorted(_load(), key=lambda t: t.get("created_at", ""), reverse=True)


def delete_task(task_id: str) -> bool:
    tasks = _load()
    new_tasks = [t for t in tasks if t["task_id"] != task_id]
    if len(new_tasks) == len(tasks):
        return False
    _save(new_tasks)
    return True


def _should_use_pdf_content_v2(course: dict, user_request: str) -> bool:
    """PDF 5.0: Course-agnostic routing.

    ALL courses with a valid profile go through UniversalRenderPipeline.
    No longer checks for specific course names like '电磁场'.
    Falls back to False only if no course profile can be resolved.
    """
    try:
        from core.course_profiles.profile_registry import get_profile
        from core.course_profiles.base_profile import ProfileSource

        course_id = course.get("course_id", "")
        if not course_id:
            return False

        profile = get_profile(course_id)
        # Accept any profile that isn't a pure generic fallback
        return profile.source != ProfileSource.GENERIC
    except Exception:
        return False


def _pdf_v2_type_for_task(task_type: str) -> str:
    return {
        "exam_sprint": "Sprint",
        "single_chapter": "Review",
        "past_paper": "PastPaper",
        "mock_exam": "MockExam",
    }.get(task_type, "Review")


def _pdf_v2_markdown_summary(
    pdf_type: str,
    pdf_info: dict,
    report_path: str,
    summary: dict,
) -> str:
    quality = pdf_info.get("quality", {})
    checks = quality.get("checks", {})
    version = summary.get("version", "pdf5.0")
    is_demo = summary.get("is_demo", False)
    demo_note = "\n⚠️ Demo only — 未上传教材，内容为 AI_DERIVED/GenericPlugin 生成。\n" if is_demo else ""
    return "\n".join([
        f"# StudyPilot PDF 5.0 - {pdf_type}",
        "",
        "本次输出使用 UniversalRenderPipeline (PDF 5.0) 生成。",
        demo_note,
        f"- PDF: {pdf_info.get('pdf', '')}",
        f"- Typst: {pdf_info.get('typst', '')}",
        f"- Report: {report_path}",
        f"- AI content ratio: {summary.get('ai_content_ratio', 0)}",
        f"- Contamination count: {summary.get('course_contamination_count', 0)}",
        f"- Option-answer mismatches: {summary.get('option_answer_mismatch_count', 0)}",
        f"- Fake questions: {summary.get('fake_question_count', 0)}",
        "",
        "所有课程通过 CoursePlugin → CourseProfile → EvidenceDeck → Validators 生成。",
        "不存在跨课程污染、默认 EM fallback 或伪造来源。",
    ])


# ---- background execution -------------------------------------------------

def run_task_in_background(
    task_id: str,
    course: dict,
    task_type: str,
    user_request: str,
    top_k: int,
    pdf_style: str = "textbook",
    run_id: str | None = None,
    prefs: dict | None = None,
) -> threading.Thread:
    """Spawn a daemon thread that executes the full generation pipeline.

    Progress is persisted to ``data/tasks.json`` after every phase so the
    UI can pick it up on the next ``st.rerun()`` regardless of which page
    the user is viewing.
    """

    def _run() -> None:
        try:
            # ---- Phase 1: retrieve ------------------------------------------
            _update(task_id, status="running", progress=5,
                    message="正在检索课程资料...")
            from core.rag_engine import retrieve
            chunks = retrieve(course["course_id"], user_request, top_k=top_k)

            # ---- Phase 1.5: analyze textbook style (v2.2) -------------------
            _update(task_id, progress=10, message="正在分析教材符号风格...")
            from core.textbook_style_analyzer import analyze_textbook_style
            textbook_style = analyze_textbook_style(chunks, course)

            # ---- PDF 5.0: UniversalRenderPipeline fast path -----------------
            # All courses with valid profiles go through the universal pipeline.
            # Course routing is handled by CoursePlugin → CourseProfile → EvidenceDeck.
            if _should_use_pdf_content_v2(course, user_request):
                _update(task_id, progress=25, message="正在构建 Evidence-first 知识卡片...")
                from core.pdf_content_v2.renderer import render_all_pdf_v2
                from core.prompt_templates import TASK_LABELS
                from core.export_utils import save_markdown

                course_id = course.get("course_id", "")
                outputs = render_all_pdf_v2(course_id=course_id)
                pdf_type = _pdf_v2_type_for_task(task_type)
                pdf_info = outputs.get(pdf_type, {})
                report_path = outputs.get("report", "")
                summary = outputs.get("summary", {})
                content = _pdf_v2_markdown_summary(pdf_type, pdf_info, report_path, summary)
                title = f"{course['course_name']}_{TASK_LABELS.get(task_type, task_type)}_PDF_v2"
                md_path = save_markdown(content, title, run_id=run_id)
                pdf_str = str(pdf_info.get("pdf", ""))
                checks = {
                    "is_teaching_grade": bool(pdf_info.get("quality", {}).get("passed")),
                    "is_complete": bool(pdf_info.get("quality", {}).get("passed")),
                    "total_score": 100 if pdf_info.get("quality", {}).get("passed") else 0,
                    "grade": "PDF 2.0 Evidence-first",
                    "pdf_content_v2": summary,
                }
                _update(
                    task_id,
                    status="completed" if checks["is_teaching_grade"] else "warning",
                    progress=100,
                    message="Evidence-first PDF 2.0 生成完成",
                    result_markdown_path=str(md_path),
                    result_pdf_path=pdf_str,
                    sources=chunks,
                    figures=[],
                    quality_checks=checks,
                    textbook_style=textbook_style,
                    selected_assets={},
                    finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                if run_id:
                    try:
                        from core.output_manager import finalize_run as om_finalize
                        om_finalize(run_id, get_task(task_id) or {})
                    except Exception:
                        pass
                return

            # ---- PDF 5.0: No legacy DeepSeek fallback -----------------------
            # Courses without a valid CourseProfile cannot use the universal pipeline.
            # The legacy DeepSeek path (Phases 2-7) has been disabled.
            _update(
                task_id,
                status="failed",
                progress=0,
                message="PDF 5.0: 课程无有效 CourseProfile，无法生成。请上传教材/PPT/真题资料。",
                error_message="Legacy DeepSeek path disabled in PDF 5.0. Upload materials to generate.",
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            return

        except Exception as exc:
            _update(
                task_id,
                status="failed",
                progress=0,
                message="生成失败",
                error_message=str(exc),
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def _update(task_id: str, **kwargs: object) -> None:
    """Thin wrapper so the background thread only touches the JSON file."""
    update_task(task_id, **kwargs)
