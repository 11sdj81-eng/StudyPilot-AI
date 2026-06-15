"""Build structured chunk report from DocumentBlocks."""

from __future__ import annotations

import json
from pathlib import Path

from core.document_intelligence_v5.document_blocks import DocumentParseResult


def build_rag_v5_report(results: list[DocumentParseResult], output_path: str | Path = "data/outputs/v5_reports/rag_v5_report.json") -> dict:
    chunks = []
    for result in results:
        for page in result.pages:
            if page.text.strip():
                chunks.append(
                    {
                        "chunk_type": "TextBlock",
                        "source_file": Path(result.file_path).name,
                        "page_number": page.page_number,
                        "parser_name": result.parser_name,
                        "confidence": result.quality_score,
                        "text": page.text[:800],
                    }
                )
        for fig in result.figures:
            chunks.append(
                {
                    "chunk_type": "FigureCaptionChunk",
                    "source_file": Path(result.file_path).name,
                    "page_number": fig.page_number,
                    "parser_name": result.parser_name,
                    "confidence": fig.confidence,
                    "text": fig.caption,
                }
            )
    report = {
        "chunk_count": len(chunks),
        "text_chunk_count": sum(1 for c in chunks if c["chunk_type"] == "TextBlock"),
        "figure_chunk_count": sum(1 for c in chunks if c["chunk_type"] == "FigureCaptionChunk"),
        "supports_source_ref": True,
        "chunks_preview": chunks[:100],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
