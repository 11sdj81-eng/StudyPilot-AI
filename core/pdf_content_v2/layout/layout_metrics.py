"""PageLayoutMetrics — per-page layout measurements."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PageLayoutMetrics:
    page_number: int
    content_density: float = 0.0       # 0–1, fraction of page covered by text/images
    text_block_count: int = 0
    image_count: int = 0
    table_count: int = 0
    formula_count: int = 0              # estimated from math blocks
    overlap_count: int = 0             # text-image bbox overlaps
    blank_area_ratio: float = 0.0      # fraction of page that's empty
    overcrowded_score: float = 0.0     # 0–1, higher = more crowded
    orphan_heading: bool = False       # heading at bottom with no body
    issue_codes: list[str] = field(default_factory=list)

    def has_issues(self) -> bool:
        return len(self.issue_codes) > 0

    def critical_issues(self) -> list[str]:
        return [c for c in self.issue_codes if c.startswith("CRITICAL")]

    def warning_issues(self) -> list[str]:
        return [c for c in self.issue_codes if c.startswith("WARNING")]

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number, "content_density": round(self.content_density, 3),
            "text_block_count": self.text_block_count, "image_count": self.image_count,
            "table_count": self.table_count, "formula_count": self.formula_count,
            "overlap_count": self.overlap_count, "blank_area_ratio": round(self.blank_area_ratio, 3),
            "overcrowded_score": round(self.overcrowded_score, 3),
            "orphan_heading": self.orphan_heading, "issue_codes": self.issue_codes,
        }
