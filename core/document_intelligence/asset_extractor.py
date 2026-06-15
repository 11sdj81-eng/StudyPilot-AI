"""Asset extraction interfaces for parser results."""

from __future__ import annotations

from core.document_intelligence.parser_result import ParserAsset, ParserResult


def list_assets(result: ParserResult) -> list[ParserAsset]:
    return list(result.assets)
