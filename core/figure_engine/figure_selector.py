"""FigureSelector —— Select the best figure for a given concept and PDF context.

Selection strategy:
1. Prefer textbook/ppt/past_paper sources
2. Match PDF type to figure style
3. Avoid reusing the same figure in the same PDF
4. Avoid using the same figure in all four PDFs
5. Fallback to redraw/programmatic if no high-quality figure found
6. Record all fallbacks
"""

from __future__ import annotations

from typing import Any

from core.figure_engine.figure_objects import FigureObject, SourceType, ConceptId


PDF_TYPE = {
    "sprint": "sprint",
    "pastpaper": "pastpaper",
    "mockexam": "mockexam",
    "review": "review",
}

PURPOSE = {
    "quick_memory": "quick_memory",
    "exam_solution": "exam_solution",
    "problem_statement": "problem_statement",
    "full_explanation": "full_explanation",
    "formula_explanation": "formula_explanation",
}

# Source type priority for each PDF type
PDF_SOURCE_PRIORITY: dict[str, list[str]] = {
    "sprint": [SourceType.TEXTBOOK, SourceType.PPT, SourceType.REDRAW, SourceType.PROGRAMMATIC],
    "pastpaper": [SourceType.PAST_PAPER, SourceType.TEXTBOOK, SourceType.REDRAW, SourceType.PROGRAMMATIC],
    "mockexam": [SourceType.PAST_PAPER, SourceType.TEXTBOOK, SourceType.REDRAW, SourceType.PROGRAMMATIC],
    "review": [SourceType.TEXTBOOK, SourceType.PPT, SourceType.PAST_PAPER, SourceType.REDRAW, SourceType.PROGRAMMATIC],
}


class FigureSelector:
    """Select the best figure for a given concept and PDF context."""

    def __init__(self):
        # Track which figures have been used in which PDF context
        self._usage: dict[str, set[str]] = {}  # figure_id -> set of pdf_type
        self._fallback_log: list[dict[str, Any]] = []

    def select_figure(
        self,
        figures: list[FigureObject],
        concept_id: str,
        pdf_type: str,
        purpose: str = "full_explanation",
        allow_fallback: bool = True,
    ) -> FigureObject | None:
        """Select the best figure for a concept and PDF context.

        Args:
            figures: Available FigureObject candidates.
            concept_id: Target concept (e.g. 'gauss_law').
            pdf_type: One of 'sprint', 'pastpaper', 'mockexam', 'review'.
            purpose: Usage purpose (quick_memory, exam_solution, etc.).
            allow_fallback: If True, fallback to redraw/programmatic when no
                            high-quality source figure found.

        Returns:
            Best FigureObject, or None if no suitable figure found.
        """
        # Filter by concept
        candidates = [f for f in figures if f.concept_id == concept_id]
        if not candidates:
            if allow_fallback:
                return self._fallback_select(figures, concept_id, pdf_type, purpose, "no concept match")
            return None

        # Sort by final_score desc
        candidates.sort(key=lambda f: f.final_score, reverse=True)

        # Get source type priority for this PDF type
        priority = PDF_SOURCE_PRIORITY.get(pdf_type, PDF_SOURCE_PRIORITY["review"])

        # Try each priority level
        for source_type in priority:
            for fig in candidates:
                if fig.source_type == source_type:
                    if self._can_use(fig.figure_id, pdf_type):
                        self._record_usage(fig.figure_id, pdf_type)
                        return fig

        # If no priority match, try any high-score candidate
        for fig in candidates:
            if fig.final_score >= 30.0 and self._can_use(fig.figure_id, pdf_type):
                self._record_usage(fig.figure_id, pdf_type)
                return fig

        # Fallback
        if allow_fallback:
            return self._fallback_select(figures, concept_id, pdf_type, purpose, "no suitable high-score figure")

        return None

    def select_all(
        self,
        figures: list[FigureObject],
        concept_ids: list[str],
        pdf_type: str,
        purpose: str = "full_explanation",
        allow_fallback: bool = True,
    ) -> dict[str, FigureObject | None]:
        """Select best figures for multiple concepts. Returns {concept_id: FigureObject}."""
        result: dict[str, FigureObject | None] = {}
        for cid in concept_ids:
            result[cid] = self.select_figure(figures, cid, pdf_type, purpose, allow_fallback)
        return result

    def _fallback_select(
        self,
        figures: list[FigureObject],
        concept_id: str,
        pdf_type: str,
        purpose: str,
        reason: str,
    ) -> FigureObject | None:
        """Select a fallback figure (redraw or programmatic)."""
        fallback_types = [SourceType.REDRAW, SourceType.PROGRAMMATIC, SourceType.AI_GENERATED]

        for fb_type in fallback_types:
            for f in figures:
                if f.concept_id == concept_id and f.source_type == fb_type:
                    if self._can_use(f.figure_id, pdf_type):
                        self._record_usage(f.figure_id, pdf_type)
                        self._fallback_log.append({
                            "concept_id": concept_id,
                            "pdf_type": pdf_type,
                            "purpose": purpose,
                            "reason": reason,
                            "fallback_figure_id": f.figure_id,
                            "fallback_source_type": f.source_type,
                        })
                        return f

        # Last resort: any concept-matching figure
        for f in figures:
            if f.concept_id == concept_id and self._can_use(f.figure_id, pdf_type):
                self._record_usage(f.figure_id, pdf_type)
                self._fallback_log.append({
                    "concept_id": concept_id,
                    "pdf_type": pdf_type,
                    "purpose": purpose,
                    "reason": reason,
                    "fallback_figure_id": f.figure_id,
                    "fallback_source_type": f.source_type,
                })
                return f

        return None

    def _can_use(self, figure_id: str, pdf_type: str) -> bool:
        """Check if a figure can be used in a given PDF type (avoid reuse)."""
        if figure_id not in self._usage:
            return True
        return pdf_type not in self._usage[figure_id]

    def _record_usage(self, figure_id: str, pdf_type: str) -> None:
        """Record that a figure has been used in a PDF type."""
        if figure_id not in self._usage:
            self._usage[figure_id] = set()
        self._usage[figure_id].add(pdf_type)

    def get_fallback_log(self) -> list[dict[str, Any]]:
        """Return the fallback log."""
        return self._fallback_log

    def reset_usage(self) -> None:
        """Reset usage tracking (for a new PDF generation session)."""
        self._usage.clear()
        self._fallback_log.clear()
