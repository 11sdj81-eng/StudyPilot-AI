# StudyPilot v5.1 Architecture

## Overview

v5.1 adds a Document Intelligence layer without replacing the existing UI,
upload flow, RAG, DeepSeek configuration, or PDF v4.1 output.

All downstream systems consume unified `DocumentParseResult` and `DocumentBlock`
objects. They do not depend on raw MinerU, Marker, PaddleOCR, or DocLayout-YOLO
JSON directly.

## Architecture Diagram

```
Uploaded course files
    │
    ▼
ParserRegistry (auto-selects best available)
    ├── MinerU        ❌ Not available (Python 3.14)
    ├── Marker        ✅ Available (v1.10.2)
    ├── PaddleOCR     ❌ Not available (no arm64 wheel)
    ├── DocLayout-YOLO ⚠️ Package ok, weights unavailable
    └── PyMuPDF       ✅ Fallback (always available)
    │
    ▼
DocumentParseResult
    │
    ├──► FigureBank v2        (figure extraction)
    ├──► KnowledgeGraph v5    (concept extraction)
    ├──► ExamPattern v5       (question detection)
    ├──► RAG v5               (text chunking)
    └──► PDF v4.1 / v5        (optional enhanced input)
```

## Real Status (2026-06-15)

| Component | Status | What Works |
|-----------|--------|------------|
| ParserRegistry | ✅ | Auto-detects available parsers |
| Marker | ✅ | Python API works; model download needed |
| PyMuPDF | ✅ | Text extraction from digital PDFs |
| DocLayout-YOLO | ⚠️ | Package installed; weights download broken |
| MinerU | ❌ | Python 3.14 incompatibility (PyO3) |
| PaddleOCR | ❌ | No macOS arm64 support |
| FigureBank v2 | ✅ | Receives blocks from parsers |
| KnowledgeGraph v5 | ✅ | Keyword-based concept extraction |
| ExamPattern v5 | ✅ | Question block detection |
| RAG v5 | ✅ | Text chunking from parsed blocks |
| PDF v4.1 | ✅ | Remains stable, unchanged |
| Full DI Pipeline | ✅ | `scripts/run_full_di_pipeline_v51.py` |

## Key Design Decisions

1. **All DI tools are optional.** PyMuPDF is the only mandatory fallback.
2. **ParserRegistry selects best parser** based on availability and file type.
3. **DocumentBlocks are the universal format** — parsers produce them, downstream systems consume them.
4. **`use_document_intelligence_v5 = False`** is the default for PDF generation — v4.1 remains stable.
5. **Model weights are never bundled** — downloaded at runtime by the user.

## Next Steps

1. Fix DocLayout-YOLO weights download (try direct HuggingFace Hub loading)
2. Wait for PyO3/Pydantic-core Python 3.14 support for MinerU
3. Test Marker on more PDFs once model downloads complete
4. Consider EasyOCR as PaddleOCR alternative for macOS arm64
5. Test with Python 3.12 environment for full DI ecosystem

---

*Updated: 2026-06-15*
