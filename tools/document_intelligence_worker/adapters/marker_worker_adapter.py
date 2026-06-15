"""Marker adapter — PDF → Markdown/JSON with text, formulas, tables."""

from __future__ import annotations

from pathlib import Path

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from schemas.document_parse_schema import Block, DocumentParseResult, Page


def parse_with_marker(
    input_path: Path,
    output_dir: Path,
    doc_id: str,
    max_pages: int = 10,
) -> DocumentParseResult:
    warnings: list[str] = []

    converter = PdfConverter(
        artifact_dict=create_model_dict(),
    )
    rendered = converter(str(input_path))

    if not rendered or not rendered.markdown:
        return DocumentParseResult(
            document_id=doc_id,
            file_path=str(input_path),
            parser_used="marker",
            success=False,
            warnings=["Marker produced no output"],
        )

    markdown = rendered.markdown

    # Build pages from markdown structure
    pages: list[Page] = []
    blocks: list[Block] = []

    # Split markdown into blocks
    md_parts = markdown.split("\n\n")
    for i, part in enumerate(md_parts[:200]):  # safety cap
        part = part.strip()
        if not part:
            continue

        block_type = "text"
        if part.startswith("#"):
            block_type = "title"
        elif "$" in part or "\\begin" in part:
            block_type = "formula"
        elif "?" in part or "求" in part[:50]:
            block_type = "question"
        elif part.startswith("|") and "|" in part[1:]:
            block_type = "table"

        blocks.append(Block(
            block_id=f"marker_b{i}",
            block_type=block_type,
            text=part[:3000],
            confidence=0.85,
            metadata={"source": "marker"},
        ))

    # Crude page assignment (Marker output is continuous markdown, not page-aware)
    pages.append(Page(
        page_number=0,
        text=markdown[:100000],
        blocks=blocks,
        metadata={"note": "Marker outputs continuous markdown, pages approximated"},
    ))

    # Formula count
    formula_count = sum(1 for b in blocks if b.block_type == "formula")

    return DocumentParseResult(
        document_id=doc_id,
        file_path=str(input_path),
        file_type=input_path.suffix.lstrip("."),
        parser_used="marker",
        success=True,
        is_scanned=False,
        pages=pages,
        markdown=markdown,
        warnings=warnings,
        metadata={
            "markdown_chars": len(markdown),
            "block_count": len(blocks),
            "formula_count": formula_count,
        },
    )
