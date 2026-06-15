"""Marker adapter placeholder for future structured PDF/PPT parsing."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence.parser_result import ParserResult


class MarkerAdapter:
    name = "marker"

    def available(self) -> bool:
        return False

    def parse(self, file_path: str | Path) -> ParserResult:
        raise NotImplementedError("MarkerAdapter interface is reserved for future Marker integration.")
