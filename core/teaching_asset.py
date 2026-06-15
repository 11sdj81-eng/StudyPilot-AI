"""Teaching asset data model for StudyPilot v3.1."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TeachingAsset:
    id: str
    concept_id: str
    asset_type: str
    source: str
    pdf_types: list[str]
    difficulty: str
    usage_context: str
    path: str
    caption: str
    why_needed: str
    visual_style: str
    usage_count: int = 0
    max_usage_per_run: int = 1
    title: str = ""
    confidence: float = 0.85
    source_file: str = ""
    page: str = ""
    bbox: list[float] | None = None

    def to_dict(self) -> dict:
        return asdict(self)
