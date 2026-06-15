"""MinerU optional adapter for Document Intelligence v5."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from core.document_intelligence_v5.base_parser import BaseDocumentParser
from core.document_intelligence_v5.document_blocks import DocumentParseResult
from core.document_intelligence_v5.fallback_parser import FallbackParser


class MinerUAdapterV5(BaseDocumentParser):
    name = "mineru"
    supported_extensions = {"pdf", "png", "jpg", "jpeg", "docx", "pptx", "xlsx"}

    def available(self) -> bool:
        return bool(shutil.which("mineru") or shutil.which("magic-pdf") or importlib.util.find_spec("magic_pdf"))

    def missing_dependency(self) -> str:
        return "MinerU not detected. Install as optional external parser following MinerU official docs."

    def parse(self, file_path: str | Path, output_dir: str | Path = "data/parsed/v5") -> DocumentParseResult:
        # Adapter shell: avoid pretending deep integration unless CLI/module is fully configured.
        result = FallbackParser().parse(file_path, output_dir)
        result.parser_name = self.name if self.available() else "fallback"
        result.warnings.append("MinerU adapter is present, but full CLI execution is not enabled in this run; normalized fallback result returned.")
        return result
