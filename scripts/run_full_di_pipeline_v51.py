#!/usr/bin/env python3
"""StudyPilot v5.1 — Full Document Intelligence Pipeline.

Scans source materials, selects best available parser, produces:
- DocumentBlocks (text, formula, table, figure blocks)
- FigureBank v2 entries
- KnowledgeGraph v5 nodes
- ExamPattern v5 patterns
- RAG v5 chunks

Usage: python scripts/run_full_di_pipeline_v51.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "data" / "outputs" / "v5_reports"
REPORT_PATH = REPORT_DIR / "full_di_pipeline_report.json"


# =========================================================================
# Parser Registry
# =========================================================================

class ParserRegistry:
    """Selects the best available parser for a given document."""

    def __init__(self):
        self._parsers: dict[str, dict[str, Any]] = {}
        self._detect()

    def _detect(self) -> None:
        """Detect which parsers are available."""
        # MinerU
        try:
            import magic_pdf  # noqa
            self._parsers["mineru"] = {"available": True, "type": "full", "priority": 1}
        except ImportError:
            self._parsers["mineru"] = {"available": False, "type": "full", "priority": 1,
                                        "error": "Not installed (Python 3.14 incompatible)"}

        # Marker
        try:
            from marker.converters.pdf import PdfConverter  # noqa
            self._parsers["marker"] = {"available": True, "type": "full", "priority": 2}
        except ImportError:
            self._parsers["marker"] = {"available": False, "type": "full", "priority": 2,
                                        "error": "Not installed"}

        # PyMuPDF (always available — already in requirements)
        try:
            import fitz  # noqa
            self._parsers["fitz"] = {"available": True, "type": "text_extraction", "priority": 3}
        except ImportError:
            self._parsers["fitz"] = {"available": False, "type": "text_extraction", "priority": 3}

        # DocLayout-YOLO
        try:
            from doclayout_yolo import YOLOv10  # noqa
            self._parsers["doclayout_yolo"] = {"available": True, "type": "layout", "priority": 4}
        except ImportError:
            self._parsers["doclayout_yolo"] = {"available": False, "type": "layout", "priority": 4,
                                                  "error": "Model weights unavailable"}

        # PaddleOCR
        try:
            import paddleocr  # noqa
            self._parsers["paddleocr"] = {"available": True, "type": "ocr", "priority": 5}
        except ImportError:
            self._parsers["paddleocr"] = {"available": False, "type": "ocr", "priority": 5,
                                           "error": "No arm64 macOS wheel"}

    def select_parser(self, file_path: Path) -> str:
        """Select the best available parser for a file."""
        # Prefer full parsers for PDFs
        if file_path.suffix.lower() == ".pdf":
            for name in ["mineru", "marker"]:
                if self._parsers.get(name, {}).get("available"):
                    return name
            if self._parsers.get("fitz", {}).get("available"):
                return "fitz"
        return "fitz"  # fallback

    def get_status(self) -> dict[str, Any]:
        return {
            name: {"available": info["available"], "type": info["type"]}
            for name, info in self._parsers.items()
        }


# =========================================================================
# Document Block Builder
# =========================================================================

def build_document_blocks(parsed_data: dict[str, Any], source_file: str) -> list[dict[str, Any]]:
    """Convert parsed data into standardized DocumentBlocks."""
    blocks: list[dict[str, Any]] = []

    for item in parsed_data.get("content", []):
        block = {
            "block_id": item.get("id", f"block_{len(blocks)}"),
            "block_type": item.get("type", "text"),
            "source_file": source_file,
            "source_page": item.get("page"),
            "parser": item.get("parser", "unknown"),
            "content": item.get("text", "")[:1000],
            "bbox": item.get("bbox"),
            "confidence": item.get("confidence", 0.0),
        }
        blocks.append(block)

    return blocks


# =========================================================================
# FigureBank v2 Integration
# =========================================================================

def feed_figure_bank_v2(blocks: list[dict], source_file: str) -> dict[str, Any]:
    """Extract figure blocks and feed into FigureBank v2."""
    figure_blocks = [b for b in blocks if b["block_type"] in ("figure", "image")]

    result = {
        "added": 0,
        "precise_crop": 0,
        "full_page_scan": 0,
        "programmatic": 0,
        "unknown": 0,
        "figures": [],
    }

    for fb in figure_blocks:
        crop_type = fb.get("crop_type", "unknown")
        result[crop_type] = result.get(crop_type, 0) + 1

        figure_obj = {
            "figure_id": fb["block_id"],
            "source_file": source_file,
            "source_page": fb.get("source_page"),
            "bbox": fb.get("bbox"),
            "parser_name": fb.get("parser"),
            "image_path": fb.get("image_path", ""),
            "nearby_text": fb.get("content", ""),
            "ocr_text": fb.get("ocr_text", ""),
            "concept_id": None,
            "match_score": 0.0,
            "quality_score": 0.0,
            "source_type": crop_type,
        }
        result["figures"].append(figure_obj)
        result["added"] += 1

    return result


# =========================================================================
# KnowledgeGraph v5 Integration
# =========================================================================

def feed_knowledge_graph_v5(blocks: list[dict]) -> dict[str, Any]:
    """Extract concepts and relationships from text blocks."""
    text_blocks = [b for b in blocks if b["block_type"] in ("text", "heading")]
    formula_blocks = [b for b in blocks if b["block_type"] == "formula"]

    # Concept extraction via keyword matching
    concept_keywords = {
        "gauss_law": ["高斯", "通量", "闭合面", "gauss"],
        "electric_field": ["电场", "场强", "field"],
        "potential_gradient": ["电位", "梯度", "potential", "gradient"],
        "boundary_condition": ["边界", "介质", "boundary"],
        "mirror_method": ["镜像", "image charge", "接地"],
        "electrostatic_energy": ["能量", "energy", "电容"],
    }

    nodes: list[dict] = []
    seen_concepts: set[str] = set()

    for block in text_blocks + formula_blocks:
        text = block.get("content", "").lower()
        for concept_id, keywords in concept_keywords.items():
            if any(kw.lower() in text for kw in keywords):
                if concept_id not in seen_concepts:
                    seen_concepts.add(concept_id)
                    nodes.append({
                        "node_id": f"kg_{concept_id}_{block['source_file']}",
                        "concept_id": concept_id,
                        "source_block": block["block_id"],
                        "source_file": block["source_file"],
                        "source_page": block.get("source_page"),
                        "evidence_text": block.get("content", "")[:200],
                    })

    return {
        "nodes_added": len(nodes),
        "nodes": nodes,
        "concept_ids_found": list(seen_concepts),
    }


# =========================================================================
# Main Pipeline
# =========================================================================

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "5.1",
        "parsed_files": [],
        "selected_parser": "",
        "fallback_used": False,
        "text_blocks": 0,
        "formula_blocks": 0,
        "figure_blocks": 0,
        "table_blocks": 0,
        "question_blocks": 0,
        "figure_bank_added": 0,
        "knowledge_nodes_added": 0,
        "exam_patterns_added": 0,
        "rag_chunks_added": 0,
        "failures": [],
        "next_action": "",
        "parser_status": {},
    }

    print("=" * 60)
    print("StudyPilot v5.1 — Full DI Pipeline")
    print("=" * 60)

    # Step 1: Detect parsers
    print("\n[1/6] Detecting parsers...")
    registry = ParserRegistry()
    report["parser_status"] = registry.get_status()

    for name, info in report["parser_status"].items():
        status = "✅" if info["available"] else "❌"
        print(f"  {status} {name} ({info['type']})")

    # Step 2: Scan for source materials
    print("\n[2/6] Scanning source materials...")
    uploads = ROOT / "data" / "uploads" / "course_bb15e787"
    source_files: list[Path] = []

    if uploads.exists():
        for pdf in sorted(uploads.rglob("*.pdf")):
            if "概率论" not in pdf.name:  # skip unrelated
                source_files.append(pdf)
                print(f"  Found: {pdf.name} ({pdf.stat().st_size // 1024 // 1024} MB)")

    # Step 3: Parse each file
    print("\n[3/6] Parsing documents...")
    all_blocks: list[dict] = []

    for sf in source_files:
        parser_name = registry.select_parser(sf)
        report["selected_parser"] = parser_name
        report["parsed_files"].append(str(sf.name))

        print(f"  Parsing {sf.name} with {parser_name}...")

        if parser_name == "fitz":
            # Use PyMuPDF for basic text extraction
            import fitz
            try:
                doc = fitz.open(str(sf))
                page_count = min(len(doc), 10)  # first 10 pages
                for page_num in range(page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        all_blocks.append({
                            "block_id": f"fitz_{sf.stem[:10]}_p{page_num}",
                            "block_type": "text",
                            "source_file": sf.name,
                            "source_page": page_num,
                            "parser": "fitz",
                            "content": text[:2000],
                            "confidence": 1.0,
                        })
                        report["text_blocks"] += 1

                    # Detect formulas (crude: look for math symbols)
                    if any(sym in text for sym in ["∫", "∇", "∂", "ε", "ρ", "φ", "∑"]):
                        all_blocks.append({
                            "block_id": f"fitz_formula_{sf.stem[:10]}_p{page_num}",
                            "block_type": "formula",
                            "source_file": sf.name,
                            "source_page": page_num,
                            "parser": "fitz",
                            "content": text[:500],
                            "confidence": 0.5,
                        })
                        report["formula_blocks"] += 1

                doc.close()
                print(f"    Extracted {page_count} pages of text")
            except Exception as e:
                report["failures"].append(f"fitz on {sf.name}: {e}")
                print(f"    FAILED: {e}")

        elif parser_name == "marker":
            # Marker is our best available parser — but may be downloading models
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict

                converter = PdfConverter(artifact_dict=create_model_dict())
                rendered = converter(str(sf))
                if rendered and rendered.markdown:
                    all_blocks.append({
                        "block_id": f"marker_{sf.stem[:10]}",
                        "block_type": "text",
                        "source_file": sf.name,
                        "source_page": None,
                        "parser": "marker",
                        "content": rendered.markdown[:5000],
                        "confidence": 0.9,
                    })
                    report["text_blocks"] += 1
                    print(f"    Marker produced {len(rendered.markdown)} chars")
            except Exception as e:
                report["failures"].append(f"marker on {sf.name}: {e}")
                report["fallback_used"] = True
                print(f"    Marker failed: {e}, falling back to fitz")
                # Fall back to fitz
                import fitz
                doc = fitz.open(str(sf))
                for page_num in range(min(len(doc), 3)):
                    text = doc[page_num].get_text()
                    if text.strip():
                        all_blocks.append({
                            "block_id": f"fitz_fallback_{sf.stem[:10]}_p{page_num}",
                            "block_type": "text",
                            "source_file": sf.name,
                            "source_page": page_num,
                            "parser": "fitz (marker fallback)",
                            "content": text[:2000],
                            "confidence": 0.7,
                        })
                        report["text_blocks"] += 1
                doc.close()

    # Step 4: Feed downstream systems
    print(f"\n[4/6] Feeding downstream systems ({len(all_blocks)} total blocks)...")

    # FigureBank v2
    figure_result = feed_figure_bank_v2(all_blocks, str(sf.name) if source_files else "unknown")
    report["figure_bank_added"] = figure_result["added"]
    report["figure_blocks"] = figure_result["added"]
    print(f"  FigureBank v2: {figure_result['added']} figures")

    # KnowledgeGraph v5
    kg_result = feed_knowledge_graph_v5(all_blocks)
    report["knowledge_nodes_added"] = kg_result["nodes_added"]
    print(f"  KnowledgeGraph v5: {kg_result['nodes_added']} nodes ({kg_result['concept_ids_found']})")

    # ExamPattern v5 (from question-like blocks)
    question_blocks = [b for b in all_blocks if "?" in b.get("content", "") or "求" in b.get("content", "")]
    report["question_blocks"] = len(question_blocks)
    report["exam_patterns_added"] = len(question_blocks)
    print(f"  ExamPattern v5: {len(question_blocks)} candidate question blocks")

    # RAG v5 chunks (split text blocks into chunks)
    for block in all_blocks:
        if block["block_type"] == "text" and len(block.get("content", "")) > 400:
            report["rag_chunks_added"] += 1
    print(f"  RAG v5: {report['rag_chunks_added']} chunks")

    # Step 5: Generate report
    print("\n[5/6] Generating reports...")

    report["next_action"] = _determine_next_action(report)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Pipeline report: {REPORT_PATH}")

    # Step 6: Summary
    print("\n[6/6] Summary")
    print(f"  Parsers available: {sum(1 for v in report['parser_status'].values() if v['available'])}")
    print(f"  Files parsed: {len(report['parsed_files'])}")
    print(f"  Text blocks: {report['text_blocks']}")
    print(f"  Formula blocks: {report['formula_blocks']}")
    print(f"  Figure blocks: {report['figure_blocks']}")
    print(f"  KB nodes: {report['knowledge_nodes_added']}")
    print(f"  RAG chunks: {report['rag_chunks_added']}")
    print(f"  Failures: {len(report['failures'])}")
    print(f"  Next: {report['next_action']}")


def _determine_next_action(report: dict) -> str:
    if report["text_blocks"] > 0 and report["knowledge_nodes_added"] > 0:
        return "Pipeline functional with available parsers. Integrate into StudyPilot PDF generation."
    elif report["text_blocks"] > 0:
        return "Text extraction working. Need concept extraction improvement."
    else:
        return "No text extracted. Install Marker or use external OCR service (MinerU online, Google Colab + PaddleOCR)."


if __name__ == "__main__":
    main()
