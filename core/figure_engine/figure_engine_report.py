"""FigureEngineReport —— Generate comprehensive reports for the Figure Engine.

Produces:
- figure_extraction_report.json
- figure_match_report.json
- figure_quality_report.json
- review_queue.json
- figure_engine_demo_report.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.figure_engine.figure_objects import FigureObject, SourceType, ConceptId
from core.figure_engine.figure_quality_gate import FigureQualityGate


REPORTS_DIR = Path("data/figure_bank/_reports")
REVIEW_QUEUE_PATH = Path("data/figure_bank/review_queue.json")


class FigureEngineReport:
    """Generate all Figure Engine reports."""

    def __init__(self, reports_dir: str | Path = REPORTS_DIR):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(
        self,
        figures: list[FigureObject],
        extraction_summary: dict[str, Any] | None = None,
        match_log: list[dict[str, Any]] | None = None,
        fallback_log: list[dict[str, Any]] | None = None,
        extraction_report: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Generate all reports and return a mapping of report name -> file path."""
        paths: dict[str, str] = {}

        # 1. Extraction report
        ext_path = self.reports_dir / "figure_extraction_report.json"
        self._write_report(ext_path, self._build_extraction_report(figures, extraction_report))
        paths["extraction_report"] = str(ext_path.resolve())

        # 2. Match report
        match_path = self.reports_dir / "figure_match_report.json"
        self._write_report(match_path, self._build_match_report(figures, match_log or []))
        paths["match_report"] = str(match_path.resolve())

        # 3. Quality report
        quality_path = self.reports_dir / "figure_quality_report.json"
        gate = FigureQualityGate()
        quality_results = gate.check(figures)
        self._write_report(quality_path, quality_results)
        paths["quality_report"] = str(quality_path.resolve())

        # 4. Review queue
        review_path = REVIEW_QUEUE_PATH
        self._write_report(review_path, self._build_review_queue(figures, quality_results))
        paths["review_queue"] = str(review_path.resolve())

        # 5. Demo report
        demo_path = self.reports_dir / "figure_engine_demo_report.json"
        self._write_report(demo_path, self._build_demo_report(
            figures, extraction_summary, quality_results, fallback_log
        ))
        paths["demo_report"] = str(demo_path.resolve())

        return paths

    # ------------------------------------------------------------------
    # Report builders
    # ------------------------------------------------------------------

    def _build_extraction_report(
        self,
        figures: list[FigureObject],
        extraction_report: dict[str, Any] | None,
    ) -> dict[str, Any]:
        by_source = self._count_by_source_type(figures)
        return {
            "report_type": "figure_extraction_report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_extracted": len(figures),
            "by_source_type": by_source,
            "scanned_pages": by_source.get(SourceType.SCANNED_PAGE, 0),
            "extraction_details": extraction_report or {},
            "figure_summary": [
                {
                    "figure_id": f.figure_id,
                    "source_type": f.source_type,
                    "source_file": f.source_file,
                    "source_page": f.source_page,
                    "width": f.width,
                    "height": f.height,
                    "concept_id": f.concept_id,
                }
                for f in figures
            ],
        }

    def _build_match_report(
        self,
        figures: list[FigureObject],
        match_log: list[dict[str, Any]],
    ) -> dict[str, Any]:
        by_concept = self._count_by_concept(figures)
        return {
            "report_type": "figure_match_report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_matched": sum(1 for f in figures if f.concept_id),
            "total_unmatched": sum(1 for f in figures if not f.concept_id),
            "by_concept": by_concept,
            "match_statistics": {
                "mean_match_score": self._mean([f.match_score for f in figures]),
                "mean_final_score": self._mean([f.final_score for f in figures]),
            },
            "match_log": match_log,
        }

    def _build_review_queue(
        self,
        figures: list[FigureObject],
        quality_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a human-review checklist for low-confidence figures."""
        queue: list[dict[str, Any]] = []

        for f in figures:
            needs_review = False
            reasons: list[str] = []

            # Low confidence
            if f.final_score < 20.0:
                needs_review = True
                reasons.append(f"low_final_score ({f.final_score:.1f})")

            # Scanned page
            if f.source_type == SourceType.SCANNED_PAGE:
                needs_review = True
                reasons.append("scanned_page_needs_crop")

            # Unmatched
            if not f.concept_id:
                needs_review = True
                reasons.append("no_concept_match")

            # Needs manual crop
            if f.metadata.get("needs_manual_crop"):
                needs_review = True
                reasons.append("needs_manual_crop")

            # Potential duplicate
            if f.metadata.get("possible_duplicate"):
                needs_review = True
                reasons.append("possible_duplicate")

            if needs_review:
                queue.append({
                    "figure_id": f.figure_id,
                    "source_type": f.source_type,
                    "source_file": f.source_file,
                    "source_page": f.source_page,
                    "image_path": f.image_path,
                    "concept_id": f.concept_id,
                    "final_score": f.final_score,
                    "reasons": reasons,
                    "action_suggested": self._suggest_action(reasons),
                })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_in_queue": len(queue),
            "description": "人工审核清单：低置信图、扫描页图、未匹配概念图、需人工裁剪图、可疑重复图。",
            "items": queue,
        }

    def _build_demo_report(
        self,
        figures: list[FigureObject],
        extraction_summary: dict[str, Any] | None,
        quality_results: dict[str, Any],
        fallback_log: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Build a comprehensive demo/summary report."""
        by_concept = self._count_by_concept(figures)
        by_source = self._count_by_source_type(figures)

        # Per-concept coverage
        concept_coverage: dict[str, dict[str, Any]] = {}
        for cid in ConceptId.ALL:
            figures_for_concept = [f for f in figures if f.concept_id == cid]
            has_high_quality = any(
                f.source_type in (SourceType.TEXTBOOK, SourceType.PPT, SourceType.PAST_PAPER)
                for f in figures_for_concept
            )
            concept_coverage[cid] = {
                "label": ConceptId.LABELS.get(cid, cid),
                "total_figures": len(figures_for_concept),
                "has_high_quality_source": has_high_quality,
                "source_types": list(set(f.source_type for f in figures_for_concept)),
                "best_score": max((f.final_score for f in figures_for_concept), default=0.0),
            }

        return {
            "report_type": "figure_engine_demo_report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "figure_engine_version": "1.0",
            "summary": {
                "total_figures": len(figures),
                "by_source_type": by_source,
                "by_concept": by_concept,
                "concept_coverage": concept_coverage,
                "has_real_source_figures": (
                    by_source.get(SourceType.TEXTBOOK, 0) > 0
                    or by_source.get(SourceType.PPT, 0) > 0
                    or by_source.get(SourceType.PAST_PAPER, 0) > 0
                ),
                "quality_gate": {
                    "passed": quality_results.get("recommend_use_in_pdf", False),
                    "total_issues": len(quality_results.get("issues", [])),
                    "total_warnings": len(quality_results.get("warnings", [])),
                },
                "fallback_count": len(fallback_log or []),
            },
            "extraction_summary": extraction_summary or {},
            "quality_issues": quality_results.get("issues", []),
            "quality_warnings": quality_results.get("warnings", []),
            "fallback_log": fallback_log or [],
            "concept_high_quality_status": {
                cid: concept_coverage[cid]["has_high_quality_source"]
                for cid in concept_coverage
            },
            "recommendation": self._build_recommendation(quality_results, by_source, by_concept),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_by_source_type(self, figures: list[FigureObject]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in figures:
            counts[f.source_type] = counts.get(f.source_type, 0) + 1
        return counts

    def _count_by_concept(self, figures: list[FigureObject]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in figures:
            cid = f.concept_id or "unmatched"
            counts[cid] = counts.get(cid, 0) + 1
        return counts

    def _mean(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def _suggest_action(self, reasons: list[str]) -> str:
        if "scanned_page_needs_crop" in reasons:
            return "建议使用 MinerU / Marker 对扫描页进行区域检测和裁剪，或人工用截图工具裁剪。"
        if "no_concept_match" in reasons:
            return "建议人工标注概念，或在 metadata 中补充 OCR 文本。"
        if "low_final_score" in reasons:
            return "质量分低，建议人工检查图像清晰度和内容匹配度。"
        if "needs_manual_crop" in reasons:
            return "需人工裁剪。"
        return "建议人工审核。"

    def _build_recommendation(
        self,
        quality: dict[str, Any],
        by_source: dict[str, int],
        by_concept: dict[str, int],
    ) -> str:
        """Generate an honest recommendation."""
        textbook = by_source.get(SourceType.TEXTBOOK, 0)
        ppt = by_source.get(SourceType.PPT, 0)
        past_paper = by_source.get(SourceType.PAST_PAPER, 0)
        real_source_concept_matched = quality.get("real_source_concept_matched_count", 0)

        if real_source_concept_matched == 0:
            return (
                "当前资料未命中高质量原图（教材/PPT/真题中无概念匹配的插图）。"
                "原因：(1) 教材PDF是扫描版，无法自动提取嵌入图片，所有页面均被识别为整页扫描图；"
                "(2) 期末试卷PDF也是扫描版；"
                "(3) 项目中没有PPTX文件。"
                "建议：(a) 使用 MinerU 或 Marker 对扫描PDF进行区域检测和图表裁剪；"
                "(b) 人工从教材中截图关键插图并放入 figure_bank；"
                "(c) 继续使用现有 v4 程序化 SVG 图作为 fallback。"
            )
        return "已有高质量原图命中，建议逐步替换程序化 SVG 图为 FigureBank 选图。"

    def _write_report(self, path: Path, data: dict[str, Any]) -> None:
        """Write a JSON report to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
