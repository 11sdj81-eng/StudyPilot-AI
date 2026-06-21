"""FigureCard and FigureRegistry — unified figure metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Per-course supported figure types
SUPPORTED_FIGURES: dict[str, list[str]] = {
    "math": ["cdf_curve", "pmf_bar", "pdf_curve", "normal_curve",
              "exponential_curve", "uniform_rect", "comparison_chart"],
    "engineering": ["field_line", "gaussian_surface", "boundary_diagram",
                     "mirror_diagram", "coordinate_system", "circuit_diagram"],
    "digital_logic": ["truth_table", "kmap_diagram", "state_diagram",
                       "timing_diagram", "logic_gate_diagram"],
}


@dataclass
class FigureCard:
    figure_id: str
    course_id: str
    chapter_id: str
    concept_id: str
    figure_type: str           # e.g. "normal_curve"
    title: str                 # e.g. "正态分布曲线"
    caption: str               # e.g. "图 2-1 标准正态分布 N(0,1) 密度曲线"
    source_level: str = "programmatic"
    source_refs: list[str] = field(default_factory=list)
    file_path: str = ""        # path to SVG file
    generated_by: str = "FigureGenerator"
    confidence: float = 0.9
    width: int = 400
    height: int = 250
    svg_content: str = ""      # inline SVG for rendering

    def to_dict(self) -> dict:
        return {
            "figure_id": self.figure_id, "concept_id": self.concept_id,
            "figure_type": self.figure_type, "title": self.title,
            "caption": self.caption, "source_level": self.source_level,
            "source_refs": self.source_refs, "confidence": self.confidence,
        }

    def typst_figure_block(self) -> str:
        """Render as Typst figure block."""
        if self.svg_content:
            return (
                f'#figure(\n  image("{self.file_path}", width: {self.width}pt),\n'
                f'  caption: [{self.caption}]\n)'
            )
        return f'#figure(caption: [{self.caption}])[ // Figure placeholder: {self.title} ]'


class FigureRegistry:
    """Central registry for all figures."""

    def __init__(self):
        self._figures: dict[str, FigureCard] = {}
        self._by_concept: dict[str, list[FigureCard]] = {}

    def register(self, figure: FigureCard) -> None:
        self._figures[figure.figure_id] = figure
        self._by_concept.setdefault(figure.concept_id, []).append(figure)

    def get(self, figure_id: str) -> FigureCard | None:
        return self._figures.get(figure_id)

    def for_concept(self, concept_id: str) -> list[FigureCard]:
        return self._by_concept.get(concept_id, [])

    def count(self) -> int:
        return len(self._figures)

    def supported_types(self, subject_type: str) -> list[str]:
        return SUPPORTED_FIGURES.get(subject_type, ["generic_diagram"])

    def stats(self) -> dict:
        types = {}
        for f in self._figures.values():
            types[f.figure_type] = types.get(f.figure_type, 0) + 1
        return {"total": len(self._figures), "by_type": types}
