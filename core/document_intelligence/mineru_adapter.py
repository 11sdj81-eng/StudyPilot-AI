"""MinerU adapter placeholder for future OCR/structured parsing."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence.parser_result import ParserResult


class MinerUAdapter:
    name = "mineru"

    def available(self) -> bool:
        return False

    def parse(self, file_path: str | Path) -> ParserResult:
        raise NotImplementedError("MinerUAdapter interface is reserved for future MinerU/OCR integration.")
