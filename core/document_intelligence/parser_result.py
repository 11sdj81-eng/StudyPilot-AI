"""Standard parser result objects for StudyPilot v3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ParserAsset:
    asset_id: str
    asset_type: str
    page_number: int
    path: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParserPage:
    page_number: int
    text: str = ""
    blocks: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParserResult:
    file_path: str
    file_type: str
    is_scanned: bool
    pages: list[ParserPage]
    raw_text: str
    markdown: str
    assets: list[ParserAsset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["pages"] = [page.to_dict() for page in self.pages]
        data["assets"] = [asset.to_dict() for asset in self.assets]
        return data
