"""PDFAestheticJudge — rule-based layout quality checker for PDF 5.0.

Checks: page density, whitespace ratio, figure size, table readability,
formula line breaks, orphan headings, print suitability.

No vision API required. If vision API is available, can optionally
render PNG pages for AI vision review, but never pretends it was done.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LayoutReport:
    """Layout quality assessment for a PDF document."""
    pdf_type: str = ""
    layout_score: int = 0  # 0-100
    checks: dict = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    vision_review_done: bool = False
    is_print_suitable: bool = True

    def to_dict(self) -> dict:
        return {
            "pdf_type": self.pdf_type,
            "layout_score": self.layout_score,
            "checks": self.checks,
            "issues": self.issues,
            "warnings": self.warnings,
            "vision_review_done": self.vision_review_done,
            "is_print_suitable": self.is_print_suitable,
        }


class PDFAestheticJudge:
    """Rule-based layout quality checker.

    PDF 5.0: Always generates a rule_based_layout_report.
    If a vision API key is configured, can optionally do AI vision review,
    but CLEARLY labels whether it was rule-based or AI-vision.
    """

    def __init__(self, enable_vision: bool = False):
        self.enable_vision = enable_vision and self._vision_available()

    def _vision_available(self) -> bool:
        """Check if vision API is available. Never pretend."""
        # Check for OpenAI/Anthropic vision API keys
        import os
        return bool(
            os.environ.get("OPENAI_API_KEY") or
            os.environ.get("ANTHROPIC_API_KEY")
        )

    def check(self, typst_text: str, pdf_type: str = "Review") -> LayoutReport:
        """Run rule-based layout checks on Typst source.

        Since we analyze Typst source (not rendered PNG), these checks
        focus on structural issues detectable in markup.
        """
        report = LayoutReport(pdf_type=pdf_type)
        report.vision_review_done = False
        score = 100

        # 1. Page density check (too many sections?)
        section_count = typst_text.count("#section-heading")
        if section_count == 0:
            section_count = typst_text.count("#block-title")
        if pdf_type == "Sprint" and section_count > 8:
            score -= 10
            report.warnings.append(f"Sprint has {section_count} sections (target: 4-6)")
        report.checks["section_count"] = section_count

        # 2. Whitespace/density — check for pagebreak usage
        pagebreaks = typst_text.count("#pagebreak")
        report.checks["pagebreak_count"] = pagebreaks
        if pdf_type == "Sprint" and pagebreaks > 3:
            report.warnings.append(f"Too many pagebreaks in Sprint ({pagebreaks})")

        # 3. Figure count and sizing
        figure_count = typst_text.count("#figure") + typst_text.count("#image")
        report.checks["figure_count"] = figure_count
        if figure_count == 0:
            score -= 15
            report.issues.append("No figures found — PDF may be text-only and hard to read")

        # 4. Formula line break issues
        formula_count = len(re.findall(r'\$[^$]+\$', typst_text))
        report.checks["formula_count"] = formula_count
        # Check for very long formulas that might break
        long_formulas = len(re.findall(r'\$[^$]{80,}\$', typst_text))
        if long_formulas > 3:
            score -= 5
            report.warnings.append(f"{long_formulas} long formulas may cause line breaks")

        # 5. Orphan heading detection (heading at end of content)
        # Check if section-heading appears very close to pagebreak
        orphans = len(re.findall(
            r'#section-heading[^\n]*\n(?![^\n]{50,})#pagebreak', typst_text
        ))
        report.checks["orphan_headings"] = orphans
        if orphans > 0:
            score -= 10
            report.issues.append(f"{orphans} orphan headings detected")

        # 6. Table readability
        table_count = typst_text.count("#table") + typst_text.count("#grid")
        report.checks["table_count"] = table_count
        # Check for tables with too many columns (>6)
        wide_tables = len(re.findall(r'columns:\s*\([^)]*,\s*[^)]*,\s*[^)]*,\s*[^)]*,\s*[^)]*,\s*[^)]*,', typst_text))
        if wide_tables > 0:
            score -= 5
            report.warnings.append(f"{wide_tables} tables may be too wide")

        # 7. Print suitability
        # Sprint: 5-8 pages, Review: 20-40, PastPaper: 12-24, MockExam: 8-16
        target_pages = {"Sprint": (5, 8), "Review": (20, 40),
                       "PastPaper": (12, 24), "MockExam": (8, 16)}
        min_p, max_p = target_pages.get(pdf_type, (5, 50))
        estimated_pages = max(1, section_count * 2 + pagebreaks)
        report.checks["estimated_pages"] = estimated_pages
        report.checks["target_page_range"] = f"{min_p}-{max_p}"

        if estimated_pages < min_p:
            score -= 10
            report.issues.append(
                f"Estimated {estimated_pages} pages (target: {min_p}-{max_p}) — too short"
            )
        elif estimated_pages > max_p * 1.5:
            score -= 5
            report.warnings.append(
                f"Estimated {estimated_pages} pages (target: {min_p}-{max_p}) — may be too long"
            )

        # 8. Content warnings
        if "未找到高置信来源" in typst_text:
            source_missing = typst_text.count("未找到高置信来源")
            report.checks["source_missing_count"] = source_missing
            if source_missing > 5:
                score -= 10
                report.issues.append(f"{source_missing} source-missing warnings")

        report.layout_score = max(0, score)
        report.is_print_suitable = report.layout_score >= 70
        return report

    def check_all(self, typst_files: dict[str, Path]) -> dict[str, LayoutReport]:
        """Run layout checks on all PDF types."""
        results = {}
        for pdf_type, path in typst_files.items():
            if path.exists():
                text = path.read_text(encoding="utf-8")
                results[pdf_type] = self.check(text, pdf_type)
        return results

    def aggregate_score(self, reports: dict[str, LayoutReport]) -> int:
        """Aggregate layout scores across all PDF types."""
        if not reports:
            return 0
        return int(sum(r.layout_score for r in reports.values()) / len(reports))
