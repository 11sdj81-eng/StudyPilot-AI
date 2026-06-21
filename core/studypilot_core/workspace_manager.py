"""WorkspaceManager — one workspace per course. Persists and restores session state.

Replaces the fragile session_state-only approach. Each course gets a workspace
that remembers materials, profile, tasks, and outputs across sessions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACES_DIR = Path("data/workspaces")


@dataclass
class Workspace:
    """A course workspace that persists across sessions."""
    workspace_id: str
    course_id: str
    course_name: str = ""
    chapter: str = ""
    subject_type: str = "unknown"
    created_at: str = ""
    last_opened_at: str = ""
    materials: list[str] = field(default_factory=list)    # resource_ids
    profile_summary: dict = field(default_factory=dict)     # CourseProfile summary
    rag_status: str = "empty"      # built / stale / empty
    tasks: list[str] = field(default_factory=list)         # task_ids
    outputs: list[str] = field(default_factory=list)       # run_ids
    is_demo: bool = False

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "course_id": self.course_id,
            "course_name": self.course_name,
            "chapter": self.chapter,
            "subject_type": self.subject_type,
            "created_at": self.created_at,
            "last_opened_at": self.last_opened_at,
            "materials": self.materials,
            "profile_summary": self.profile_summary,
            "rag_status": self.rag_status,
            "tasks": self.tasks,
            "outputs": self.outputs,
            "is_demo": self.is_demo,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Workspace:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class WorkspaceManager:
    """Manages course workspaces with persistent storage."""

    def __init__(self, core=None):
        self.core = core
        self._cache: dict[str, Workspace] = {}
        WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

    # ── CRUD ────────────────────────────────────────────────────────────

    def create(self, course_id: str, course_name: str = "",
               chapter: str = "", subject_type: str = "unknown") -> Workspace:
        """Create a new workspace for a course."""
        workspace_id = f"ws_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()

        # Try to get profile
        profile_summary = {}
        try:
            from core.course_profiles.profile_registry import get_profile
            profile = get_profile(course_id)
            profile_summary = {
                "course_name": profile.course_name,
                "subject_type": profile.subject_type,
                "concept_count": profile.concept_count,
                "formula_count": profile.formula_count,
                "source": profile.source.value,
            }
            course_name = course_name or profile.course_name
            subject_type = subject_type or profile.subject_type
        except Exception:
            pass

        ws = Workspace(
            workspace_id=workspace_id,
            course_id=course_id,
            course_name=course_name,
            chapter=chapter,
            subject_type=subject_type,
            created_at=now,
            last_opened_at=now,
            profile_summary=profile_summary,
        )
        self._save(ws)
        self._cache[workspace_id] = ws
        return ws

    def get(self, workspace_id: str) -> Workspace | None:
        """Get a workspace by ID."""
        if workspace_id in self._cache:
            return self._cache[workspace_id]

        path = WORKSPACES_DIR / workspace_id / "workspace.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            ws = Workspace.from_dict(data)
            self._cache[workspace_id] = ws
            return ws
        return None

    def get_by_course(self, course_id: str) -> Workspace | None:
        """Find workspace by course_id."""
        for ws_dir in WORKSPACES_DIR.iterdir():
            if ws_dir.is_dir():
                ws_file = ws_dir / "workspace.json"
                if ws_file.exists():
                    data = json.loads(ws_file.read_text(encoding="utf-8"))
                    if data.get("course_id") == course_id:
                        return Workspace.from_dict(data)
        return None

    def get_or_create(self, course_id: str, course_name: str = "",
                      chapter: str = "") -> Workspace:
        """Get existing workspace or create a new one."""
        existing = self.get_by_course(course_id)
        if existing:
            return self.open(existing.workspace_id)
        return self.create(course_id, course_name, chapter)

    def open(self, workspace_id: str) -> Workspace | None:
        """Open a workspace (updates last_opened_at)."""
        ws = self.get(workspace_id)
        if ws:
            ws.last_opened_at = datetime.now().isoformat()
            self._save(ws)
            self._cache[workspace_id] = ws
        return ws

    def update(self, workspace_id: str, **kwargs) -> Workspace | None:
        """Update workspace fields."""
        ws = self.get(workspace_id)
        if ws:
            for key, value in kwargs.items():
                if hasattr(ws, key):
                    setattr(ws, key, value)
            self._save(ws)
            self._cache[workspace_id] = ws
        return ws

    def delete(self, workspace_id: str) -> bool:
        """Delete a workspace and its data directory."""
        import shutil
        ws_dir = WORKSPACES_DIR / workspace_id
        if ws_dir.exists():
            shutil.rmtree(ws_dir)
        self._cache.pop(workspace_id, None)
        return True

    def list_all(self) -> list[dict]:
        """List all workspaces, sorted by last_opened_at desc."""
        workspaces = []
        if WORKSPACES_DIR.exists():
            for ws_dir in sorted(WORKSPACES_DIR.iterdir(), reverse=True):
                if ws_dir.is_dir():
                    ws_file = ws_dir / "workspace.json"
                    if ws_file.exists():
                        try:
                            data = json.loads(ws_file.read_text(encoding="utf-8"))
                            workspaces.append(data)
                        except Exception:
                            pass
        workspaces.sort(key=lambda w: w.get("last_opened_at", ""), reverse=True)
        return workspaces

    def scan_existing(self) -> int:
        """Scan for existing workspaces on disk. Called on startup."""
        count = 0
        for ws_dir in WORKSPACES_DIR.iterdir():
            if ws_dir.is_dir() and (ws_dir / "workspace.json").exists():
                count += 1
        return count

    def add_material(self, workspace_id: str, resource_id: str) -> None:
        """Record that a material was added to this workspace."""
        ws = self.get(workspace_id)
        if ws and resource_id not in ws.materials:
            ws.materials.append(resource_id)
            ws.rag_status = "stale"
            self._save(ws)

    def add_task(self, workspace_id: str, task_id: str) -> None:
        """Record a task for this workspace."""
        ws = self.get(workspace_id)
        if ws and task_id not in ws.tasks:
            ws.tasks.append(task_id)
            self._save(ws)

    def add_output(self, workspace_id: str, run_id: str) -> None:
        """Record an output run for this workspace."""
        ws = self.get(workspace_id)
        if ws and run_id not in ws.outputs:
            ws.outputs.append(run_id)
            self._save(ws)

    # ── Internal ─────────────────────────────────────────────────────────

    def _save(self, ws: Workspace) -> None:
        ws_dir = WORKSPACES_DIR / ws.workspace_id
        ws_dir.mkdir(parents=True, exist_ok=True)
        path = ws_dir / "workspace.json"
        path.write_text(json.dumps(ws.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
