"""User-visible content blocks for the StudyPilot PDF v4 engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ContentBlock:
    id: str
    block_type: str
    pdf_type: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    render_priority: int = 50
    allow_page_break: bool = True
    keep_together: bool = False
    user_visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TextBlock(ContentBlock):
    pass


class HeadingBlock(ContentBlock):
    pass


class FormulaBlock(ContentBlock):
    pass


class FigureBlock(ContentBlock):
    pass


class ExampleBlock(ContentBlock):
    pass


class ProblemBlock(ContentBlock):
    pass


class SolutionBlock(ContentBlock):
    pass


class TipBlock(ContentBlock):
    pass


class MistakeBlock(ContentBlock):
    pass


class RubricBlock(ContentBlock):
    pass


class VariantBlock(ContentBlock):
    pass


class ChecklistBlock(ContentBlock):
    pass


class ReferenceBlock(ContentBlock):
    pass


class PageBreakBlock(ContentBlock):
    pass


class TwoColumnBlock(ContentBlock):
    pass


def visible_blocks(blocks: list[ContentBlock]) -> list[ContentBlock]:
    return sorted([block for block in blocks if block.user_visible], key=lambda b: b.render_priority)
