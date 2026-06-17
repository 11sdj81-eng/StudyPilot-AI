"""StudyPilot AI — Output file manager.

Run-based output directory management, replacing the flat-file dump in
``data/outputs/``.  Each generation creates a ``run_id`` directory under
``data/outputs/runs/`` with a ``manifest.json`` index.

Existing flat files are left untouched for backward compatibility.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from core.config import OUTPUT_DIR, OUTPUT_INDEX_FILE, RUNS_DIR


# ── helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def _generate_run_id() -> str:
    short = uuid4().hex[:8]
    return f"run_{_timestamp()}_{short}"


def _load_index() -> list[dict]:
    if not OUTPUT_INDEX_FILE.exists():
        return []
    try:
        return json.loads(OUTPUT_INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(data: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_INDEX_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _index_upsert(entry: dict) -> None:
    data = _load_index()
    for i, item in enumerate(data):
        if item.get("run_id") == entry["run_id"]:
            data[i] = entry
            break
    else:
        data.append(entry)
    _save_index(data)


def _index_remove(run_id: str) -> None:
    data = [item for item in _load_index() if item.get("run_id") != run_id]
    _save_index(data)


# ── public API ──────────────────────────────────────────────────────────────

def create_run(
    course_id: str,
    task_type: str = "",
    user_request: str = "",
    course_name: str = "",
    chapter_name: str = "",
) -> str:
    """Initialise a new run directory and return its ``run_id``.

    Creates ``data/outputs/runs/<run_id>/`` with an empty manifest.
    """
    run_id = _generate_run_id()
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "run_id": run_id,
        "course_id": course_id,
        "course_name": course_name,
        "chapter_name": chapter_name,
        "task_type": task_type,
        "user_request": user_request,
        "status": "running",
        "quality_score": 0,
        "quality_grade": "",
        "files": [],
        "created_at": _now(),
        "finished_at": "",
        "is_final": False,
    }
    _write_manifest(run_dir, manifest)
    _index_upsert(_index_entry(manifest))
    return run_id


def save_output(
    run_id: str,
    content: str,
    title: str,
    fmt: str = "md",
) -> Path | None:
    """Save generated content into the run directory.

    Args:
        run_id: The run identifier from ``create_run()``.
        content: Text/binary content to write.
        title: Human-readable title (slugified for filename).
        fmt: File extension — ``"md"``, ``"pdf"``, or ``"json"``.

    Returns:
        Path to the saved file, or ``None`` if the run doesn't exist.
    """
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        return None

    from core.export_utils import safe_slug

    slug = safe_slug(title)
    filename = f"{slug}.{fmt}"
    path = run_dir / filename
    path.write_text(content, encoding="utf-8")

    # Update manifest
    manifest = _read_manifest(run_dir)
    if manifest:
        # Remove old entry for same file
        manifest["files"] = [
            f for f in manifest.get("files", []) if f["path"] != filename
        ]
        manifest["files"].append(
            {
                "path": filename,
                "size_bytes": path.stat().st_size,
                "format": fmt,
            }
        )
        _write_manifest(run_dir, manifest)

    return path


def save_output_bytes(
    run_id: str,
    data: bytes,
    title: str,
    fmt: str = "pdf",
) -> Path | None:
    """Save binary output (e.g. PDF bytes) into the run directory."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        return None

    from core.export_utils import safe_slug

    slug = safe_slug(title)
    filename = f"{slug}.{fmt}"
    path = run_dir / filename
    path.write_bytes(data)

    manifest = _read_manifest(run_dir)
    if manifest:
        manifest["files"] = [
            f for f in manifest.get("files", []) if f["path"] != filename
        ]
        manifest["files"].append(
            {
                "path": filename,
                "size_bytes": path.stat().st_size,
                "format": fmt,
            }
        )
        _write_manifest(run_dir, manifest)

    return path


def finalize_run(run_id: str, task: dict) -> None:
    """Update the run manifest after task completion.

    Args:
        run_id: The run identifier.
        task: The completed task dict from ``task_manager``.
    """
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        return

    manifest = _read_manifest(run_dir)
    if not manifest:
        return

    qc = task.get("quality_checks", {})
    manifest.update(
        {
            "status": task.get("status", "completed"),
            "quality_score": qc.get("total_score", 0),
            "quality_grade": qc.get("grade", ""),
            "task_id": task.get("task_id", ""),
            "finished_at": _now(),
        }
    )
    _write_manifest(run_dir, manifest)
    _index_upsert(_index_entry(manifest))


