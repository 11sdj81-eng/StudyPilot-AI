"""OutputManagerV2 — truthful output tracking with file-existence verification.

Wraps existing output_manager. Enforces:
- File existence verified before report claims success
- Atomic writes (tmp → rename)
- Missing files reported as FILE_MISSING, never as success
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUTS_DIR = Path("data/outputs")


class OutputManagerV2:
    """Truthful output management with file verification and atomic writes."""

    def __init__(self, core=None):
        self.core = core
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_run(self, course_id: str, task_type: str,
                   workspace_id: str = "") -> dict:
        """Create a new output run."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        run_dir = OUTPUTS_DIR / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "run_id": run_id,
            "course_id": course_id,
            "workspace_id": workspace_id,
            "task_type": task_type,
            "created_at": now,
            "finished_at": None,
            "outputs": [],
            "status": "pending",
        }
        self._save_manifest(run_id, manifest)
        return manifest

    def save_output(self, run_id: str, content: str, title: str,
                    fmt: str = "md") -> dict:
        """Save an output file atomically. Returns file info with verification."""
        run_dir = OUTPUTS_DIR / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        ext = ".pdf" if fmt == "pdf" else ".md"
        safe_name = self._safe_filename(title)
        final_path = run_dir / f"{safe_name}{ext}"
        tmp_path = run_dir / f"{safe_name}{ext}.tmp"

        # Write to temp file first
        if isinstance(content, str):
            tmp_path.write_text(content, encoding="utf-8")
        else:
            tmp_path.write_bytes(content)

        # Atomic rename
        shutil.move(str(tmp_path), str(final_path))

        # Verify
        file_info = self._verify_file(final_path)
        if not file_info["exists"]:
            # Clean up broken file
            if final_path.exists():
                final_path.unlink()
            file_info["status"] = "FILE_MISSING_AFTER_WRITE"
        else:
            file_info["status"] = "ok"

        # Update manifest
        manifest = self._load_manifest(run_id)
        manifest["outputs"].append(file_info)
        self._save_manifest(run_id, manifest)

        return file_info

    def finalize_run(self, run_id: str, quality: dict | None = None) -> dict:
        """Finalize a run with quality checks and truthful status."""
        manifest = self._load_manifest(run_id)
        manifest["finished_at"] = datetime.now().isoformat()

        # Verify all outputs exist
        all_exist = True
        missing = []
        for output in manifest.get("outputs", []):
            path = Path(output.get("path", ""))
            if not path.exists() or path.stat().st_size == 0:
                all_exist = False
                missing.append(str(path))

        if missing:
            manifest["status"] = "FILE_MISSING"
            manifest["missing_files"] = missing
        elif quality and not quality.get("all_hard_gates_passed", True):
            manifest["status"] = "draft"
        else:
            manifest["status"] = "success"

        manifest["quality"] = quality or {}
        self._save_manifest(run_id, manifest)
        return manifest

    def get_run(self, run_id: str) -> dict | None:
        return self._load_manifest(run_id)

    def list_runs(self, course_id: str = "", workspace_id: str = "",
                  limit: int = 20) -> list[dict]:
        """List runs with optional course/workspace filters."""
        runs_dir = OUTPUTS_DIR / "runs"
        if not runs_dir.exists():
            return []

        runs = []
        for run_dir in sorted(runs_dir.iterdir(), reverse=True):
            manifest_path = run_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if course_id and manifest.get("course_id") != course_id:
                        continue
                    if workspace_id and manifest.get("workspace_id") != workspace_id:
                        continue
                    runs.append(manifest)
                except Exception:
                    pass
            if len(runs) >= limit:
                break
        return runs

    def delete_run(self, run_id: str) -> dict:
        """Delete a run and its files."""
        run_dir = OUTPUTS_DIR / "runs" / run_id
        file_count = 0
        bytes_freed = 0
        if run_dir.exists():
            for f in run_dir.iterdir():
                if f.is_file():
                    bytes_freed += f.stat().st_size
                    file_count += 1
            shutil.rmtree(run_dir)
        return {"run_id": run_id, "files_removed": file_count, "bytes_freed": bytes_freed}

    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        total_files = 0
        total_bytes = 0
        runs_dir = OUTPUTS_DIR / "runs"
        if runs_dir.exists():
            for f in runs_dir.rglob("*"):
                if f.is_file():
                    total_files += 1
                    total_bytes += f.stat().st_size
        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
        }

    # ── Verification ────────────────────────────────────────────────────

    def verify_all_runs(self) -> dict:
        """Verify all runs and flag any with missing files."""
        results = {"total": 0, "healthy": 0, "missing_files": 0, "details": []}
        runs_dir = OUTPUTS_DIR / "runs"
        if not runs_dir.exists():
            return results

        for run_dir in runs_dir.iterdir():
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            results["total"] += 1
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            missing = []
            for output in manifest.get("outputs", []):
                path = Path(output.get("path", ""))
                if not path.exists() or path.stat().st_size == 0:
                    missing.append(str(path))

            if missing:
                results["missing_files"] += 1
                manifest["status"] = "FILE_MISSING"
                manifest["missing_files"] = missing
                self._save_manifest(run_dir.name, manifest)
                results["details"].append({
                    "run_id": run_dir.name,
                    "missing": missing,
                })
            else:
                results["healthy"] += 1

        return results

    def _verify_file(self, path: Path) -> dict:
        """Verify a file exists and return its info."""
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        return {
            "path": str(path.resolve()),
            "exists": exists,
            "file_size": size,
            "file_size_kb": round(size / 1024, 1),
        }

    # ── Internal ─────────────────────────────────────────────────────────

    def _load_manifest(self, run_id: str) -> dict:
        path = OUTPUTS_DIR / "runs" / run_id / "manifest.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"run_id": run_id, "outputs": [], "status": "unknown"}

    def _save_manifest(self, run_id: str, manifest: dict) -> None:
        run_dir = OUTPUTS_DIR / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Sanitize a filename for safe output."""
        import re
        safe = re.sub(r'[<>:"/\\|?*\s]', '_', name)
        return safe[:100] if len(safe) > 100 else safe
