"""Map DocumentBlocks into FigureBank v2 compatible objects."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence_v5.document_blocks import DocumentParseResult


def build_figure_bank_v2(results: list[DocumentParseResult], output_dir: str | Path = "data/figure_bank/v2") -> dict:
    figures = []
    for result in results:
        for fig in result.figures:
            figures.append(
                {
                    "figure_id": fig.block_id,
                    "source_file": Path(result.file_path).name,
                    "page_number": fig.page_number,
                    "parser_name": result.parser_name,
                    "layout_region_type": fig.block_type,
                    "caption_block_id": "",
                    "nearby_text": _nearby_text(result, fig.page_number),
                    "formula_refs": [],
                    "question_refs": [],
                    "document_block_id": fig.block_id,
                    "image_path": fig.image_path,
                    "confidence": fig.confidence,
                    "full_page_scan_risk": fig.metadata.get("full_page_risk", False),
                }
            )
    return {
        "figure_count": len(figures),
        "usable_precise_crop_count": sum(1 for f in figures if f["image_path"] and not f["full_page_scan_risk"]),
        "full_page_scan_risk_count": sum(1 for f in figures if f["full_page_scan_risk"]),
        "figures": figures,
    }


def _nearby_text(result: DocumentParseResult, page_number: int) -> str:
    for page in result.pages:
        if page.page_number == page_number:
            return page.text[:500]
    return ""