def get_run(run_id: str) -> dict | None:
    """Read a run's manifest. Returns ``None`` if not found."""
    run_dir = RUNS_DIR / run_id
    manifest = _read_manifest(run_dir)
    return manifest


def list_runs(course_id: str | None = None, limit: int = 20) -> list[dict]:
    """List recent runs, newest first.  Optionally filter by ``course_id``."""
    index = _load_index()
    if course_id:
        index = [r for r in index if r.get("course_id") == course_id]
    # Supplement from disk: any run dir not in index
    seen = {r["run_id"] for r in index}
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir(), reverse=True):
            if d.is_dir() and d.name not in seen:
                m = _read_manifest(d)
                if m:
                    index.append(_index_entry(m))
                    seen.add(d.name)
    index.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return index[:limit]


def delete_run(run_id: str) -> tuple[int, int]:
    """Delete a run directory and its index entry.

    Returns:
        ``(files_removed, bytes_freed)``.
    """
    run_dir = RUNS_DIR / run_id
    files_removed = 0
    bytes_freed = 0

    if run_dir.exists():
        for f in run_dir.rglob("*"):
            if f.is_file():
                bytes_freed += f.stat().st_size
                files_removed += 1
        shutil.rmtree(run_dir)

    _index_remove(run_id)
    return files_removed, bytes_freed


def mark_final(run_id: str) -> None:
    """Toggle the ``is_final`` flag on a run."""
    manifest = get_run(run_id)
    if not manifest:
        return
    run_dir = RUNS_DIR / run_id
    manifest["is_final"] = not manifest.get("is_final", False)
    _write_manifest(run_dir, manifest)
    _index_upsert(_index_entry(manifest))


# ── cleanup ─────────────────────────────────────────────────────────────────

def cleanup_old_runs(keep_last: int = 5) -> dict:
    """Remove all but the most recent *N* runs.

    Runs marked ``is_final`` are never removed.
    """
    runs = list_runs(limit=1000)
    non_final = [r for r in runs if not r.get("is_final")]
    to_delete = non_final[keep_last:]

    total_files = 0
    total_bytes = 0
    for run in to_delete:
        f, b = delete_run(run["run_id"])
        total_files += f
        total_bytes += b

    return {
        "runs_removed": len(to_delete),
        "files_removed": total_files,
        "bytes_freed": total_bytes,
        "kept": min(keep_last, len(runs)),
    }


def cleanup_non_final() -> dict:
    """Remove all runs that are NOT marked ``is_final``."""
    runs = list_runs(limit=1000)
    to_delete = [r for r in runs if not r.get("is_final")]

    total_files = 0
    total_bytes = 0
    for run in to_delete:
        f, b = delete_run(run["run_id"])
        total_files += f
        total_bytes += b

    return {
        "runs_removed": len(to_delete),
        "files_removed": total_files,
        "bytes_freed": total_bytes,
    }


def cleanup_all() -> dict:
    """Remove ALL runs and the index.  Use with caution."""
    runs = list_runs(limit=1000)
    total_files = 0
    total_bytes = 0
    for run in runs:
        f, b = delete_run(run["run_id"])
        total_files += f
        total_bytes += b

    if OUTPUT_INDEX_FILE.exists():
        OUTPUT_INDEX_FILE.unlink()

    return {
        "runs_removed": len(runs),
        "files_removed": total_files,
        "bytes_freed": total_bytes,
    }


def cleanup_orphaned_outputs() -> dict:
    """Remove flat files in ``data/outputs/`` that are NOT inside ``runs/``.

    Only touches files directly in the outputs root; leaves directories
    (including ``runs/``) untouched.
    """
    files_removed = 0
    bytes_freed = 0

    for path in OUTPUT_DIR.iterdir():
        if path.is_file() and not path.name.startswith("."):
            if path.name == "index.json":
                continue
            bytes_freed += path.stat().st_size
            path.unlink()
            files_removed += 1

    return {
        "files_removed": files_removed,
        "bytes_freed": bytes_freed,
    }


