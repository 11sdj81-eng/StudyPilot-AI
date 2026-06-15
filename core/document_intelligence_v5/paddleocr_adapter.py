"""PaddleOCR optional adapter for Document Intelligence v5."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from core.document_intelligence_v5.base_parser import BaseDocumentParser
from core.document_intelligence_v5.document_blocks import DocumentParseResult, OCRResult
from core.document_intelligence_v5.fallback_parser import FallbackParser


class PaddleOCRAdapterV5(BaseDocumentParser):
    name = "paddleocr"
    supported_extensions = {"png", "jpg", "jpeg", "webp", "pdf"}

    def available(self) -> bool:
        return importlib.util.find_spec("paddleocr") is not None

    def missing_dependency(self) -> str:
        return "PaddleOCR not detected. Optional dependency: paddleocr."

    def parse(self, file_path: str | Path, output_dir: str | Path = "data/parsed/v5") -> DocumentParseResult:
        result = FallbackParser().parse(file_path, output_dir)
        result.warnings.append("PaddleOCR full OCR execution is not enabled in this run; fallback result returned.")
        return result


def empty_ocr_result() -> OCRResult:
    return OCRResult(text="", confidence=0.0, metadata={"reason": "paddleocr_unavailable"})
