"""PaddleOCR adapter — Chinese OCR for scanned pages."""

from __future__ import annotations

from pathlib import Path

import cv2
import fitz
import numpy as np
from paddleocr import PaddleOCR
from schemas.document_parse_schema import Block, DocumentParseResult, Page

# Singleton OCR instance
_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(lang="ch", use_angle_cls=True)
    return _ocr


def parse_with_paddleocr(
    input_path: Path,
    output_dir: Path,
    doc_id: str,
    max_pages: int = 10,
    save_images: str = "true",
) -> DocumentParseResult:
    pages_dir = output_dir / "assets" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    ocr = _get_ocr()
    doc = fitz.open(str(input_path))
    pages: list[Page] = []
    assets: list[str] = []
    warnings: list[str] = []

    try:
        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]

            # Render page as image
            mat = fitz.Matrix(2.0, 2.0)  # 2x for OCR quality
            pix = page.get_pixmap(matrix=mat)
            img_path = pages_dir / f"page_{page_num:03d}.png"
            pix.save(str(img_path))
            assets.append(str(img_path))

            # OCR the page
            img = cv2.imread(str(img_path))
            if img is None:
                warnings.append(f"Page {page_num}: failed to read image")
                pages.append(Page(page_number=page_num, text=""))
                continue

            ocr_result = ocr.ocr(img)
            blocks: list[Block] = []
            texts: list[str] = []

            if ocr_result and len(ocr_result) > 0:
                r = ocr_result[0]
                # PaddleOCR 3.7 returns OCRResult dict-like object
                rec_texts = r.get("rec_texts", []) if hasattr(r, "get") else []
                rec_scores = r.get("rec_scores", []) if hasattr(r, "get") else []
                dt_polys = r.get("dt_polys", []) if hasattr(r, "get") else []

                for i in range(len(rec_texts)):
                    text = rec_texts[i]
                    confidence = rec_scores[i] if i < len(rec_scores) else 0.0
                    texts.append(text)

                    # Get bbox from dt_polys
                    if i < len(dt_polys):
                        poly = dt_polys[i]
                        if isinstance(poly, list) and len(poly) >= 4:
                            xs = [p[0] for p in poly]
                            ys = [p[1] for p in poly]
                            flat_bbox = [min(xs), min(ys), max(xs), max(ys)]
                        else:
                            flat_bbox = [0, 0, 0, 0]
                    else:
                        flat_bbox = [0, 0, 0, 0]

                    # Classify block type
                    block_type = "text"
                    if len(text) < 40 and any(kw in text for kw in ["第", "章", "节", "电磁场"]):
                        block_type = "title"
                    elif any(sym in text for sym in ["=", "∫", "∇", "∂", "φ", "ε", "ρ"]):
                        block_type = "formula"
                    elif "?" in text or "求" in text or "计算" in text:
                        block_type = "question"

                    blocks.append(Block(
                        block_id=f"ocr_p{page_num}_{i}",
                        block_type=block_type,
                        text=text,
                        bbox=flat_bbox,
                        confidence=round(float(confidence), 4),
                    ))

            page_text = "\n".join(texts)
            pages.append(Page(page_number=page_num, text=page_text, blocks=blocks))

    finally:
        doc.close()

    total_chars = sum(len(p.text) for p in pages)
    success = total_chars > 100

    if not success:
        warnings.append(f"OCR produced only {total_chars} chars — may be a blank/scanned page issue.")

    return DocumentParseResult(
        document_id=doc_id,
        file_path=str(input_path),
        file_type=input_path.suffix.lstrip("."),
        parser_used="paddleocr",
        success=success,
        is_scanned=True,  # PaddleOCR is used precisely for scanned docs
        pages=pages,
        assets=assets,
        warnings=warnings,
    )