# ── stats & history ─────────────────────────────────────────────────────────

def get_storage_stats() -> dict:
    """Return storage statistics for the outputs directory."""
    runs = list_runs(limit=1000)

    total_files = 0
    total_bytes = 0
    for run in runs:
        run_dir = RUNS_DIR / run["run_id"]
        if run_dir.exists():
            for f in run_dir.rglob("*"):
                if f.is_file():
                    total_bytes += f.stat().st_size
                    total_files += 1

    # Count orphaned files in outputs root
    orphaned = 0
    orphaned_bytes = 0
    if OUTPUT_DIR.exists():
        for path in OUTPUT_DIR.iterdir():
            if path.is_file() and not path.name.startswith("."):
                if path.name == "index.json":
                    continue
                orphaned += 1
                orphaned_bytes += path.stat().st_size

    return {
        "total_runs": len(runs),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 1),
        "orphaned_files": orphaned,
        "orphaned_bytes": orphaned_bytes,
        "orphaned_mb": round(orphaned_bytes / (1024 * 1024), 1),
    }


def get_history() -> list[dict]:
    """Return full generation history (same as ``list_runs`` with all runs)."""
    return list_runs(limit=1000)


# ── internal helpers ────────────────────────────────────────────────────────

def _read_manifest(run_dir: Path) -> dict | None:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_manifest(run_dir: Path, manifest: dict) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def generate_demo_manifest(output_dir: str | Path | None = None) -> dict:
    """Generate a demo manifest summarising the current state.

    Used for project showcase / GitHub README screenshots.
    Writes to ``data/demo/demo_manifest.json``.
    """
    from core.user_profile import load_profile, export_profile_summary

    output_dir = Path(output_dir) if output_dir else Path("data/demo")
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = load_profile()
    summary = export_profile_summary(profile)
    runs = list_runs(limit=20)
    recent_runs = [
        {
            "run_id": r["run_id"],
            "task_type": r["task_type"],
            "status": r["status"],
            "quality_grade": r.get("quality_grade", ""),
            "is_final": r.get("is_final", False),
            "created_at": r.get("created_at", ""),
            "files": r.get("file_count", 0),
        }
        for r in runs[:10]
    ]

    storage = get_storage_stats()

    manifest = {
        "demo_version": "1.3",
        "generated_at": _now(),
        "user_profile": summary,
        "recent_runs": recent_runs,
        "storage": storage,
        "screenshot_suggestions": [
            "1. 首页 Hero + 今日状态卡",
            "2. Agent 输入框 + 个性化计划解析结果",
            "3. 学习路径图（带薄弱点高亮）",
            "4. Wizard Flow 偏好设置页",
            "5. 结果页（含学习建议 + 覆盖率 + 使用场景标签）",
            "6. 输出文件管理页",
            "7. Bunny 助手卡片",
        ],
        "readme_highlights": [
            "个性化学习画像（UserProfile）",
            "自然语言目标解析与自适应推荐",
            "Typst PDF v4.1 四类输出（Sprint/PastPaper/MockExam/Review）",
            "知识图谱与概念学习路径",
            "Bunny AI 学习教练",
            "输出文件管理与 Demo Manifest",
        ],
    }

    manifest_path = output_dir / "demo_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return manifest


def _index_entry(manifest: dict) -> dict:
    """Extract the lightweight index entry from a full manifest."""
    return {
        "run_id": manifest.get("run_id", ""),
        "course_id": manifest.get("course_id", ""),
        "course_name": manifest.get("course_name", ""),
        "chapter_name": manifest.get("chapter_name", ""),
        "task_type": manifest.get("task_type", ""),
        "status": manifest.get("status", ""),
        "quality_score": manifest.get("quality_score", 0),
        "quality_grade": manifest.get("quality_grade", ""),
        "is_final": manifest.get("is_final", False),
        "created_at": manifest.get("created_at", ""),
        "finished_at": manifest.get("finished_at", ""),
        "file_count": len(manifest.get("files", [])),
        "total_bytes": sum(
            f.get("size_bytes", 0) for f in manifest.get("files", [])
        ),
    }
