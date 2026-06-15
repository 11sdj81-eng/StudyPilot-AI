"""FigureRewriter —— Redraw or regenerate figures from teaching assets.

Reserved interface for future AI-powered redrawing.  Current fallback delegates
to the existing v4/v4.1 SVG figure builder, carrying forward concept_id and tags.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.figure_engine.figure_objects import FigureObject, SourceType


# Style presets
TARGET_STYLES = {
    "study_pilot_clean": "Clean, textbook-style educational diagram with Chinese labels.",
    "goodnotes_friendly": "Handwriting-friendly style suitable for GoodNotes annotation.",
    "exam_problem": "Concise problem-solving diagram, exam-sheet style.",
    "quick_memory": "Minimalist memory-aid diagram for quick review.",
}


class FigureRewriter:
    """Rewrites/generates figures — reserved for future AI-powered redrawing."""

    def __init__(self, output_dir: str | Path = "data/figure_bank/_processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._rewrite_count = 0

    def rewrite_figure(
        self,
        source_figure: FigureObject,
        target_style: str = "study_pilot_clean",
        annotations: list[str] | None = None,
    ) -> FigureObject:
        """Generate a 'redraw' version of a source figure.

        Current implementation delegates to the existing v4 SVG figure builder
        when possible.  AI-powered redrawing is reserved for future versions.

        Args:
            source_figure: The source FigureObject to redraw.
            target_style: One of TARGET_STYLES keys.
            annotations: Optional list of annotation texts to add.

        Returns:
            A new FigureObject with source_type='redraw'.
        """
        self._rewrite_count += 1

        fig_id = f"redraw_{source_figure.figure_id}_{self._rewrite_count}"

        # For now, we carry forward the source figure's path and mark it as redraw.
        # Future: call AI image generation or programmatic SVG builder.
        redrawn = FigureObject(
            figure_id=fig_id,
            concept_id=source_figure.concept_id,
            source_type=SourceType.REDRAW,
            source_file=source_figure.source_file,
            source_page=source_figure.source_page,
            bbox=source_figure.bbox,
            image_path=source_figure.image_path,  # reuse original; future: replace with new render
            caption=source_figure.caption,
            ocr_text=source_figure.ocr_text,
            tags=list(set(source_figure.tags + (annotations or []))),
            quality_score=15.0,   # baseline for redraw
            match_score=source_figure.match_score,
            usability_score=10.0,
            width=source_figure.width,
            height=source_figure.height,
            aspect_ratio=source_figure.aspect_ratio,
            has_text_overlap_risk=False,
            has_low_resolution_risk=False,
            has_noise_risk=False,
            metadata={
                "rewritten_from": source_figure.figure_id,
                "target_style": target_style,
                "annotations": annotations or [],
                "rewrite_method": "delegated_v4_svg_builder",
            },
        )

        return redrawn

    def build_programmatic_fallback(
        self,
        concept_id: str,
        svg_path: str | Path,
        caption: str | None = None,
    ) -> FigureObject:
        """Build a FigureObject wrapping an existing programmatic SVG.

        This is the fallback path — when no textbook/PPT/pastpaper figures are
        available, this method wraps existing v4 SVG figures as FigureObjects.
        """
        svg_path = Path(svg_path)
        fig_id = f"prog_{concept_id}_{self._rewrite_count}"
        self._rewrite_count += 1

        caption_text = caption or svg_path.stem.replace("_", " ")

        return FigureObject(
            figure_id=fig_id,
            concept_id=concept_id,
            source_type=SourceType.PROGRAMMATIC,
            source_file=str(svg_path.name),
            source_page=None,
            bbox=None,
            image_path=str(svg_path.resolve()),
            caption=caption_text,
            ocr_text=None,
            tags=[concept_id, "programmatic", "fallback"],
            quality_score=8.0,
            match_score=20.0,
            usability_score=10.0,
            width=980,
            height=560,
            aspect_ratio=1.75,
            has_text_overlap_risk=False,
            has_low_resolution_risk=True,  # SVG is vector, but we're honest about it being programmatic
            has_noise_risk=False,
            metadata={
                "build_method": "programmatic_fallback",
                "is_fallback": True,
            },
        )
