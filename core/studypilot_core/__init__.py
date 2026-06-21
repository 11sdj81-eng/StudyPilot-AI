"""StudyPilotCore — unified system architecture.

All modules work through StudyPilotCore. No module operates independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.studypilot_core.workspace_manager import WorkspaceManager, Workspace
from core.studypilot_core.tutor_brain import TutorBrain
from core.studypilot_core.rag_index_manager import RAGIndexManager
from core.studypilot_core.task_manager_v2 import TaskManagerV2
from core.studypilot_core.output_manager_v2 import OutputManagerV2


# ── System Status ───────────────────────────────────────────────────────

@dataclass
class SystemStatus:
    """Overall system health status."""
    workspaces: int = 0
    active_courses: int = 0
    total_tasks: int = 0
    running_tasks: int = 0
    failed_tasks: int = 0
    total_outputs: int = 0
    rag_courses: int = 0
    rag_integrity_issues: int = 0
    legacy_renderer_active: bool = False
    is_healthy: bool = True

    def to_dict(self) -> dict:
        return {
            "workspaces": self.workspaces, "active_courses": self.active_courses,
            "total_tasks": self.total_tasks, "running_tasks": self.running_tasks,
            "failed_tasks": self.failed_tasks, "total_outputs": self.total_outputs,
            "rag_courses": self.rag_courses, "rag_integrity_issues": self.rag_integrity_issues,
            "legacy_renderer_active": self.legacy_renderer_active,
            "is_healthy": self.is_healthy,
        }


# ── StudyPilotCore ──────────────────────────────────────────────────────

class StudyPilotCore:
    """Unified system core. ALL modules are accessed through this context."""

    def __init__(self):
        self._workspace = None
        self._materials = None
        self._rag = None
        self._tutor = None
        self._tasks = None
        self._outputs = None
        self._quality = None
        self._initialized = False

    @property
    def workspace(self) -> WorkspaceManager:
        if self._workspace is None:
            self._workspace = WorkspaceManager(core=self)
        return self._workspace

    @property
    def materials(self):
        if self._materials is None:
            from core.studypilot_core.material_store import MaterialStore
            self._materials = MaterialStore(core=self)
        return self._materials

    @property
    def rag(self) -> RAGIndexManager:
        if self._rag is None:
            self._rag = RAGIndexManager(core=self)
        return self._rag

    @property
    def tutor(self) -> TutorBrain:
        if self._tutor is None:
            self._tutor = TutorBrain(core=self)
        return self._tutor

    @property
    def tasks(self) -> TaskManagerV2:
        if self._tasks is None:
            self._tasks = TaskManagerV2(core=self)
        return self._tasks

    @property
    def outputs(self) -> OutputManagerV2:
        if self._outputs is None:
            self._outputs = OutputManagerV2(core=self)
        return self._outputs

    @property
    def quality(self):
        if self._quality is None:
            from core.studypilot_core.unified_quality_gate import UnifiedQualityGate
            self._quality = UnifiedQualityGate(core=self)
        return self._quality

    def initialize(self) -> SystemStatus:
        if self._initialized:
            return self.status()
        self.workspace.scan_existing()
        self._initialized = True
        return self.status()

    def status(self) -> SystemStatus:
        ws_list = self.workspace.list_all() if self._workspace else []
        task_stats = self.tasks.get_stats() if self._tasks else {}
        legacy_active = False
        try:
            from core.study_pdf_v3_renderer import render_all_v3_pdfs
            legacy_active = True
        except Exception:
            pass
        return SystemStatus(
            workspaces=len(ws_list), active_courses=len(ws_list),
            total_tasks=task_stats.get("total", 0),
            running_tasks=task_stats.get("running", 0),
            failed_tasks=task_stats.get("failed", 0),
            rag_courses=len(self.rag.list_courses()) if self._rag else 0,
            legacy_renderer_active=legacy_active,
            is_healthy=True,
        )

    def shutdown(self) -> dict:
        result = {"clean": True, "warnings": []}
        if self._tasks:
            for t in self._tasks.list_by_status("running"):
                self._tasks.cancel(t.get("task_id", ""))
                result["warnings"].append(f"Cancelled: {t.get('task_id')}")
        return result


# ── Singleton ───────────────────────────────────────────────────────────

_core: StudyPilotCore | None = None

def get_core() -> StudyPilotCore:
    global _core
    if _core is None:
        _core = StudyPilotCore()
    return _core

def reset_core() -> None:
    global _core
    _core = None
