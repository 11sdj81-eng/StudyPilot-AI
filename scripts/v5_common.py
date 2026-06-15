"""Helpers shared by v5 scripts."""

from __future__ import annotations

import json
from pathlib import Path

from core.document_intelligence_v5.document_blocks import DocumentParseResult, PageBlock, DocumentBlock, FigureBlock


def load_parse_results(input_dir: str | Path) -> list[DocumentParseResult]:
    results = []
    for path in sorted(Path(input_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pages = []
        for page in data.get("pages", []):
            blocks = [DocumentBlock(**{k: v for k, v in b.items() if k in DocumentBlock.__dataclass_fields__}) for b in page.get("blocks", [])]
            pages.append(PageBlock(page_number=page["page_number"], text=page.get("text", ""), blocks=blocks))
        figures = []
        for fig in data.get("figures", []):
            allowed = {k: v for k, v in fig.items() if k in FigureBlock.__dataclass_fields__}
            figures.append(FigureBlock(**allowed))
        results.append(
            DocumentParseResult(
                document_id=data["document_id"],
                file_path=data["file_path"],
                file_type=data["file_type"],
                parser_name=data["parser_name"],
                is_scanned=data["is_scanned"],
                pages=pages,
                markdown=data.get("markdown", ""),
                assets=data.get("assets", []),
                figures=figures,
                warnings=data.get("warnings", []),
                metadata=data.get("metadata", {}),
                quality_score=data.get("quality_score", 0.0),
            )
        )
    return results


def write_acknowledgement_draft(path: str | Path) -> Path:
    content = """# Open Source Acknowledgement Draft

| Project | Status | Purpose in StudyPilot | License note |
| --- | --- | --- | --- |
| MinerU | Optional Adapter | Planned primary parser for PDF/image/DOCX/PPTX/XLSX layout, formulas, tables and assets | Check upstream license before bundling; no code copied |
| Marker | Optional Adapter | Fallback/compare parser for Markdown/JSON/chunks/assets | Optional dependency; no code copied |
| PaddleOCR | Optional Adapter | Chinese OCR for scanned pages, figures, captions and exam questions | Optional dependency/model weights external |
| DocLayout-YOLO | Optional Adapter | Layout region detection and figure/table/formula/question cropping | Optional dependency/model weights external |
| Nougat | Reserved Adapter | Formula-heavy academic PDF parsing | Reserved only |
| Unstructured / MarkItDown | Reserved Adapter | Multi-format document parsing expansion | Reserved only |
| Typst | Integrated | Formal PDF v4/v4.1 publishing engine | External CLI |
| PyMuPDF | Used | Current fallback PDF text/image inspection | Python dependency |
| python-pptx | Optional | PPTX fallback extraction | Optional dependency |

This draft is for README / GitHub acknowledgement preparation. It does not claim deep integration for adapters that are currently optional or unavailable in the local environment.
"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
