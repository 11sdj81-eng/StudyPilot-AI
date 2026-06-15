"""Parser registry and selection policy for Document Intelligence v5."""

from __future__ import annotations

import json
from pathlib import Path

from core.document_intelligence_v5.base_parser import BaseDocumentParser
from core.document_intelligence_v5.fallback_parser import FallbackParser
from core.document_intelligence_v5.marker_adapter import MarkerAdapterV5
from core.document_intelligence_v5.mineru_adapter import MinerUAdapterV5
from core.document_intelligence_v5.paddleocr_adapter import PaddleOCRAdapterV5
from core.document_intelligence_v5.doclayout_yolo_adapter import DocLayoutYOLOAdapterV5


class ParserRegistry:
    def __init__(self) -> None:
        self.parsers: list[BaseDocumentParser] = [
            MinerUAdapterV5(),
            MarkerAdapterV5(),
            PaddleOCRAdapterV5(),
            DocLayoutYOLOAdapterV5(),
            FallbackParser(),
        ]
        self.selection_log: list[dict] = []

    def dependency_report(self) -> dict:
        return {
            parser.name: {
                "available": parser.available(),
                "supported_extensions": sorted(parser.supported_extensions),
                "missing_dependency": "" if parser.available() else parser.missing_dependency(),
            }
            for parser in self.parsers
        }

    def select(self, file_path: str | Path, is_scanned: bool | None = None) -> BaseDocumentParser:
        path = Path(file_path)
        ext = path.suffix.lower().lstrip(".")
        strategy = self._strategy(ext, is_scanned)
        for name in strategy:
            parser = next(p for p in self.parsers if p.name == name)
            if ext in parser.supported_extensions and parser.available():
                self._log(path, parser.name, "selected", strategy, is_scanned)
                return parser
        fallback = next(p for p in self.parsers if p.name == "fallback")
        self._log(path, fallback.name, "all preferred parsers unavailable; using fallback", strategy, is_scanned)
        return fallback

    def write_selection_report(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.selection_log, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _strategy(self, ext: str, is_scanned: bool | None) -> list[str]:
        if ext == "pdf" and is_scanned:
            return ["mineru", "doclayout_yolo", "marker", "fallback"]
        if ext == "pdf":
            return ["mineru", "marker", "fallback"]
        if ext in {"pptx", "ppt"}:
            return ["mineru", "marker", "fallback"]
        if ext in {"png", "jpg", "jpeg", "webp"}:
            return ["paddleocr", "mineru", "fallback"]
        if ext in {"docx", "doc"}:
            return ["mineru", "marker", "fallback"]
        return ["mineru", "marker", "fallback"]

    def _log(self, path: Path, parser_name: str, reason: str, strategy: list[str], is_scanned: bool | None) -> None:
        self.selection_log.append(
            {
                "file_path": str(path),
                "file_type": path.suffix.lower().lstrip("."),
                "is_scanned": is_scanned,
                "selected_parser": parser_name,
                "selection_reason": reason,
                "strategy": strategy,
            }
        )
