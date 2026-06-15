"""FigureBank —— StudyPilot image asset bank.

Maintains the authoritative index of all managed figure assets under
data/figure_bank/.  Provides CRUD, search, and organisation operations.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.figure_engine.figure_objects import FigureObject, SourceType, ConceptId

# Canonical bank root
BANK_ROOT = Path("data/figure_bank")
INDEX_PATH = BANK_ROOT / "index.json"


class FigureBank:
    """Central asset bank for all teaching figures."""

    def __init__(self, bank_root: str | Path = BANK_ROOT):
        self.root = Path(bank_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._figures: dict[str, FigureObject] = {}
        self.load_index()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_figure(self, figure: FigureObject) -> str:
        """Add a figure to the bank.  Returns the figure_id."""
        if figure.figure_id in self._figures:
            # Update existing
            self._figures[figure.figure_id] = figure
        else:
            self._figures[figure.figure_id] = figure

        # Copy image file into bank structure if it's outside
        self._ensure_image_in_bank(figure)
        return figure.figure_id

    def remove_figure(self, figure_id: str) -> bool:
        """Remove a figure from the bank."""
        if figure_id not in self._figures:
            return False
        fig = self._figures.pop(figure_id)
        # Remove image file from bank
        bank_img = self._bank_image_path(fig)
        if bank_img.exists():
            bank_img.unlink()
        return True

    def get_figure(self, figure_id: str) -> FigureObject | None:
        """Get a figure by ID."""
        return self._figures.get(figure_id)

    def list_figures(self) -> list[FigureObject]:
        """List all figures in the bank."""
        return list(self._figures.values())

    # ------------------------------------------------------------------
    # Search & query
    # ------------------------------------------------------------------

    def search_by_concept(
        self,
        concept_id: str,
        min_score: float = 0.0,
    ) -> list[FigureObject]:
        """Return figures matching a concept_id, sorted by final_score desc."""
        results = [
            f for f in self._figures.values()
            if f.concept_id == concept_id and f.final_score >= min_score
        ]
        results.sort(key=lambda f: f.final_score, reverse=True)
        return results

    def search_by_tags(
        self,
        tags: list[str],
        min_match: int = 1,
    ) -> list[FigureObject]:
        """Return figures matching at least min_match tags."""
        results: list[FigureObject] = []
        for f in self._figures.values():
            matched = sum(1 for t in tags if t in f.tags)
            if matched >= min_match:
                results.append(f)
        results.sort(key=lambda f: f.final_score, reverse=True)
        return results

    def get_best_figure(
        self,
        concept_id: str,
        source_type_priority: list[str] | None = None,
    ) -> FigureObject | None:
        """Return the single best figure for a concept."""
        candidates = self.search_by_concept(concept_id)
        if not candidates:
            return None

        if source_type_priority:
            for st in source_type_priority:
                for f in candidates:
                    if f.source_type == st:
                        return f

        return candidates[0]  # highest final_score

    # ------------------------------------------------------------------
    # Mark-as-used tracking
    # ------------------------------------------------------------------

    def mark_used(self, figure_id: str, context: str = "") -> None:
        """Mark a figure as used in a specific PDF context."""
        fig = self._figures.get(figure_id)
        if fig:
            used = fig.metadata.setdefault("used_in", [])
            if context and context not in used:
                used.append(context)
            fig.metadata["last_used"] = datetime.now(timezone.utc).isoformat()

    def get_used_in(self, figure_id: str) -> list[str]:
        """Get list of PDF contexts where a figure has been used."""
        fig = self._figures.get(figure_id)
        return fig.metadata.get("used_in", []) if fig else []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_index(self) -> dict[str, Any]:
        """Export the full index as a dict for serialization."""
        return {
            "bank_version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_figures": len(self._figures),
            "by_source_type": self._count_by_source_type(),
            "by_concept": self._count_by_concept(),
            "figures": [f.to_dict() for f in self._figures.values()],
        }

    def save_index(self, path: str | Path | None = None) -> Path:
        """Persist the index to disk."""
        target = Path(path) if path else self.index_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.export_index(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def load_index(self) -> None:
        """Load the index from disk if it exists."""
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                for fig_dict in data.get("figures", []):
                    fig = FigureObject.from_dict(fig_dict)
                    self._figures[fig.figure_id] = fig
            except Exception as e:
                print(f"[FigureBank] Warning: could not load index: {e}")
                self._figures = {}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def count(self) -> int:
        return len(self._figures)

    def _count_by_source_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self._figures.values():
            counts[f.source_type] = counts.get(f.source_type, 0) + 1
        return counts

    def _count_by_concept(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self._figures.values():
            if f.concept_id:
                counts[f.concept_id] = counts.get(f.concept_id, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bank_image_path(self, figure: FigureObject) -> Path:
        """Compute the canonical path for an image inside the bank."""
        concept = figure.concept_id or "unmatched"
        return self.root / "electromagnetic_static" / concept / "images" / Path(figure.image_path).name

    def _ensure_image_in_bank(self, figure: FigureObject) -> None:
        """Copy the image file into the bank directory structure if it lives outside."""
        src = Path(figure.image_path)
        if not src.exists():
            return

        dst = self._bank_image_path(figure)
        if dst.resolve() == src.resolve():
            return  # already in place

        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)

        # Write per-concept metadata
        concept_dir = dst.parent.parent
        meta_path = concept_dir / "metadata.json"
        existing: dict[str, Any] = {}
        if meta_path.exists():
            try:
                existing = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        existing[figure.figure_id] = {
            "source_type": figure.source_type,
            "source_file": figure.source_file,
            "source_page": figure.source_page,
            "quality_score": figure.quality_score,
            "match_score": figure.match_score,
            "final_score": figure.final_score,
            "tags": figure.tags,
            "caption": figure.caption,
            "image_path": str(dst),
            "created_at": figure.created_at,
        }
        meta_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
