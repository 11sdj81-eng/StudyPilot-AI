#!/usr/bin/env python3
"""StudyPilot DI Worker v5.2 — Unified document parser CLI.

Usage:
  python parse_document.py --input file.pdf --output out_dir --mode auto

Modes: auto, fallback, paddleocr, marker, mineru, doclayout
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add adapters path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schemas.document_parse_schema import Block, DocumentParseResult, Page


def main():
    parser = argparse.ArgumentParser(description="DI Worker — Parse documents")
    parser.add_argument("--input", required=True, help="Path to input PDF/PPTX")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--mode", default="auto", choices=["auto", "fallback", "paddleocr", "marker", "mineru", "doclayout"])
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to process")
    parser.add_argument("--save-images", type=str, default="true", help="Save page images")
    parser.add_argument("--save-crops", type=str, default="true", help="Save figure/table crops")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_id = input_path.stem[:40].replace(" ", "_")

    # ---- Select parser ----
    parser_used, doc = _run_parser(args.mode, input_path, output_dir, doc_id, args)

    # ---- Write outputs ----
    doc.metadata.update({
        "parse_time": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "max_pages": args.max_pages,
    })

    # document.json
    doc_path = output_dir / "document.json"
    doc_path.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2))
    print(f"✅ document.json → {doc_path}")

    # document.md
    if doc.markdown:
        md_path = output_dir / "document.md"
        md_path.write_text(doc.markdown, encoding="utf-8")
        print(f"✅ document.md → {md_path} ({len(doc.markdown)} chars)")

    # report.json (always generated even on failure)
    report = _build_report(doc, parser_used, output_dir)
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ report.json → {report_path}")

    # logs.txt
    log_path = output_dir / "logs.txt"
    log_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"\n{'='*50}")
    print(f"Parse complete: parser={parser_used}, success={doc.success}")
    print(f"  Pages: {len(doc.pages)}, Blocks: {sum(len(p.blocks) for p in doc.pages)}")
    print(f"  OCR chars: {sum(len(p.text) for p in doc.pages)}")
    print(f"  Warnings: {len(doc.warnings)}")
    print(f"{'='*50}")


def _run_parser(mode: str, input_path: Path, output_dir: Path, doc_id: str, args: Any) -> tuple[str, DocumentParseResult]:
    """Dispatch to the correct parser adapter."""

    # ---- Determine parser ----
    if mode == "auto":
        mode = _auto_select()

    parser_used = mode

    # ---- PaddleOCR (priority 1 — OCR scanned pages) ----
    if mode == "paddleocr":
        try:
            from adapters.paddleocr_worker_adapter import parse_with_paddleocr
            doc = parse_with_paddleocr(input_path, output_dir, doc_id, max_pages=args.max_pages, save_images=args.save_images)
            return "paddleocr", doc
        except Exception as e:
            return "paddleocr", _failure_doc(doc_id, str(input_path), "paddleocr", str(e))

    # ---- Marker (priority 2 — full parse) ----
    if mode == "marker":
        try:
            from adapters.marker_worker_adapter import parse_with_marker
            doc = parse_with_marker(input_path, output_dir, doc_id, max_pages=args.max_pages)
            return "marker", doc
        except Exception as e:
            return "marker", _failure_doc(doc_id, str(input_path), "marker", str(e))

    # ---- MinerU (priority 3 — complex PDFs) ----
    if mode == "mineru":
        try:
            from adapters.mineru_worker_adapter import parse_with_mineru
            doc = parse_with_mineru(input_path, output_dir, doc_id, max_pages=args.max_pages)
            return "mineru", doc
        except Exception as e:
            return "mineru", _failure_doc(doc_id, str(input_path), "mineru", str(e))

    # ---- Fallback (always works) ----
    try:
        from adapters.fallback_worker_adapter import parse_with_fallback
        doc = parse_with_fallback(input_path, output_dir, doc_id, max_pages=args.max_pages, save_images=args.save_images)
        return "fallback", doc
    except Exception as e:
        return "fallback", _failure_doc(doc_id, str(input_path), "fallback", str(e))


def _auto_select() -> str:
    """Select best available parser."""
    # Try PaddleOCR first (best for Chinese scanned docs)
    try:
        import paddleocr
        return "paddleocr"
    except ImportError:
        pass
    # Try Marker
    try:
        from marker.converters.pdf import PdfConverter
        return "marker"
    except ImportError:
        pass
    # Fallback
    return "fallback"


def _failure_doc(doc_id: str, file_path: str, parser: str, error: str) -> DocumentParseResult:
    return DocumentParseResult(
        document_id=doc_id,
        file_path=file_path,
        parser_used=parser,
        success=False,
        warnings=[f"Parser '{parser}' failed: {error}"],
    )


def _build_report(doc: DocumentParseResult, parser_used: str, output_dir: Path) -> dict:
    blocks = []
    for page in doc.pages:
        for b in page.blocks:
            blocks.append(b.block_type)

    return {
        "parser_used": parser_used,
        "success": doc.success,
        "is_scanned": doc.is_scanned,
        "page_count": len(doc.pages),
        "total_blocks": len(blocks),
        "block_types": {t: blocks.count(t) for t in set(blocks)},
        "ocr_chars": sum(len(p.text) for p in doc.pages),
        "markdown_chars": len(doc.markdown),
        "asset_count": len(doc.assets),
        "warnings": doc.warnings,
        "output_dir": str(output_dir),
    }


if __name__ == "__main__":
    main()
