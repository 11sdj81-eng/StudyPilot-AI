"""Fallback document parser using local lightweight extractors."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence.parser_result import ParserAsset, ParserPage, ParserResult


SCAN_WARNING = "该文件可能是扫描版 PDF，当前只能做有限解析，建议后续接入 OCR / MinerU。"


def parse_with_fallback(file_path: str | Path) -> ParserResult:
    path = Path(file_path)
    file_type = path.suffix.lower().lstrip(".") or "unknown"
    if file_type == "pdf":
        return _parse_pdf(path)
    return ParserResult(
        file_path=str(path),
        file_type=file_type,
        is_scanned=False,
        pages=[],
        raw_text="",
        markdown="",
        warnings=[f"{file_type} 解析接口已预留，当前 fallback parser 未实现完整解析。"],
        metadata={"parser": "fallback"},
    )


def _parse_pdf(path: Path) -> ParserResult:
    pages: list[ParserPage] = []
    assets: list[ParserAsset] = []
    warnings: list[str] = []
    raw_parts: list[str] = []
    image_count = 0
    try:
        import fitz

        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                text = page.get_text("text")
                raw_parts.append(text)
                images = page.get_images(full=True)
                page_images = []
                for img_index, img in enumerate(images, start=1):
                    image_count += 1
                    asset = ParserAsset(
                        asset_id=f"page{page_index}_image{img_index}",
                        asset_type="image",
                        page_number=page_index,
                        path="",
                        description="PDF embedded image reference",
                        metadata={"xref": img[0] if img else None},
                    )
                    assets.append(asset)
                    page_images.append(asset.to_dict())
                pages.append(ParserPage(page_number=page_index, text=text, images=page_images))
    except Exception as exc:
        warnings.append(f"fallback PDF 解析失败：{exc}")
    raw_text = "\n".join(raw_parts)
    is_scanned = _looks_scanned(len(pages), raw_text, image_count)
    if is_scanned:
        warnings.append(SCAN_WARNING)
    markdown = "\n\n".join(f"## Page {page.page_number}\n\n{page.text.strip()}" for page in pages if page.text.strip())
    return ParserResult(
        file_path=str(path),
        file_type="pdf",
        is_scanned=is_scanned,
        pages=pages,
        raw_text=raw_text,
        markdown=markdown,
        assets=assets,
        warnings=warnings,
        metadata={"parser": "fallback_pdf", "page_count": len(pages), "image_count": image_count},
    )


def _looks_scanned(page_count: int, raw_text: str, image_count: int) -> bool:
    text_len = len((raw_text or "").strip())
    if page_count >= 3 and text_len < page_count * 80:
        return True
    if image_count >= max(3, page_count) and text_len < page_count * 120:
        return True
    return False
