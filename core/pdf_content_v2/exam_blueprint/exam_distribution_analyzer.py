"""Analyze real exam patterns from uploaded past papers."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.pdf_content_v2.exam_blueprint.exam_blueprint import BlueprintSource


@dataclass
class ExamDistributionReport:
    detected_exam_count: int = 0
    section_distribution: dict[str, Any] = field(default_factory=dict)
    score_distribution: dict[str, Any] = field(default_factory=dict)
    concept_distribution: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "detected_exam_count": self.detected_exam_count,
            "section_distribution": self.section_distribution,
            "score_distribution": self.score_distribution,
            "concept_distribution": self.concept_distribution,
            "confidence": self.confidence,
        }


class ExamDistributionAnalyzer:
    """Analyze past exam papers to extract blueprint statistics.

    Priority:
        1. Past exam stats (confidence ≥ 0.7 → use it)
        2. Local course profile
        3. Default blueprint
        4. AI estimated (must be labeled)
    """

    def __init__(self, data_dir: str = "data/exam_patterns"):
        self.data_dir = Path(data_dir)
        self.source: BlueprintSource = BlueprintSource.DEFAULT_PROFILE
        self.confidence: float = 0.0

    def analyze(self, course_id: str = "probability_ch2") -> ExamDistributionReport:
        """Scan for exam pattern data and compute distribution."""
        report = ExamDistributionReport()

        # Look for past exam files
        pattern_dir = self.data_dir / "engineering" / "electromagnetic_static_chapter1"
        if course_id == "probability_ch2":
            # Check for probability-specific pattern data
            prob_dir = self.data_dir / "math" / "probability_random_var_ch2"
            if prob_dir.exists():
                pattern_dir = prob_dir

        pattern_file = pattern_dir / "patterns.json" if pattern_dir.exists() else None

        if pattern_file and pattern_file.exists():
            try:
                patterns = json.loads(pattern_file.read_text(encoding="utf-8"))
                report.detected_exam_count = len(patterns)
                report.confidence = self._compute_confidence(patterns, report)

                if report.confidence >= 0.7:
                    self.source = BlueprintSource.PAST_EXAM_STATS
                    self.confidence = report.confidence
                    report.section_distribution = self._count_sections(patterns)
                    report.score_distribution = self._count_scores(patterns)
                    report.concept_distribution = self._count_concepts(patterns)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        if report.confidence < 0.7:
            self.source = BlueprintSource.DEFAULT_PROFILE
            self.confidence = 0.5

        return report

    def _compute_confidence(self, patterns: list, report: ExamDistributionReport) -> float:
        """Compute confidence based on data quality."""
        if not patterns:
            return 0.0
        # More patterns → higher confidence
        count_score = min(1.0, len(patterns) / 5)
        # Each pattern should have expected fields
        field_score = sum(
            1 for p in patterns
            if p.get("type") and p.get("concept_ids") and p.get("score_weight")
        ) / max(1, len(patterns))
        return 0.4 * count_score + 0.6 * field_score

    def _count_sections(self, patterns: list) -> dict:
        counter = Counter(p.get("type", "未知") for p in patterns)
        return dict(counter)

    def _count_scores(self, patterns: list) -> dict:
        weights = Counter(p.get("score_weight", "中") for p in patterns)
        return dict(weights)

    def _count_concepts(self, patterns: list) -> dict:
        all_concepts: list[str] = []
        for p in patterns:
            all_concepts.extend(p.get("concept_ids", []))
        counter = Counter(all_concepts)
        total = max(1, sum(counter.values()))
        return {k: round(v / total, 3) for k, v in counter.most_common(10)}

    def get_source_label(self) -> str:
        labels = {
            BlueprintSource.PAST_EXAM_STATS: "用户上传真题统计",
            BlueprintSource.LOCAL_COURSE_PROFILE: "课程本地蓝图",
            BlueprintSource.DEFAULT_PROFILE: "课程默认蓝图",
            BlueprintSource.AI_ESTIMATED: "⚠️ AI 估计蓝图（非真题统计）",
        }
        return labels.get(self.source, "未知来源")

    def should_use_blueprint(self) -> tuple[BlueprintSource, float]:
        """Returns (source, confidence) for blueprint selection."""
        return self.source, self.confidence
