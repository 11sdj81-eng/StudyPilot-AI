"""TaskManagerV2 — proper task lifecycle with cancel, recovery, and atomic output.

States: queued → running → success / failed / cancelled
Features: cancel support, failure recovery, temp-first PDF writes, progress persistence.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

TASKS_DIR = Path("data/tasks_v2")


class TaskManagerV2:
    """Task manager with proper lifecycle states and failure recovery."""

    VALID_STATUSES = {"queued", "running", "success", "failed", "cancelled"}

    def __init__(self, core=None):
        self.core = core
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        self._recover_on_startup()

    # ── CRUD ────────────────────────────────────────────────────────────

    def create(self, course_id: str, task_type: str, user_request: str = "",
               workspace_id: str = "", prefs: dict | None = None) -> dict:
        """Create a new task in queued state."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        task = {
            "task_id": task_id,
            "course_id": course_id,
            "workspace_id": workspace_id,
            "task_type": task_type,
            "user_request": user_request,
            "status": "queued",
            "progress": 0,
            "stage": "",
            "message": "等待执行...",
            "logs": [],
            "error": None,
            "result_pdf_path": "",
            "result_markdown_path": "",
            "result_report_path": "",
            "quality_checks": {},
            "created_at": now,
            "started_at": None,
            "finished_at": None,
            "generation_prefs": prefs or {},
        }
        self._save(task)
        return task

    def get(self, task_id: str) -> dict | None:
        path = TASKS_DIR / f"{task_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def list_all(self) -> list[dict]:
        tasks = []
        if TASKS_DIR.exists():
            for f in sorted(TASKS_DIR.glob("*.json"), reverse=True):
                try:
                    tasks.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks

    def list_by_status(self, status: str) -> list[dict]:
        return [t for t in self.list_all() if t.get("status") == status]

    def list_by_course(self, course_id: str) -> list[dict]:
        return [t for t in self.list_all() if t.get("course_id") == course_id]

    def get_stats(self) -> dict:
        all_tasks = self.list_all()
        stats = {"total": len(all_tasks), "running": 0, "success": 0,
                 "failed": 0, "cancelled": 0, "queued": 0}
        for t in all_tasks:
            status = t.get("status", "queued")
            stats[status] = stats.get(status, 0) + 1
        return stats

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start(self, task_id: str) -> dict | None:
        """Transition task from queued → running."""
        task = self.get(task_id)
        if task and task["status"] == "queued":
            task["status"] = "running"
            task["started_at"] = datetime.now().isoformat()
            task["progress"] = 5
            task["message"] = "正在启动..."
            self._save(task)
            self._log(task_id, "Task started")
        return task

    def update_progress(self, task_id: str, progress: int, message: str = "",
                        stage: str = "") -> dict | None:
        """Update task progress during execution."""
        task = self.get(task_id)
        if task and task["status"] == "running":
            task["progress"] = min(100, max(0, progress))
            if message:
                task["message"] = message
            if stage:
                task["stage"] = stage
            self._save(task)
        return task

    def complete(self, task_id: str, result: dict | None = None) -> dict | None:
        """Mark task as success with results."""
        task = self.get(task_id)
        if task and task["status"] == "running":
            task["status"] = "success"
            task["progress"] = 100
            task["finished_at"] = datetime.now().isoformat()
            task["message"] = "完成"
            if result:
                task["result_pdf_path"] = result.get("pdf", "")
                task["result_markdown_path"] = result.get("markdown", "")
                task["result_report_path"] = result.get("report", "")
                task["quality_checks"] = result.get("quality", {})
            self._save(task)
            self._log(task_id, "Task completed successfully")
        return task

    def fail(self, task_id: str, error: str) -> dict | None:
        """Mark task as failed with error message."""
        task = self.get(task_id)
        if task:
            task["status"] = "failed"
            task["error"] = error
            task["finished_at"] = datetime.now().isoformat()
            task["message"] = f"失败: {error[:100]}"
            self._save(task)
            self._log(task_id, f"Task failed: {error[:200]}")

            # Clean up temp files
            self._cleanup_temp(task_id)
        return task

    def cancel(self, task_id: str) -> dict | None:
        """Cancel a queued or running task."""
        task = self.get(task_id)
        if task and task["status"] in ("queued", "running"):
            task["status"] = "cancelled"
            task["finished_at"] = datetime.now().isoformat()
            task["message"] = "已取消"
            self._save(task)
            self._log(task_id, "Task cancelled")

            # Set cancel flag for running thread to detect
            cancel_flag = TASKS_DIR / f"{task_id}.cancel"
            cancel_flag.write_text("1")

            # Clean up temp files
            self._cleanup_temp(task_id)
        return task

    def is_cancelled(self, task_id: str) -> bool:
        """Check if a task has been cancelled (for running threads)."""
        return (TASKS_DIR / f"{task_id}.cancel").exists()

    # ── Execution ───────────────────────────────────────────────────────

    def run_in_background(self, task_id: str, course: dict, task_type: str,
                          user_request: str, prefs: dict | None = None) -> threading.Thread:
        """Spawn a daemon thread for task execution using the universal pipeline."""
        task = self.start(task_id)
        if not task:
            raise RuntimeError(f"Cannot start task {task_id}")

        def _execute():
            try:
                self.update_progress(task_id, 10, "正在构建证据卡片...", "evidence")

                # Use the existing PDF 5.0 universal pipeline
                from core.pdf_content_v2.renderer import render_all_pdf_v2
                course_id = course.get("course_id", "")

                self.update_progress(task_id, 25, "正在生成 PDF...", "rendering")
                outputs = render_all_pdf_v2(course_id=course_id)

                # Check cancel
                if self.is_cancelled(task_id):
                    self.cancel(task_id)
                    return

                self.update_progress(task_id, 80, "正在验证质量...", "quality")
                summary = outputs.get("summary", {})

                self.update_progress(task_id, 95, "正在保存输出...", "saving")

                # Record output in workspace
                if task.get("workspace_id") and self.core:
                    report_path = outputs.get("report", "")
                    self.core.workspace.add_output(task["workspace_id"],
                                                   str(report_path))

                self.complete(task_id, {
                    "pdf": outputs.get("MockExam", {}).get("pdf", ""),
                    "markdown": "",
                    "report": outputs.get("report", ""),
                    "quality": summary,
                })

            except Exception as e:
                import traceback
                self._log(task_id, traceback.format_exc()[-500:])
                self.fail(task_id, str(e))

            finally:
                # Clean up cancel flag
                cancel_flag = TASKS_DIR / f"{task_id}.cancel"
                if cancel_flag.exists():
                    cancel_flag.unlink()

        thread = threading.Thread(target=_execute, daemon=True)
        thread.start()
        return thread

    # ── Recovery ────────────────────────────────────────────────────────

    def _recover_on_startup(self) -> int:
        """On startup, mark any 'running' tasks as failed (process restarted)."""
        count = 0
        for task in self.list_by_status("running"):
            task["status"] = "failed"
            task["error"] = "Process restarted — task was interrupted"
            task["finished_at"] = datetime.now().isoformat()
            task["message"] = "失败: 进程重启导致任务中断"
            self._save(task)
            self._cleanup_temp(task["task_id"])
            count += 1
        return count

    def _cleanup_temp(self, task_id: str) -> None:
        """Remove temporary files for a task."""
        import glob
        patterns = [
            str(TASKS_DIR / f"{task_id}*.tmp"),
            str(Path("data/outputs") / f"*{task_id}*.tmp"),
        ]
        for pattern in patterns:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except Exception:
                    pass

    # ── Internal ─────────────────────────────────────────────────────────

    def _save(self, task: dict) -> None:
        path = TASKS_DIR / f"{task['task_id']}.json"
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    def _log(self, task_id: str, message: str) -> None:
        task = self.get(task_id)
        if task:
            logs = task.get("logs", [])
            logs.append(f"[{datetime.now().isoformat()}] {message}")
            task["logs"] = logs[-50:]  # Keep last 50 entries
            self._save(task)
