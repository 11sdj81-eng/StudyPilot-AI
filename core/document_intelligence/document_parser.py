"""Document parser facade for StudyPilot v3."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence.fallback_parser import parse_with_fallback
from core.document_intelligence.marker_adapter import MarkerAdapter
from core.document_intelligence.mineru_adapter import MinerUAdapter
from core.document_intelligence.parser_result import ParserResult


def parse_document(file_path: str | Path, preferred: str = "auto") -> ParserResult:
    path = Path(file_path)
    adapters = [MarkerAdapter(), MinerUAdapter()]
    if preferred != "fallback":
        for adapter in adapters:
            if preferred in {"auto", adapter.name} and adapter.available():
                return adapter.parse(path)
    return parse_with_fallback(path)
