"""Standard document parse schema for DI Worker v5.2.

All parsers (PyMuPDF, PaddleOCR, Marker, MinerU, DocLayout-YOLO) output
this unified format so the main project never depends on raw parser outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Block:
    block_id: str
    block_type: str  # text, title, figure, table, formula, question, caption
    text: str = ""
    bbox: list[float] = field(default_factory=lambda: [0, 0, 0, 0])
    confidence: float = 0.0
    asset_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "text": self.text,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "asset_path": self.asset_path,
            "metadata": self.metadata,
        }


@dataclass
class Page:
    page_number: int
    text: str = ""
    blocks: list[Block] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "blocks": [b.to_dict() for b in self.blocks],
            "metadata": self.metadata,
        }


@dataclass
class DocumentParseResult:
    document_id: str
    file_path: str
    file_type: str = "pdf"
    parser_used: str = "unknown"
    success: bool = False
    is_scanned: bool = False
    pages: list[Page] = field(default_factory=list)
    markdown: str = ""
    assets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "parser_used": self.parser_used,
            "success": self.success,
            "is_scanned": self.is_scanned,
            "pages": [p.to_dict() for p in self.pages],
            "markdown": self.markdown,
            "assets": self.assets,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentParseResult":
        pages = []
        for p in data.get("pages", []):
            blocks = []
            for b in p.get("blocks", []):
                blocks.append(Block(**{k: b.get(k, "") if k == "text" else b.get(k, []) if k == "bbox" else b.get(k, {}) if k == "metadata" else b.get(k, 0.0) if k == "confidence" else b.get(k, "") for k in ["block_id", "block_type", "text", "bbox", "confidence", "asset_path", "metadata"]}))
            pages.append(Page(page_number=p["page_number"], text=p.get("text", ""), blocks=blocks, metadata=p.get("metadata", {})))
        return cls(
            document_id=data.get("document_id", ""),
            file_path=data.get("file_path", ""),
            file_type=data.get("file_type", "pdf"),
            parser_used=data.get("parser_used", "unknown"),
            success=data.get("success", False),
            is_scanned=data.get("is_scanned", False),
            pages=pages,
            markdown=data.get("markdown", ""),
            assets=data.get("assets", []),
            warnings=data.get("warnings", []),
            metadata=data.get("metadata", {}),
        )
