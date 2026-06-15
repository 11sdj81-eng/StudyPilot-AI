"""FigureObject data structures for StudyPilot Figure Engine."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


class SourceType:
    """Allowed source_type values."""
    TEXTBOOK = "textbook"
    PPT = "ppt"
    PAST_PAPER = "past_paper"
    NOTE = "note"
    PROGRAMMATIC = "programmatic"
    REDRAW = "redraw"
    AI_GENERATED = "ai_generated"
    UNKNOWN = "unknown"
    SCANNED_PAGE = "scanned_page"

    ALL = {TEXTBOOK, PPT, PAST_PAPER, NOTE, PROGRAMMATIC, REDRAW, AI_GENERATED, UNKNOWN, SCANNED_PAGE}


class ConceptId:
    """Allowed concept_id values for 电磁场与电磁波 第一章静电场."""
    ELECTRIC_FIELD = "electric_field"
    GAUSS_LAW = "gauss_law"
    POTENTIAL_GRADIENT = "potential_gradient"
    BOUNDARY_CONDITION = "boundary_condition"
    MIRROR_METHOD = "mirror_method"
    ELECTROSTATIC_ENERGY = "electrostatic_energy"

    ALL = {ELECTRIC_FIELD, GAUSS_LAW, POTENTIAL_GRADIENT, BOUNDARY_CONDITION, MIRROR_METHOD, ELECTROSTATIC_ENERGY}

    LABELS = {
        ELECTRIC_FIELD: "电场强度与电场线",
        GAUSS_LAW: "高斯定理",
        POTENTIAL_GRADIENT: "电位梯度",
        BOUNDARY_CONDITION: "边界条件",
        MIRROR_METHOD: "镜像法",
        ELECTROSTATIC_ENERGY: "静电能量",
    }


@dataclass
class FigureObject:
    """Represents one extracted/managed figure asset."""
    figure_id: str
    concept_id: str | None
    source_type: str
    source_file: str
    source_page: int | None
    bbox: tuple | None
    image_path: str
    caption: str | None
    ocr_text: str | None
    tags: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    match_score: float = 0.0
    usability_score: float = 0.0
    width: int | None = None
    height: int | None = None
    aspect_ratio: float | None = None
    has_text_overlap_risk: bool = False
    has_low_resolution_risk: bool = False
    has_noise_risk: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def final_score(self) -> float:
        return self.quality_score + self.match_score + self.usability_score

    @property
    def concept_label(self) -> str:
        if self.concept_id:
            return ConceptId.LABELS.get(self.concept_id, self.concept_id)
        return "未匹配"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bbox"] = list(self.bbox) if self.bbox else None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FigureObject":
        d = dict(data)
        if d.get("bbox") and isinstance(d["bbox"], list):
            d["bbox"] = tuple(d["bbox"])
        return cls(**{k: d.get(k) for k in [
            "figure_id", "concept_id", "source_type", "source_file",
            "source_page", "bbox", "image_path", "caption", "ocr_text",
            "tags", "quality_score", "match_score", "usability_score",
            "width", "height", "aspect_ratio",
            "has_text_overlap_risk", "has_low_resolution_risk", "has_noise_risk",
            "created_at", "metadata",
        ]})

    def __repr__(self) -> str:
        return (
            f"FigureObject(id={self.figure_id!r}, concept={self.concept_id!r}, "
            f"source={self.source_type!r}, score={self.final_score:.1f})"
        )
