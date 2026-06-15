"""FigureQualityGate —— Quality assurance checks for the figure bank.

Checks for:
1. Broken images
2. Low-resolution figures
3. Scanned pages misidentified as figures
4. Concept mismatch
5. Duplicate figures
6. Missing captions
7. Source type spoofing
8. Excessive fallbacks
9. No textbook/PPT/past-paper hits
10. Insufficient figure count
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.figure_engine.figure_objects import FigureObject, SourceType, ConceptId

# Quality thresholds
MIN_RESOLUTION_W = 300
MIN_RESOLUTION_H = 200
MIN_TOTAL_FIGURES = 3
MAX_DUPLICATE_RATIO = 0.5  # if >50% are duplicates, flag it
MAX_FALLBACK_RATIO = 0.7


class FigureQualityGate:
    """Run quality checks on the figure bank."""

    def __init__(self):
        self._results: dict[str, Any] = {}

    def check(self, figures: list[FigureObject]) -> dict[str, Any]:
        """Run all quality checks and return a report."""
        results = {
            "total_figures": len(figures),
            "textbook_figures": 0,
            "ppt_figures": 0,
            "past_paper_figures": 0,
            "programmatic_figures": 0,
            "fallback_count": 0,
            "duplicate_count": 0,
            "broken_count": 0,
            "low_resolution_count": 0,
            "scanned_page_count": 0,
            "concept_unmatched_count": 0,
            "missing_caption_count": 0,
            "concept_match_pass": False,
            "recommend_use_in_pdf": False,
            "issues": [],
            "warnings": [],
        }

        # Count by source type
        for f in figures:
            st = f.source_type
            if st == SourceType.TEXTBOOK:
                results["textbook_figures"] += 1
            elif st == SourceType.PPT:
                results["ppt_figures"] += 1
            elif st == SourceType.PAST_PAPER:
                results["past_paper_figures"] += 1
            elif st == SourceType.PROGRAMMATIC:
                results["programmatic_figures"] += 1
            if f.metadata.get("is_fallback"):
                results["fallback_count"] += 1

        # 1. Broken images
        results["broken_count"] = self._check_broken_images(figures, results)

        # 2. Low resolution
        results["low_resolution_count"] = self._check_low_resolution(figures, results)

        # 3. Scanned pages
        results["scanned_page_count"] = self._check_scanned_pages(figures, results)

        # 4. Concept unmatched
        results["concept_unmatched_count"] = self._check_concept_match(figures, results)

        # 5. Duplicates
        results["duplicate_count"] = self._check_duplicates(figures, results)

        # 6. Missing captions
        results["missing_caption_count"] = self._check_captions(figures, results)

        # 7. Source type spoofing
        self._check_spoofing(figures, results)

        # 8. Fallback ratio
        self._check_fallback_ratio(figures, results)

        # 9. No textbook/PPT/past-paper hits
        self._check_source_hits(results)

        # 10. Figure count
        self._check_figure_count(results)

        # Final recommendation
        results["concept_match_pass"] = results["concept_unmatched_count"] < len(figures) * 0.5

        # Check for concept-matched real-source figures (not scanned pages, not programmatic)
        real_source_concept_matched = sum(
            1 for f in figures
            if f.concept_id
            and f.source_type in {SourceType.TEXTBOOK, SourceType.PPT, SourceType.PAST_PAPER}
            and f.source_type != SourceType.SCANNED_PAGE
        )

        has_real_sources = real_source_concept_matched > 0
        results["real_source_concept_matched_count"] = real_source_concept_matched
        results["recommend_use_in_pdf"] = (
            len(results["issues"]) == 0
            and results["total_figures"] >= MIN_TOTAL_FIGURES
            and has_real_sources
        )

        self._results = results
        return results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_broken_images(self, figures: list[FigureObject], results: dict) -> int:
        count = 0
        for f in figures:
            path = Path(f.image_path)
            if not path.exists() or path.stat().st_size == 0:
                count += 1
                results["issues"].append(f"Broken image: {f.figure_id} at {f.image_path}")
        return count

    def _check_low_resolution(self, figures: list[FigureObject], results: dict) -> int:
        count = 0
        for f in figures:
            if f.width and f.height:
                if f.width < MIN_RESOLUTION_W or f.height < MIN_RESOLUTION_H:
                    count += 1
                    results["warnings"].append(
                        f"Low resolution: {f.figure_id} ({f.width}x{f.height})"
                    )
            if f.has_low_resolution_risk:
                if f.figure_id not in [w.split(":")[-1].strip() for w in results["warnings"]]:
                    count += 1
        return count

    def _check_scanned_pages(self, figures: list[FigureObject], results: dict) -> int:
        count = 0
        for f in figures:
            if f.source_type == SourceType.SCANNED_PAGE:
                count += 1
                results["warnings"].append(
                    f"Scanned page (not cropped figure): {f.figure_id}"
                )
            if f.metadata.get("needs_manual_crop"):
                if f.figure_id not in [w.split(":")[-1].strip() for w in results["warnings"]]:
                    count += 1
        return count

    def _check_concept_match(self, figures: list[FigureObject], results: dict) -> int:
        count = 0
        for f in figures:
            if not f.concept_id or f.concept_id not in ConceptId.ALL:
                count += 1
        if count > 0:
            results["warnings"].append(f"{count} figures have no concept match")
        return count

    def _check_duplicates(self, figures: list[FigureObject], results: dict) -> int:
        """Detect duplicate figures by image content hash."""
        seen: dict[str, list[str]] = {}
        for f in figures:
            path = Path(f.image_path)
            if not path.exists():
                continue
            try:
                h = hashlib.md5(path.read_bytes()).hexdigest()
            except Exception:
                continue
            seen.setdefault(h, []).append(f.figure_id)

        dup_count = sum(len(ids) - 1 for ids in seen.values() if len(ids) > 1)
        if dup_count > 0:
            results["warnings"].append(f"{dup_count} duplicate figures detected")
        return dup_count

    def _check_captions(self, figures: list[FigureObject], results: dict) -> int:
        count = sum(1 for f in figures if not f.caption)
        if count > 0:
            results["warnings"].append(f"{count} figures have no caption")
        return count

    def _check_spoofing(self, figures: list[FigureObject], results: dict) -> None:
        """Flag figures that might be pretending to be higher-quality sources."""
        for f in figures:
            if f.source_type == SourceType.TEXTBOOK and f.metadata.get("is_fallback"):
                results["issues"].append(
                    f"Source type spoofing: {f.figure_id} is marked textbook but is a fallback"
                )

    def _check_fallback_ratio(self, figures: list[FigureObject], results: dict) -> None:
        if results["total_figures"] == 0:
            return
        ratio = results["fallback_count"] / results["total_figures"]
        if ratio > MAX_FALLBACK_RATIO:
            results["warnings"].append(
                f"Fallback ratio {ratio:.0%} exceeds {MAX_FALLBACK_RATIO:.0%} threshold"
            )

    def _check_source_hits(self, results: dict) -> None:
        if results["textbook_figures"] == 0 and results["ppt_figures"] == 0 and results["past_paper_figures"] == 0:
            results["issues"].append(
                "当前资料未命中高质量原图（无教材/PPT/真题图），已使用 fallback 重绘图。"
            )

    def _check_figure_count(self, results: dict) -> None:
        if results["total_figures"] < MIN_TOTAL_FIGURES:
            results["warnings"].append(
                f"Figure count ({results['total_figures']}) below minimum ({MIN_TOTAL_FIGURES})"
            )

    def get_results(self) -> dict[str, Any]:
        return self._results
