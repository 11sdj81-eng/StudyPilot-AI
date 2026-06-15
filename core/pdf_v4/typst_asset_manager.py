"""Asset manifest for StudyPilot PDF v4 Typst outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


FIGURE_DIR = Path("data/assets/pdf_v4/figures")


@dataclass
class V4FigureAsset:
    id: str
    title: str
    caption: str
    concept_id: str
    source: str
    path: str
    pdf_types: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def write_figure_manifest(assets: list[V4FigureAsset], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([a.to_dict() for a in assets], ensure_ascii=False, indent=2), encoding="utf-8")
    return path
