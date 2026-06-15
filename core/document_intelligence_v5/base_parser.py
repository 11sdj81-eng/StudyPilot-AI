"""Base parser interface for Document Intelligence v5."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence_v5.document_blocks import DocumentParseResult


class BaseDocumentParser:
    name = "base"
    supported_extensions: set[str] = set()

    def available(self) -> bool:
        return False

    def missing_dependency(self) -> str:
        return f"{self.name} is not installed."

    def parse(self, file_path: str | Path, output_dir: str | Path = "data/parsed/v5") -> DocumentParseResult:
        raise NotImplementedError
