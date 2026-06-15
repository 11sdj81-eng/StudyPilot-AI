"""PyMuPDF/python-pptx fallback parser for Document Intelligence v5."""

from __future__ import annotations

import hashlib
from pathlib import Path

from core.document_intelligence_v5.base_parser import BaseDocumentParser
from core.document_intelligence_v5.document_blocks import (
    DocumentBlock,
    DocumentParseResult,
    FigureBlock,
    PageBlock,
    SourceRef,
)


SCAN_WARNING = "当前环境未安装 MinerU / PaddleOCR / DocLayout-YOLO，已使用 fallback，解析质量有限。"


class FallbackParser(BaseDocumentParser):
    name = "fallback"
    supported_extensions = {"pdf", "pptx", "ppt", "docx", "png", "jpg", "jpeg", "webp", "txt", "md"}

    def available(self) -> bool:
        return True

    def parse(self, file_path: str | Path, output_dir: str | Path = "data/parsed/v5") -> DocumentParseResult:
        path = Path(file_path)
        ext = path.suffix.lower().lstrip(".")
        if ext == "pdf":
            return self._parse_pdf(path)
        if ext in {"txt", "md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            block = DocumentBlock(
                block_id="text_1",
                page_number=1,
                block_type="text",
                text=text,
                confidence=0.8,
                source_ref=SourceRef(path.name, 1, parser_name=self.name, confidence=0.8),
            )
            return DocumentParseResult(
                document_id=_doc_id(path),
                file_path=str(path),
                file_type=ext,
                parser_name=self.name,
                is_scanned=False,
                pages=[PageBlock(page_number=1, text=text, blocks=[block])],
                markdown=text,
                quality_score=0.55,
                warnings=[SCAN_WARNING],
                metadata={"fallback_reason": "plain text parser"},
            )
        return DocumentParseResult(
            document_id=_doc_id(path),
            file_path=str(path),
            file_type=ext,
            parser_name=self.name,
            is_scanned=False,
            warnings=[SCAN_WARNING, f"{ext} fallback parser only records file metadata."],
            quality_score=0.2,
        )

    def _parse_pdf(self, path: Path) -> DocumentParseResult:
        import fitz

        pages: list[PageBlock] = []
        figures: list[FigureBlock] = []
        assets: list[dict] = []
        text_parts: list[str] = []
        image_count = 0
        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                text = page.get_text("text")
                text_parts.append(text)
                blocks = []
                if text.strip():
                    blocks.append(
                        DocumentBlock(
                            block_id=f"p{page_index}_text",
                            page_number=page_index,
                            block_type="text",
                            text=text,
                            bbox=None,
                            confidence=0.55,
                            source_ref=SourceRef(path.name, page_index, parser_name=self.name, confidence=0.55),
                        )
                    )
                for img_idx, img in enumerate(page.get_images(full=True), start=1):
                    image_count += 1
                    fig = FigureBlock(
                        block_id=f"p{page_index}_image_{img_idx}",
                        page_number=page_index,
                        block_type="figure",
                        text="",
                        confidence=0.25,
                        source_ref=SourceRef(path.name, page_index, parser_name=self.name, confidence=0.25),
                        image_path="",
                        caption="fallback image reference; not a precise crop",
                        metadata={"xref": img[0] if img else None, "full_page_risk": True},
                    )
                    figures.append(fig)
                    assets.append(fig.to_dict())
                pages.append(PageBlock(page_number=page_index, text=text, blocks=blocks))
        raw_text = "\n".join(text_parts)
        is_scanned = _looks_scanned(len(pages), raw_text, image_count)
        warnings = [SCAN_WARNING]
        if is_scanned:
            warnings.append("该文件可能是扫描版 PDF，fallback 只能得到整页/嵌入图片引用，不能高置信裁剪图表公式。")
        return DocumentParseResult(
            document_id=_doc_id(path),
            file_path=str(path),
            file_type="pdf",
            parser_name=self.name,
            is_scanned=is_scanned,
            pages=pages,
            markdown="\n\n".join(f"## Page {p.page_number}\n\n{p.text}" for p in pages if p.text.strip()),
            json_data={"page_count": len(pages), "image_count": image_count},
            assets=assets,
            figures=figures,
            warnings=warnings,
            metadata={"page_count": len(pages), "image_count": image_count},
            quality_score=0.35 if is_scanned else 0.55,
        )


def detect_scanned_pdf(file_path: str | Path) -> bool:
    try:
        import fitz

        path = Path(file_path)
        if path.suffix.lower() != ".pdf":
            return False
        with fitz.open(path) as doc:
            page_count = len(doc)
            text_len = sum(len(page.get_text("text").strip()) for page in doc[: min(page_count, 8)])
            image_count = sum(len(page.get_images(full=True)) for page in doc[: min(page_count, 8)])
        sampled_pages = min(page_count, 8)
        return _looks_scanned(sampled_pages, "x" * text_len, image_count)
    except Exception:
        return False


def _looks_scanned(page_count: int, raw_text: str, image_count: int) -> bool:
    text_len = len((raw_text or "").strip())
    if page_count >= 3 and text_len < page_count * 80:
        return True
    if image_count >= max(3, page_count) and text_len < page_count * 120:
        return True
    return False


def _doc_id(path: Path) -> str:
    return hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()[:12]
