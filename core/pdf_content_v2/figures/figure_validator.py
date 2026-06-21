"""FigureValidator — quality checks for generated figures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.pdf_content_v2.figures.figure_registry import FigureCard


@dataclass
class FigureReport:
    total_figures: int = 0
    svg_figures: int = 0
    ocr_figures: int = 0
    ai_figures: int = 0
    figures_with_caption: int = 0
    missing_caption_count: int = 0
    blank_figure_count: int = 0
    a_level_concepts: int = 0
    a_level_with_figures: int = 0
    figure_issue_count: int = 0
    issues: list[str] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "total_figures": self.total_figures, "svg_figures": self.svg_figures,
            "ocr_figures": self.ocr_figures, "ai_figures": self.ai_figures,
            "figures_with_caption": self.figures_with_caption,
            "missing_caption_count": self.missing_caption_count,
            "blank_figure_count": self.blank_figure_count,
            "a_level_concepts": self.a_level_concepts,
            "a_level_with_figures": self.a_level_with_figures,
            "a_level_coverage_rate": round(
                self.a_level_with_figures / max(1, self.a_level_concepts), 2
            ),
            "figure_issue_count": self.figure_issue_count,
            "passed": self.passed,
        }


class FigureValidator:
    """Validate figure quality and coverage."""

    MIN_SVG_SIZE = 100  # bytes — smaller is likely broken

    def validate(self, figures: list[FigureCard],
                 a_level_concept_ids: list[str] | None = None) -> FigureReport:
        report = FigureReport()
        report.total_figures = len(figures)
        a_level_ids = set(a_level_concept_ids or [])

        for f in figures:
            if "svg" in f.generated_by.lower() or f.svg_content:
                report.svg_figures += 1
                if len(f.svg_content) < self.MIN_SVG_SIZE:
                    report.blank_figure_count += 1
                    report.issues.append(f"空白/损坏图: {f.figure_id}")
            elif f.source_level == "ocr":
                report.ocr_figures += 1
            elif "ai" in f.source_level.lower():
                report.ai_figures += 1

            if f.caption and len(f.caption) > 5:
                report.figures_with_caption += 1
            else:
                report.missing_caption_count += 1
                report.issues.append(f"缺少图注: {f.figure_id}")

            if f.concept_id in a_level_ids:
                report.a_level_with_figures += 1

        report.a_level_concepts = len(a_level_ids)
        report.figure_issue_count = report.blank_figure_count + report.missing_caption_count
        report.passed = report.figure_issue_count == 0
        return report
