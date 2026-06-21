"""FigureCache — avoid regenerating identical figures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path("data/outputs/figures_cache")


class FigureCache:
    """Simple file-based cache for generated SVG figures."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, str] = self._load_index()

    def get(self, figure_id: str) -> str | None:
        """Get cached SVG content for a figure_id."""
        if figure_id not in self._index:
            return None
        path = self.cache_dir / self._index[figure_id]
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def set(self, figure_id: str, svg_content: str) -> None:
        """Cache SVG content."""
        key = hashlib.md5((figure_id + svg_content[:100]).encode()).hexdigest()[:12]
        filename = f"{figure_id}_{key}.svg"
        path = self.cache_dir / filename
        path.write_text(svg_content, encoding="utf-8")
        self._index[figure_id] = filename
        self._save_index()

    def has(self, figure_id: str) -> bool:
        return figure_id in self._index

    def count(self) -> int:
        return len(self._index)

    def _load_index(self) -> dict[str, str]:
        idx_path = self.cache_dir / "index.json"
        if idx_path.exists():
            return json.loads(idx_path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self) -> None:
        (self.cache_dir / "index.json").write_text(
            json.dumps(self._index, ensure_ascii=False), encoding="utf-8"
        )

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.svg"):
            f.unlink()
        self._index = {}
        self._save_index()
