"""LayoutValidator — PyMuPDF-based PDF layout quality analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz

from core.pdf_content_v2.layout.layout_metrics import PageLayoutMetrics
from core.pdf_content_v2.layout.layout_thresholds import (
    PDFTypeThresholds, get_thresholds,
)


@dataclass
class LayoutReport:
    pdf_path: str = ""
    pdf_type: str = ""
    page_count: int = 0
    layout_issue_count: int = 0
    critical_layout_issue_count: int = 0
    warning_layout_issue_count: int = 0
    blank_page_risk_count: int = 0
    overcrowded_page_count: int = 0
    text_image_overlap_count: int = 0
    formula_overflow_count: int = 0
    table_overflow_count: int = 0
    orphan_heading_count: int = 0
    separated_solution_count: int = 0
    footer_overlap_count: int = 0
    pages: list[dict] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "pdf_path": self.pdf_path, "pdf_type": self.pdf_type,
            "page_count": self.page_count, "layout_issue_count": self.layout_issue_count,
            "critical_layout_issue_count": self.critical_layout_issue_count,
            "warning_layout_issue_count": self.warning_layout_issue_count,
            "blank_page_risk_count": self.blank_page_risk_count,
            "overcrowded_page_count": self.overcrowded_page_count,
            "text_image_overlap_count": self.text_image_overlap_count,
            "formula_overflow_count": self.formula_overflow_count,
            "table_overflow_count": self.table_overflow_count,
            "orphan_heading_count": self.orphan_heading_count,
            "separated_solution_count": self.separated_solution_count,
            "footer_overlap_count": self.footer_overlap_count,
            "pages": self.pages, "passed": self.passed,
        }


class LayoutValidator:
    """Analyze PDF layout using PyMuPDF text/image block extraction."""

    FOOTER_ZONE = 50   # bottom 50pt = footer zone
    ORPHAN_ZONE = 0.85  # heading below 85% of page height

    def validate(self, pdf_path: str | Path, pdf_type: str = "Review") -> LayoutReport:
        """Run full layout analysis on a PDF."""
        path = Path(pdf_path)
        report = LayoutReport(pdf_path=str(path), pdf_type=pdf_type)
        thresholds = get_thresholds(pdf_type)

        if not path.exists():
            report.critical_layout_issue_count = 1
            report.pages = [{"error": "PDF not found"}]
            return report

        try:
            doc = fitz.open(path)
        except Exception:
            report.critical_layout_issue_count = 1
            report.pages = [{"error": "Cannot open PDF"}]
            return report

        report.page_count = len(doc)
        metrics_list: list[PageLayoutMetrics] = []

        for i, page in enumerate(doc):
            metrics = self._analyze_page(page, i + 1, thresholds, report.page_count)
            metrics_list.append(metrics)
            report.pages.append(metrics.to_dict())

            # Aggregate counts
            for code in metrics.issue_codes:
                report.layout_issue_count += 1
                if code.startswith("CRITICAL"):
                    report.critical_layout_issue_count += 1
                elif code.startswith("WARNING"):
                    report.warning_layout_issue_count += 1

                if "blank_page" in code:
                    report.blank_page_risk_count += 1
                if "overcrowded" in code:
                    report.overcrowded_page_count += 1
                if "overlap" in code:
                    report.text_image_overlap_count += 1
                if "formula_overflow" in code:
                    report.formula_overflow_count += 1
                if "table_overflow" in code:
                    report.table_overflow_count += 1
                if "orphan_heading" in code:
                    report.orphan_heading_count += 1
                if "footer_overlap" in code:
                    report.footer_overlap_count += 1

        # Cross-page checks
        sep = self._check_separated_solutions(metrics_list, thresholds)
        report.separated_solution_count = sep

        doc.close()

        report.passed = report.critical_layout_issue_count == 0
        return report

    def _analyze_page(self, page: fitz.Page, page_num: int,
                       thresholds: PDFTypeThresholds, total_pages: int) -> PageLayoutMetrics:
        """Analyze a single PDF page."""
        m = PageLayoutMetrics(page_number=page_num)
        rect = page.rect
        page_area = abs(rect.width * rect.height)

        # ── Extract text blocks ──
        text_blocks = page.get_text("blocks")
        # Filter out empty/image blocks
        text_blocks = [b for b in text_blocks if b[6] == 0 and b[4].strip()]  # type 0 = text
        m.text_block_count = len(text_blocks)

        # ── Extract image blocks ──
        image_blocks = [b for b in page.get_text("blocks") if b[6] == 1]  # type 1 = image
        m.image_count = len(image_blocks)

        # ── Content density ──
        content_area = 0.0
        for b in text_blocks:
            content_area += abs((b[2] - b[0]) * (b[3] - b[1]))
        for b in image_blocks:
            content_area += abs((b[2] - b[0]) * (b[3] - b[1]))
        m.content_density = min(1.0, content_area / max(1, page_area))
        m.blank_area_ratio = 1.0 - m.content_density

        # ── Formula/table estimation ──
        all_text = " ".join(b[4] for b in text_blocks)
        m.formula_count = len(re.findall(r'\$[^$]+\$', all_text))  # inline math
        m.table_count = all_text.count("│") // 3  # rough table detection

        # ── Check against thresholds ──
        # 1. Blank page risk
        if m.content_density < thresholds.min_content_density and page_num > 1:
            m.issue_codes.append("WARNING_blank_page_risk")
            m.blank_area_ratio = max(m.blank_area_ratio, 1.0 - m.content_density)

        # 2. Overcrowded
        if m.content_density > thresholds.max_content_density:
            m.issue_codes.append("WARNING_overcrowded_page")
            m.overcrowded_score = (m.content_density - thresholds.max_content_density) / (1.0 - thresholds.max_content_density)

        # 3. Text-image overlap detection
        overlaps = self._detect_overlaps(text_blocks, image_blocks)
        m.overlap_count = overlaps
        if overlaps > thresholds.max_overlaps:
            m.issue_codes.append("CRITICAL_text_image_overlap" if overlaps > 1 else "WARNING_text_image_overlap")

        # 4. Formula overflow (heuristic: very long lines with math)
        for b in text_blocks:
            text = b[4]
            if len(text) > 200 and "$" in text:
                m.issue_codes.append("WARNING_formula_overflow")
                break

        # 5. Orphan heading detection
        if thresholds.check_orphan_headings:
            if self._detect_orphan(text_blocks, rect.height, page_num, total_pages):
                m.orphan_heading = True
                m.issue_codes.append("WARNING_orphan_heading")

        # 6. Footer overlap
        if self._detect_footer_overlap(text_blocks, rect.height):
            m.issue_codes.append("WARNING_footer_overlap")

        return m

    def _detect_overlaps(self, text_blocks: list, image_blocks: list) -> int:
        """Count text-image bbox overlaps."""
        overlaps = 0
        for tb in text_blocks:
            tx0, ty0, tx1, ty1 = tb[:4]
            for ib in image_blocks:
                ix0, iy0, ix1, iy1 = ib[:4]
                if _boxes_overlap((tx0, ty0, tx1, ty1), (ix0, iy0, ix1, iy1)):
                    overlaps += 1
        return overlaps

    def _check_separated_solutions(self, pages: list[PageLayoutMetrics],
                                     thresholds: PDFTypeThresholds) -> int:
        """Check if answers are too far from their questions."""
        if not thresholds.check_separated_solutions:
            return 0
        # Heuristic: if "答案" or "评分点" appears only on the last page
        # and the question count is high, solutions may be separated
        return 0  # requires cross-page text analysis; placeholder


    def _detect_orphan(self, blocks: list, page_h: float, page_num: int, total: int) -> bool:
        """Detect orphan headings (heading near bottom, no body text after)."""
        if page_num >= total:
            return False
        if not blocks:
            return False
        last_block = max(blocks, key=lambda b: b[3])
        last_y = last_block[3]
        if last_y > page_h * self.ORPHAN_ZONE:
            text = last_block[4].strip()
            if len(text) < 80:
                return True
        return False

    def _detect_footer_overlap(self, blocks: list, page_h: float) -> bool:
        """Check if content overlaps with footer zone."""
        footer_y = page_h - self.FOOTER_ZONE
        for b in blocks:
            if b[1] < footer_y < b[3]:
                return True
        return False


def _boxes_overlap(b1: tuple, b2: tuple) -> bool:
    """Check if two bounding boxes overlap."""
    x0_1, y0_1, x1_1, y1_1 = b1
    x0_2, y0_2, x1_2, y1_2 = b2
    return not (x1_1 < x0_2 or x0_1 > x1_2 or y1_1 < y0_2 or y0_1 > y1_2)
