"""DocLayout-YOLO optional adapter for Document Intelligence v5."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from core.document_intelligence_v5.base_parser import BaseDocumentParser
from core.document_intelligence_v5.document_blocks import DocumentParseResult
from core.document_intelligence_v5.fallback_parser import FallbackParser


class DocLayoutYOLOAdapterV5(BaseDocumentParser):
    name = "doclayout_yolo"
    supported_extensions = {"pdf", "png", "jpg", "jpeg", "webp"}

    def available(self) -> bool:
        return importlib.util.find_spec("doclayout_yolo") is not None or importlib.util.find_spec("ultralytics") is not None

    def missing_dependency(self) -> str:
        return "DocLayout-YOLO not detected. Optional dependency: doclayout-yolo / ultralytics with model weights."

    def parse(self, file_path: str | Path, output_dir: str | Path = "data/parsed/v5") -> DocumentParseResult:
        result = FallbackParser().parse(file_path, output_dir)
        result.warnings.append("DocLayout-YOLO layout detection is not enabled in this run; fallback result returned.")
        return result
