"""Marker optional adapter for Document Intelligence v5."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from core.document_intelligence_v5.base_parser import BaseDocumentParser
from core.document_intelligence_v5.document_blocks import DocumentParseResult
from core.document_intelligence_v5.fallback_parser import FallbackParser


class MarkerAdapterV5(BaseDocumentParser):
    name = "marker"
    supported_extensions = {"pdf", "png", "jpg", "jpeg", "pptx", "docx", "xlsx", "html", "epub"}

    def available(self) -> bool:
        return bool(shutil.which("marker_single") or shutil.which("marker") or importlib.util.find_spec("marker"))

    def missing_dependency(self) -> str:
        return "Marker not detected. Optional dependency: marker-pdf."

    def parse(self, file_path: str | Path, output_dir: str | Path = "data/parsed/v5") -> DocumentParseResult:
        result = FallbackParser().parse(file_path, output_dir)
        result.parser_name = self.name if self.available() else "fallback"
        result.warnings.append("Marker adapter is present, but full Marker execution is not enabled in this run; normalized fallback result returned.")
        return result
