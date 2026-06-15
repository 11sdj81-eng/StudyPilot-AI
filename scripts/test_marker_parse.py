#!/usr/bin/env python3
"""Test Marker parser on a real PDF and convert output to DocumentBlocks.

Usage: python scripts/test_marker_parse.py
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "data" / "outputs" / "v5_reports"
OUTPUT_DIR = ROOT / "data" / "parsed" / "marker"
REPORT_PATH = REPORT_DIR / "marker_report.json"


def _check_marker_available() -> bool:
    try:
        import marker  # noqa
        return True
    except ImportError:
        return False


def _run_marker_on_pdf(pdf_path: Path, output_dir: Path) -> dict[str, Any]:
    """Run Marker CLI on a PDF file."""
    import subprocess

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "marker",
        str(pdf_path),
        str(output_dir),
        "--workers", "1",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout after 600s"}


def _collect_marker_outputs(output_dir: Path) -> dict[str, Any]:
    """Collect and summarize Marker output files."""
    stats = {
        "markdown_files": 0,
        "json_files": 0,
        "image_files": 0,
        "markdown_chars": 0,
        "outputs": [],
    }
    for f in sorted(output_dir.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(output_dir))
            stats["outputs"].append(rel)
            if f.suffix == ".md":
                stats["markdown_files"] += 1
                stats["markdown_chars"] += len(f.read_text(encoding="utf-8", errors="replace"))
            elif f.suffix == ".json":
                stats["json_files"] += 1
            elif f.suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                stats["image_files"] += 1
    return stats


def _build_document_blocks(marker_output_dir: Path, pdf_name: str) -> list[dict]:
    """Convert Marker output to DocumentBlocks format."""
    blocks = []
    for md_file in sorted(marker_output_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8", errors="replace")
        # Crude block splitting by paragraphs
        page_num = None
        for part in md_file.stem.split("_"):
            try:
                page_num = int(part)
                break
            except ValueError:
                continue

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs):
            block = {
                "block_id": f"marker_{md_file.stem}_{i}",
                "block_type": "text",
                "source_file": pdf_name,
                "source_page": page_num,
                "parser": "marker",
                "content": para[:500],
                "content_length": len(para),
            }
            # Detect formulas
            if "$" in para or "$$" in para or "\\begin" in para:
                block["block_type"] = "formula"
            elif para.startswith("#"):
                block["block_type"] = "heading"
            blocks.append(block)
    return blocks


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parser_name": "Marker",
        "success": False,
        "input_files": [],
        "markdown_generated": False,
        "json_generated": False,
        "image_count": 0,
        "formula_count": 0,
        "table_count": 0,
        "text_blocks": 0,
        "document_blocks": [],
        "warnings": [],
        "next_action": "",
    }

    # Check availability
    if not _check_marker_available():
        report["warnings"].append("Marker not installed. Run: pip install marker-pdf")
        report["next_action"] = "Install Marker: pip install marker-pdf"
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"[Marker] NOT AVAILABLE. Report: {REPORT_PATH}")
        return

    print("[Marker] Available. Starting parse test...")

    # Find input PDFs (prefer small past papers for speed)
    uploads = ROOT / "data" / "uploads" / "course_bb15e787"
    pdfs = sorted(uploads.rglob("*.pdf"))
    # Filter: skip huge textbook (300MB+) for Marker test, use past papers first
    test_pdfs = [p for p in pdfs if p.stat().st_size < 10 * 1024 * 1024]  # <10MB
    if not test_pdfs:
        test_pdfs = [p for p in pdfs][:1]

    report["input_files"] = [str(p.name) for p in test_pdfs]

    for pdf_path in test_pdfs:
        print(f"\n[Marker] Processing: {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")
        pdf_output = OUTPUT_DIR / pdf_path.stem
        pdf_output.mkdir(parents=True, exist_ok=True)

        # Run Marker
        cli_result = _run_marker_on_pdf(pdf_path, pdf_output)

        if cli_result["success"]:
            print(f"  ✅ Marker CLI succeeded")
        else:
            print(f"  ❌ Marker CLI failed: {cli_result.get('stderr', '')[:300]}")
            report["warnings"].append(f"Marker failed on {pdf_path.name}: {cli_result.get('stderr', '')[:200]}")
            continue

        # Collect outputs
        stats = _collect_marker_outputs(pdf_output)
        print(f"  Output: {stats['markdown_files']} md, {stats['json_files']} json, {stats['image_files']} images, {stats['markdown_chars']} chars")

        report["markdown_generated"] = stats["markdown_files"] > 0
        report["json_generated"] = stats["json_files"] > 0
        report["image_count"] += stats["image_files"]

        # Build DocumentBlocks
        blocks = _build_document_blocks(pdf_output, pdf_path.name)
        report["document_blocks"].extend(blocks)
        report["text_blocks"] += sum(1 for b in blocks if b["block_type"] == "text")
        report["formula_count"] += sum(1 for b in blocks if b["block_type"] == "formula")

    if report["markdown_generated"]:
        report["success"] = True
        report["next_action"] = "Marker results can be integrated into DocumentBlocks pipeline."
    else:
        report["warnings"].append("Marker did not produce any markdown output from the test PDFs.")
        report["next_action"] = "Check Marker installation or try different input PDF."

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[Marker] Report: {REPORT_PATH}")
    print(f"[Marker] Success: {report['success']}, text blocks: {report['text_blocks']}, formulas: {report['formula_count']}")


if __name__ == "__main__":
    main()
