"""FigureRanker —— Score figures across multiple quality dimensions.

Scoring dimensions:
1. source_type weight
2. clarity (resolution, not full-page scan, no noise)
3. match quality (concept keyword hits, OCR/text hits)
4. usability (aspect ratio, resolution risk, text overlap)
"""

from __future__ import annotations

from core.figure_engine.figure_objects import FigureObject, SourceType


# Source type base weights
SOURCE_TYPE_WEIGHTS: dict[str, float] = {
    SourceType.TEXTBOOK: 30.0,
    SourceType.PPT: 25.0,
    SourceType.PAST_PAPER: 25.0,
    SourceType.NOTE: 10.0,
    SourceType.REDRAW: 15.0,
    SourceType.PROGRAMMATIC: 8.0,
    SourceType.AI_GENERATED: 3.0,
    SourceType.UNKNOWN: 0.0,
    SourceType.SCANNED_PAGE: -5.0,  # penalty for full-page scans
}

# Clarity sub-scores
CLARITY_MIN_RESOLUTION_W = 400
CLARITY_MIN_RESOLUTION_H = 300
CLARITY_RESOLUTION_OK = 10.0
CLARITY_NOT_FULL_PAGE = 10.0
CLARITY_NO_NOISE = 10.0

# Match sub-scores
MATCH_KEYWORD_HIT_MULTIPLIER = 20.0  # multiplied by match_score as computed by matcher
MATCH_TEXT_HIT_MULTIPLIER = 15.0

# Usability sub-scores
USABILITY_ASPECT_RATIO_OK = 10.0
USABILITY_NO_LOW_RES_RISK = 10.0
USABILITY_NO_TEXT_OVERLAP = 10.0

# Penalties
FULL_PAGE_PENALTY = -15.0
LOW_RES_PENALTY = -10.0
NOISE_PENALTY = -5.0


class FigureRanker:
    """Score figures on quality, match, and usability dimensions."""

    def __init__(self):
        self._scores_log: list[dict] = []

    def rank_figure(self, figure: FigureObject) -> FigureObject:
        """Compute quality_score, match_score, and usability_score for a figure."""
        figure.quality_score = self._compute_quality(figure)
        # match_score is blended: what the matcher assigned + bonus from text analysis
        figure.match_score = self._compute_match(figure)
        figure.usability_score = self._compute_usability(figure)

        self._scores_log.append({
            "figure_id": figure.figure_id,
            "source_type": figure.source_type,
            "quality_score": figure.quality_score,
            "match_score": figure.match_score,
            "usability_score": figure.usability_score,
            "final_score": figure.final_score,
        })

        return figure

    def rank_all(self, figures: list[FigureObject]) -> list[FigureObject]:
        """Rank all figures."""
        self._scores_log = []
        return [self.rank_figure(f) for f in figures]

    def _compute_quality(self, f: FigureObject) -> float:
        """Compute quality_score based on source type and clarity."""
        score = 0.0

        # Source type weight
        score += SOURCE_TYPE_WEIGHTS.get(f.source_type, 0.0)

        # Clarity: resolution
        if f.width and f.height:
            if f.width >= CLARITY_MIN_RESOLUTION_W and f.height >= CLARITY_MIN_RESOLUTION_H:
                score += CLARITY_RESOLUTION_OK
            else:
                score += CLARITY_RESOLUTION_OK * 0.3  # partial credit

        # Clarity: not full-page scan
        if not f.metadata.get("is_full_page") and not f.metadata.get("is_full_page_scan"):
            score += CLARITY_NOT_FULL_PAGE
        else:
            score += FULL_PAGE_PENALTY

        # Clarity: no noise
        if not f.has_noise_risk:
            score += CLARITY_NO_NOISE
        else:
            score += NOISE_PENALTY

        # Low resolution penalty
        if f.has_low_resolution_risk:
            score += LOW_RES_PENALTY

        return round(max(score, -35.0), 2)

    def _compute_match(self, f: FigureObject) -> float:
        """Compute match_score — blend of matcher score and text analysis."""
        score = 0.0

        # Base: what the matcher assigned (0-1 range) scaled
        score += f.match_score * MATCH_KEYWORD_HIT_MULTIPLIER

        # OCR / nearby text bonus
        if f.ocr_text or f.caption or f.metadata.get("slide_title"):
            score += MATCH_TEXT_HIT_MULTIPLIER * 0.5  # conservative: we don't parse OCR yet

        return round(min(score, 35.0), 2)

    def _compute_usability(self, f: FigureObject) -> float:
        """Compute usability_score — how suitable for PDF insertion."""
        score = 0.0

        # Aspect ratio: moderate ratios are best for PDF
        if f.aspect_ratio:
            if 0.5 <= f.aspect_ratio <= 2.0:
                score += USABILITY_ASPECT_RATIO_OK
            elif 0.3 <= f.aspect_ratio <= 3.0:
                score += USABILITY_ASPECT_RATIO_OK * 0.5

        # No low resolution risk
        if not f.has_low_resolution_risk:
            score += USABILITY_NO_LOW_RES_RISK
        else:
            score += LOW_RES_PENALTY

        # No text overlap risk (text mixed with image)
        if not f.has_text_overlap_risk:
            score += USABILITY_NO_TEXT_OVERLAP
        else:
            score += -10.0

        return round(max(score, -25.0), 2)

    def get_scores_log(self) -> list[dict]:
        return self._scores_log
