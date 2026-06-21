"""Layout thresholds — different standards per PDF type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PDFTypeThresholds:
    pdf_type: str              # Sprint / Review / PastPaper / MockExam
    min_content_density: float = 0.15
    max_content_density: float = 0.85
    max_blank_area: float = 0.50       # max acceptable blank fraction
    max_overlaps: int = 0
    max_formula_overflow: int = 2
    max_table_overflow: int = 0
    min_text_blocks: int = 2           # at least some content on every page
    check_orphan_headings: bool = True
    check_separated_solutions: bool = True
    # Sprint: denser is okay; Review: must be comfortable; PastPaper/MockExam: moderate


class LayoutThresholds:
    """Per-PDF-type layout thresholds."""

    THRESHOLDS: dict[str, PDFTypeThresholds] = {
        "Sprint": PDFTypeThresholds(
            pdf_type="Sprint", min_content_density=0.10, max_content_density=0.92,
            max_blank_area=0.55, max_overlaps=1, check_separated_solutions=False,
        ),
        "Review": PDFTypeThresholds(
            pdf_type="Review", min_content_density=0.12, max_content_density=0.85,
            max_blank_area=0.45, max_overlaps=0, check_orphan_headings=True,
        ),
        "PastPaper": PDFTypeThresholds(
            pdf_type="PastPaper", min_content_density=0.12, max_content_density=0.88,
            max_blank_area=0.45, max_overlaps=0, check_separated_solutions=True,
        ),
        "MockExam": PDFTypeThresholds(
            pdf_type="MockExam", min_content_density=0.10, max_content_density=0.90,
            max_blank_area=0.55, max_overlaps=1, check_separated_solutions=True,
        ),
    }

    @classmethod
    def get(cls, pdf_type: str) -> PDFTypeThresholds:
        return cls.THRESHOLDS.get(pdf_type, cls.THRESHOLDS["Review"])


def get_thresholds(pdf_type: str) -> PDFTypeThresholds:
    return LayoutThresholds.get(pdf_type)
