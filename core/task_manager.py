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

            # ---- Phase 2: build prompt --------------------------------------
            _update(task_id, progress=15, message="正在构造 Prompt...")
            from core.learning_planner import get_profile
            from core.prompt_templates import build_generation_prompt
            profile = get_profile(course["course_id"])
            prompt = build_generation_prompt(task_type, user_request, course, profile, chunks)

            # ---- Phase 3: call DeepSeek -------------------------------------
            _update(task_id, progress=25,
                    message="正在调用 DeepSeek 生成内容（可能需要 30-60 秒）...")
            from core.deepseek_client import call_deepseek
            content = call_deepseek(prompt)
            from core.symbol_mapper import normalize_generated_content
            content = normalize_generated_content(content, textbook_style)

            # ---- Phase 4: load textbook assets (v4.0) -----------------------
            _update(task_id, progress=55, message="正在加载教材资产库...")
            from core.textbook_asset_extractor import get_course_assets, find_assets_for_keywords
            course_assets = get_course_assets(course["course_id"])

            # ---- Phase 4.5: generate figures (v4.0: prefer textbook assets) ---
            _update(task_id, progress=60, message="正在规划教学插图...")
            from core.prompt_templates import build_figure_plan_prompt
            from core.figure_planner import plan_figures
            figure_prompt = build_figure_plan_prompt(content)
            figures = plan_figures(content, figure_prompt)

            _update(task_id, progress=70, message="正在生成教学插图...")
            from core.image_generator import safe_generate_figure
            generated_figures: list[dict] = []
            for idx, fig in enumerate(figures, start=1):
                filename = f"{course['course_id']}_{task_type}_{task_id}_{idx}.png"
                output_path = f"assets/generated/{filename}"
                gen = safe_generate_figure(fig, output_path)
                generated_figures.append({
                    "title": fig.get("title", "教学示意图"),
                    "caption": fig.get("caption", ""),
                    "path": output_path,
                    "generated": gen is not None,
                    "template": fig.get("template", ""),
                    "target_section": fig.get("target_section", ""),
                })

            # ---- Phase 5: select & embed textbook assets (v4.1) --------------
            from core.content_utils import clean_latex
            content = clean_latex(content)

            if course_assets:
                from core.asset_selector import select_assets_for_lecture, embed_selected_assets
                selection = select_assets_for_lecture(
                    course_assets, content, chunks,
                    max_figures=4, max_formulas=4, max_examples=2,
                )
                content, asset_stats = embed_selected_assets(content, selection)

                # Build diagnostics for task record
                selected_assets_info = {
                    "candidates": asset_stats.get("candidates", 0),
                    "high": asset_stats.get("high_count", 0),
                    "medium": asset_stats.get("medium_count", 0),
                    "low": asset_stats.get("low_count", 0),
                    "inserted_body": asset_stats.get("inserted_body", 0),
                    "inserted_appendix": asset_stats.get("inserted_appendix", 0),
                    "skipped_reasons": asset_stats.get("skipped_reasons", []),
                    "details": [
                        {"title": a.get("title_guess", ""), "page": a.get("page", 0),
                         "type": a.get("asset_type", ""), "confidence": a.get("confidence", ""),
                         "score": a.get("match_score", 0), "kp": a.get("matched_kp", ""),
                         "why": a.get("why", "")}
                        for a in (selection.get("high", []) + selection.get("medium", []))
                    ],
                }
            else:
                selected_assets_info = {}

            # ---- Phase 6: export --------------------------------------------
            _update(task_id, progress=85, message="正在导出 Markdown...")
            from core.prompt_templates import TASK_LABELS
            from core.export_utils import markdown_to_pdf, save_markdown
            title = f"{course['course_name']}_{TASK_LABELS.get(task_type, task_type)}"
            md_path = save_markdown(content, title, run_id=run_id)

            _update(task_id, progress=92, message="正在导出 PDF...")
            pdf_str = ""
            try:
                from core.pdf_renderer import TASK_TO_TEMPLATE
                template_type = TASK_TO_TEMPLATE.get(task_type, "lecture_deep")
                pdf_str = str(
                    markdown_to_pdf(
                        content,
                        title,
                        course=course,
                        task_type=TASK_LABELS.get(task_type, task_type),
                        sources=chunks,
                        figures=generated_figures,
                        textbook_style=textbook_style,
                        template_type=template_type,
                        pdf_style=pdf_style,
                        run_id=run_id,
                    )
                )
            except Exception:
                pass

            # ---- Phase 7: quality check (v2.2: textbook-aware) --------------
            from core.quality_checker import run_quality_checks
            checks = run_quality_checks(
                content, chunks, generated_figures, pdf_str,
                textbook_style=textbook_style,
                template_type=template_type,
            )
            is_teaching_grade = checks.get("is_teaching_grade", False)
            total = checks.get("total_score", 0)

            if is_teaching_grade:
                final_status = "completed"
                final_message = f"教辅级讲义生成完成（质量评分 {total}/100）"
            elif checks.get("is_complete"):
                final_status = "warning"
                final_message = f"讲义已生成但未达教辅级（评分 {total}/100），建议补充教材资料后重新生成"
            else:
                final_status = "warning"
                final_message = f"生成完成但质量偏低（评分 {total}/100）"

            # ---- complete ---------------------------------------------------
            _update(
                task_id,
                status=final_status,
                progress=100,
                message=final_message,
                result_markdown_path=str(md_path),
                result_pdf_path=pdf_str,
                sources=chunks,
                figures=generated_figures,
                quality_checks=checks,
                textbook_style=textbook_style,
                selected_assets=selected_assets_info,
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            # v1.2: finalize output_manager run
            if run_id:
                try:
                    from core.output_manager import finalize_run as om_finalize
                    om_finalize(run_id, get_task(task_id) or {})
                except Exception:
                    pass

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
