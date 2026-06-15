"""PDF image extractor using PyMuPDF for textbook and exam paper PDFs.

Handles both digital and scanned PDFs.  For scanned PDFs, extracts full-page
renders and marks them appropriately — not pretending they're cropped figures.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.figure_engine.figure_objects import FigureObject, SourceType

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Thresholds
MIN_FIGURE_WIDTH = 120   # px — below this is likely noise/icon
MIN_FIGURE_HEIGHT = 80
SCANNED_PAGE_AREA_RATIO = 0.6  # if image covers >60% of page, likely scanned page
MAX_FIGURES_PER_PAGE = 20      # safety cap


class PdfFigureExtractor:
    """Extract embedded images from PDF files."""

    def __init__(self, output_dir: str | Path = "data/figure_bank/_extracted"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures: list[FigureObject] = []
        self._figure_counter = 0

    def extract_from_file(
        self,
        pdf_path: str | Path,
        source_type: str = SourceType.UNKNOWN,
        concept_id: str | None = None,
        max_pages: int | None = None,
    ) -> list[FigureObject]:
        """Extract images from a single PDF file."""
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is not installed. Install with: pip install PyMuPDF")

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        figures: list[FigureObject] = []

        try:
            total_pages = min(len(doc), max_pages or len(doc))
            for page_num in range(total_pages):
                page = doc[page_num]
                page_figures = self._extract_page_images(
                    page, page_num, pdf_path, source_type, concept_id
                )
                figures.extend(page_figures)
        finally:
            doc.close()

        self.figures.extend(figures)
        return figures

    def extract_from_directory(
        self,
        directory: str | Path,
        source_type_mapping: dict[str, str] | None = None,
    ) -> list[FigureObject]:
        """Extract images from all PDFs in a directory (recursive).

        source_type_mapping: dict of filename substring -> source_type, e.g.
            {"textbook": "textbook", "exam": "past_paper", "试卷": "past_paper"}
        """
        directory = Path(directory)
        figures: list[FigureObject] = []

        mapping = source_type_mapping or _default_source_type_mapping

        for pdf_file in sorted(directory.rglob("*.pdf")):
            fname = pdf_file.name.lower()
            inferred_type = SourceType.UNKNOWN
            for key, stype in mapping.items():
                if key.lower() in fname:
                    inferred_type = stype
                    break

            try:
                page_figures = self.extract_from_file(pdf_file, source_type=inferred_type)
                figures.extend(page_figures)
            except Exception as e:
                print(f"  [WARN] Failed to extract from {pdf_file.name}: {e}")
                continue

        return figures

    def _extract_page_images(
        self,
        page: fitz.Page,
        page_num: int,
        pdf_path: Path,
        source_type: str,
        concept_id: str | None,
    ) -> list[FigureObject]:
        """Extract images from a single PDF page."""
        figures: list[FigureObject] = []
        pdf_name = pdf_path.name
        page_w = page.rect.width
        page_h = page.rect.height
        page_area = page_w * page_h
        has_embedded_images = False

        # Try extracting embedded images
        image_list = page.get_images(full=True)
        if image_list:
            has_embedded_images = True
            for img_idx, img_info in enumerate(image_list[:MAX_FIGURES_PER_PAGE]):
                xref = img_info[0]
                try:
                    base_image = page.parent.extract_image(xref)
                    if not base_image or "image" not in base_image:
                        continue

                    img_bytes = base_image["image"]
                    ext = base_image.get("ext", "png")
                    w = base_image.get("width", 0)
                    h = base_image.get("height", 0)

                    if w < MIN_FIGURE_WIDTH or h < MIN_FIGURE_HEIGHT:
                        continue  # skip tiny images (icons, logos, noise)

                    # Get bbox on page
                    bbox = self._get_image_bbox(page, img_info, page_w, page_h)
                    is_full_page = self._is_full_page_scan(bbox, page_area)

                    figure_id = _make_figure_id(pdf_name, page_num, img_idx)
                    out_path = self.output_dir / f"{figure_id}.{ext}"
                    out_path.write_bytes(img_bytes)

                    figure = FigureObject(
                        figure_id=figure_id,
                        concept_id=concept_id,
                        source_type=SourceType.SCANNED_PAGE if is_full_page else source_type,
                        source_file=pdf_name,
                        source_page=page_num,
                        bbox=bbox,
                        image_path=str(out_path.resolve()),
                        caption=None,
                        ocr_text=None,
                        tags=[],
                        quality_score=0.0,
                        match_score=0.0,
                        usability_score=0.0,
                        width=w,
                        height=h,
                        aspect_ratio=round(w / h, 4) if h else None,
                        has_text_overlap_risk=is_full_page,
                        has_low_resolution_risk=(w < 400 or h < 300),
                        has_noise_risk=False,
                        metadata={
                            "ext": ext,
                            "xref": xref,
                            "is_full_page": is_full_page,
                            "page_dimensions": (int(page_w), int(page_h)),
                        },
                    )
                    figures.append(figure)
                    self._figure_counter += 1

                except Exception as e:
                    print(f"  [WARN] Failed to extract image xref={xref} on page {page_num}: {e}")
                    continue

        # For scanned PDFs: if no meaningful embedded images found, render full page
        if not has_embedded_images:
            figure = self._render_page_as_figure(page, page_num, pdf_name, source_type, page_w, page_h)
            if figure:
                figures.append(figure)

        return figures

    def _render_page_as_figure(
        self,
        page: fitz.Page,
        page_num: int,
        pdf_name: str,
        source_type: str,
        page_w: float,
        page_h: float,
    ) -> FigureObject | None:
        """Render an entire page as an image (for scanned PDFs)."""
        try:
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for readability
            pix = page.get_pixmap(matrix=mat)
            figure_id = _make_figure_id(pdf_name, page_num, -1)
            out_path = self.output_dir / f"{figure_id}.png"
            pix.save(str(out_path))

            return FigureObject(
                figure_id=figure_id,
                concept_id=None,
                source_type=SourceType.SCANNED_PAGE,
                source_file=pdf_name,
                source_page=page_num,
                bbox=None,  # full page
                image_path=str(out_path.resolve()),
                caption=None,
                ocr_text=None,
                tags=["scanned_page", "needs_cropping"],
                quality_score=0.0,
                match_score=0.0,
                usability_score=0.0,
                width=pix.width,
                height=pix.height,
                aspect_ratio=round(pix.width / pix.height, 4) if pix.height else None,
                has_text_overlap_risk=True,
                has_low_resolution_risk=False,
                has_noise_risk=True,
                metadata={
                    "is_full_page_scan": True,
                    "needs_manual_crop": True,
                    "page_dimensions": (int(page_w), int(page_h)),
                    "render_zoom": 2.0,
                },
            )
        except Exception as e:
            print(f"  [WARN] Failed to render page {page_num}: {e}")
            return None

    def _get_image_bbox(
        self,
        page: fitz.Page,
        img_info: tuple,
        page_w: float,
        page_h: float,
    ) -> tuple[int, int, int, int] | None:
        """Find the bounding box of an embedded image on the page."""
        try:
            xref = img_info[0]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") == 1:  # image block
                    for img_block in block.get("images", []):
                        if img_block.get("xref") == xref:
                            b = img_block["bbox"]
                            return (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
        except Exception:
            pass
        return None

    def _is_full_page_scan(self, bbox: tuple | None, page_area: float) -> bool:
        """Determine if the image covers most of the page (scanned page)."""
        if bbox is None:
            return True
        x0, y0, x1, y1 = bbox
        img_area = (x1 - x0) * (y1 - y0)
        return (img_area / page_area) > SCANNED_PAGE_AREA_RATIO if page_area > 0 else False

    def generate_extraction_report(self, output_path: str | Path | None = None) -> dict[str, Any]:
        """Generate extraction report in JSON format."""
        report = {
            "extraction_time": datetime.now(timezone.utc).isoformat(),
            "total_extracted": len(self.figures),
            "by_source_type": {},
            "scanned_pages": 0,
            "full_page_figures": 0,
            "low_resolution_count": 0,
            "figures": [],
        }

        for f in self.figures:
            st = f.source_type
            report["by_source_type"][st] = report["by_source_type"].get(st, 0) + 1
            if f.source_type == SourceType.SCANNED_PAGE:
                report["scanned_pages"] += 1
            if f.metadata.get("is_full_page"):
                report["full_page_figures"] += 1
            if f.has_low_resolution_risk:
                report["low_resolution_count"] += 1
            report["figures"].append(f.to_dict())

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        return report


def _make_figure_id(pdf_name: str, page_num: int, img_idx: int) -> str:
    """Generate a unique figure ID from PDF name, page, and image index."""
    slug = Path(pdf_name).stem[:30].replace(" ", "_").replace(".", "_")
    return f"fig_{slug}_p{page_num}_{img_idx}"


_default_source_type_mapping = {
    "textbook": "textbook",
    "教材": "textbook",
    "电磁场与电磁波": "textbook",
    "概率论与随机过程": "textbook",
    "exam": "past_paper",
    "试卷": "past_paper",
    "期末": "past_paper",
    "pastpaper": "past_paper",
    "真题": "past_paper",
    "ppt": "ppt",
    "课件": "ppt",
    "lecture": "ppt",
    "讲义": "note",
    "note": "note",
}
