"""Document Intelligence interfaces for StudyPilot v3."""

from core.document_intelligence.document_parser import parse_document
from core.document_intelligence.parser_result import ParserAsset, ParserPage, ParserResult

__all__ = ["parse_document", "ParserAsset", "ParserPage", "ParserResult"]
