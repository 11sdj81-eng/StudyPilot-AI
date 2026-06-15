"""Unified DocumentBlocks for StudyPilot Document Intelligence v5."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceRef:
    source_file: str
    page_number: int = 0
    bbox: list[float] | None = None
    parser_name: str = ""
    confidence: float = 0.0


@dataclass
class DocumentBlock:
    block_id: str
    page_number: int
    block_type: str
    text: str = ""
    bbox: list[float] | None = None
    confidence: float = 0.0
    source_ref: SourceRef | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class TextBlock(DocumentBlock):
    pass


@dataclass
class TitleBlock(DocumentBlock):
    pass


@dataclass
class FormulaBlock(DocumentBlock):
    latex: str = ""


@dataclass
class TableBlock(DocumentBlock):
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class FigureBlock(DocumentBlock):
    image_path: str = ""
    caption: str = ""


@dataclass
class CaptionBlock(DocumentBlock):
    pass


@dataclass
class QuestionBlock(DocumentBlock):
    question_no: str = ""
    score: float = 0.0


@dataclass
class AnswerBlock(DocumentBlock):
    question_no: str = ""


@dataclass
class LayoutRegion:
    region_id: str
    page_number: int
    region_type: str
    bbox: list[float]
    confidence: float
    image_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OCRResult:
    text: str
    confidence: float
    language: str = "zh"
    bbox: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PageBlock:
    page_number: int
    text: str = ""
    blocks: list[DocumentBlock] = field(default_factory=list)
    layout_regions: list[LayoutRegion] = field(default_factory=list)
    ocr_results: list[OCRResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "blocks": [b.to_dict() for b in self.blocks],
            "layout_regions": [r.to_dict() for r in self.layout_regions],
            "ocr_results": [o.to_dict() for o in self.ocr_results],
        }


@dataclass
class DocumentParseResult:
    document_id: str
    file_path: str
    file_type: str
    parser_name: str
    is_scanned: bool
    pages: list[PageBlock] = field(default_factory=list)
    markdown: str = ""
    json_data: dict[str, Any] = field(default_factory=dict)
    assets: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[FormulaBlock] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)
    figures: list[FigureBlock] = field(default_factory=list)
    questions: list[QuestionBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "parser_name": self.parser_name,
            "is_scanned": self.is_scanned,
            "pages": [p.to_dict() for p in self.pages],
            "markdown": self.markdown,
            "json_data": self.json_data,
            "assets": self.assets,
            "formulas": [f.to_dict() for f in self.formulas],
            "tables": [t.to_dict() for t in self.tables],
            "figures": [f.to_dict() for f in self.figures],
            "questions": [q.to_dict() for q in self.questions],
            "warnings": self.warnings,
            "metadata": self.metadata,
            "quality_score": self.quality_score,
        }
