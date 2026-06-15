# Document Intelligence Worker Setup

StudyPilot AI v1.3 Beta includes optional document intelligence adapters for advanced PDF parsing, OCR, figure extraction, and layout analysis.

These adapters are optional. The core Streamlit app, upload flow, RAG pipeline, DeepSeek generation, and Typst PDF generation can run without installing the full document intelligence stack.

## Recommended Local Setup

```bash
python -m venv tools/document_intelligence_worker/.venv-di
source tools/document_intelligence_worker/.venv-di/bin/activate
pip install -r requirements-di.txt
```

Optional OCR dependencies can be installed separately:

```bash
pip install -r requirements-ocr.txt
```

## Notes

- Some document intelligence packages may not support every Python/macOS combination.
- Large model weights and OCR caches are not committed to the repository.
- When an optional parser is unavailable, StudyPilot falls back to safer PyMuPDF-based parsing and marks lower-confidence assets for review.
