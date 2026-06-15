"""PyMuPDF fallback adapter — always works, no extra deps beyond base."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from schemas.document_parse_schema import Block, DocumentParseResult, Page


def parse_with_fallback(
    input_path: Path,
    output_dir: Path,
    doc_id: str,
    max_pages: int = 10,
    save_images: str = "true",
) -> DocumentParseResult:
    pages_dir = output_dir / "assets" / "pages"
    if save_images == "true":
        pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(input_path))
    pages: list[Page] = []
    assets: list[str] = []
    warnings: list[str] = []
    is_scanned = True
    total_chars = 0

    try:
        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]
            text = page.get_text()
            total_chars += len(text)

            blocks: list[Block] = []

            if text.strip():
                is_scanned = False
                blocks.append(Block(
                    block_id=f"p{page_num}_text",
                    block_type="text",
                    text=text[:5000],
                    confidence=1.0,
                ))

                # Crude formula detection
                math_syms = ["∫", "∇", "∂", "ε", "ρ", "φ", "∑", "∮", "E=", "D="]
                if any(sym in text for sym in math_syms):
                    blocks.append(Block(
                        block_id=f"p{page_num}_formula",
                        block_type="formula",
                        text=text[:2000],
                        confidence=0.5,
                    ))

            # Save page image
            asset_path = ""
            if save_images == "true":
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_path = pages_dir / f"page_{page_num:03d}.png"
                pix.save(str(img_path))
                asset_path = str(img_path)
                assets.append(asset_path)

            pages.append(Page(
                page_number=page_num,
                text=text[:10000],
                blocks=blocks,
                metadata={"width": int(page.rect.width), "height": int(page.rect.height)},
            ))

    finally:
        doc.close()

    if is_scanned and total_chars < 100:
        warnings.append("Document appears to be scanned (very little extractable text). Use paddleocr or marker mode for OCR.")

    return DocumentParseResult(
        document_id=doc_id,
        file_path=str(input_path),
        file_type=input_path.suffix.lstrip("."),
        parser_used="fallback",
        success=True,
        is_scanned=is_scanned,
        pages=pages,
        assets=assets,
        warnings=warnings,
    )
