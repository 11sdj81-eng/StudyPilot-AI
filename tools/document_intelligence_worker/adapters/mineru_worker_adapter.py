"""MinerU adapter — complex PDF → Markdown/JSON/images/formulas/tables."""

from __future__ import annotations

from pathlib import Path

from schemas.document_parse_schema import Block, DocumentParseResult, Page


def parse_with_mineru(
    input_path: Path,
    output_dir: Path,
    doc_id: str,
    max_pages: int = 10,
) -> DocumentParseResult:
    import tempfile
    import shutil
    from magic_pdf.pipe.UNIPipe import UNIPipe
    from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter

    warnings: list[str] = []

    # MinerU works with a directory of the PDF + a method that writes to disk
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Copy PDF into tmp
            pdf_copy = tmp / input_path.name
            shutil.copy2(input_path, pdf_copy)

            # Set up reader/writer
            image_dir = tmp / "images"
            image_dir.mkdir(exist_ok=True)

            reader_writer = DiskReaderWriter(image_dir)

            # Parse
            pipe = UNIPipe(str(pdf_copy), reader_writer)
            pipe.pipe_classify()
            pipe.pipe_parse()

            # Collect outputs
            content_list = pipe.pipe_mk_uni_format(tmp / "output.json", drop_mode="none")

            # Build result from MinerU output
            md_content = ""
            blocks: list[Block] = []
            all_text: list[str] = []

            if content_list:
                for i, item in enumerate(content_list[:500]):
                    item_type = item.get("type", "text")
                    text = item.get("text", "") or ""
                    all_text.append(text)

                    block_type = item_type
                    if block_type == "image":
                        block_type = "figure"
                    elif block_type == "table":
                        block_type = "table"
                    elif block_type == "equation" or block_type == "interline_equation":
                        block_type = "formula"

                    blocks.append(Block(
                        block_id=f"mineru_{i}",
                        block_type=block_type,
                        text=text[:5000] if isinstance(text, str) else str(text)[:5000],
                        bbox=item.get("bbox", [0, 0, 0, 0]) if isinstance(item.get("bbox"), list) else [0, 0, 0, 0],
                        confidence=0.9,
                        metadata={"mineru_type": item_type, "page": item.get("page_idx")},
                    ))

                md_content = pipe.pipe_mk_markdown(tmp / "output.md", drop_mode="none") or ""

            # Build pages
            full_text = "\n".join(all_text)
            pages = [Page(page_number=0, text=full_text[:100000], blocks=blocks)]

            # Copy output assets
            assets_dir = output_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            assets: list[str] = []
            for img in sorted(image_dir.glob("*")):
                if img.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    dest = assets_dir / "figures" / img.name
                    dest.parent.mkdir(exist_ok=True)
                    shutil.copy2(img, dest)
                    assets.append(str(dest))

            return DocumentParseResult(
                document_id=doc_id,
                file_path=str(input_path),
                file_type=input_path.suffix.lstrip("."),
                parser_used="mineru",
                success=True,
                is_scanned=False,
                pages=pages,
                markdown=md_content,
                assets=assets,
                warnings=warnings,
                metadata={
                    "blocks": len(blocks),
                    "markdown_chars": len(md_content),
                    "figures": sum(1 for b in blocks if b.block_type == "figure"),
                    "tables": sum(1 for b in blocks if b.block_type == "table"),
                    "formulas": sum(1 for b in blocks if b.block_type == "formula"),
                },
            )

    except Exception as e:
        # MinerU failed — report honestly
        return DocumentParseResult(
            document_id=doc_id,
            file_path=str(input_path),
            parser_used="mineru",
            success=False,
            warnings=[f"MinerU parse failed: {e}"],
        )
