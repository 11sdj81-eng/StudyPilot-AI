"""v4.0: Textbook asset extraction from uploaded PDFs.

Extract figures, formula regions, and example boxes directly from textbook
PDFs so the generation pipeline can embed original publisher-quality assets
instead of relying on AI-rendered approximations.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import fitz

from core.config import DATA_DIR

ASSET_DIR = DATA_DIR / "assets"


# ---- public API ------------------------------------------------------------

def extract_textbook_assets(
    pdf_path: str | Path,
    course_id: str,
    resource_id: str = "",
) -> dict:
    """Extract figures, formulas, and example boxes from a textbook PDF.

    Returns a summary dict with counts and paths.
    """
    path = Path(pdf_path)
    if not path.exists():
        return {"figures": 0, "formulas": 0, "examples": 0, "error": "PDF not found"}

    base = ASSET_DIR / course_id
    for sub in ["figures", "formulas", "examples"]:
        (base / sub).mkdir(parents=True, exist_ok=True)

    doc = fitz.open(path)
    assets: list[dict] = []

    # Detect whether this is a scanned/image-based PDF
    is_scanned = _is_scanned_pdf(doc)

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_number = page_num + 1

        page_w = page.rect.width
        page_h = page.rect.height
        page_area = page_w * page_h

        # ---- 1. Extract embedded images -----------------------------------
        raw_images = _extract_page_images(page, page_number, path.name, course_id, resource_id, base)

        if is_scanned:
            # For scanned PDFs: classify images by size, skip full-page scans
            # (they're too large and redundant with rendered page crops)
            for img_asset in raw_images:
                bbox = img_asset["bbox"]
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                area_ratio = (w * h) / page_area if page_area > 0 else 1.0

                if area_ratio > 0.85:
                    # Full-page scan — skip (use rendered page crops instead)
                    _cleanup_asset_file(img_asset)
                    continue
                elif area_ratio > 0.10:
                    # Sub-page image → actual figure, keep it
                    img_asset["asset_type"] = "figure"
                    assets.append(img_asset)
                else:
                    # Very small → decoration, skip
                    _cleanup_asset_file(img_asset)
                    continue

            # For scanned PDFs: also render pages as formula/figure/example crops
            # (text-based detection won't work on image-only pages)
            if page_number % 20 == 1 or page_number <= 10:
                _add_page_crop_asset(page, page_number, path.name, course_id, resource_id, base, assets, "formula_page")
            if page_number % 25 == 1:
                _add_page_crop_asset(page, page_number, path.name, course_id, resource_id, base, assets, "example_page")
            # Figure pages: sample pages likely to contain diagrams
            if page_number % 15 == 1 or page_number in [2, 3, 32, 33, 45, 46, 78, 79]:
                _add_page_crop_asset(page, page_number, path.name, course_id, resource_id, base, assets, "figure_page")
        else:
            # Text-based PDF: use text detection
            assets.extend(raw_images)
            formula_assets = _detect_formula_regions(page, page_number, path.name, course_id, resource_id, base)
            assets.extend(formula_assets)
            example_assets = _detect_example_boxes(page, page_number, path.name, course_id, resource_id, base)
            assets.extend(example_assets)

    doc.close()

    # Save manifest
    manifest_path = base / "asset_manifest.json"
    existing = []
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing.extend(assets)
    manifest_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "figures": sum(1 for a in assets if a["asset_type"] in ("figure", "figure_page")),
        "formulas": sum(1 for a in assets if a["asset_type"] in ("formula", "formula_page")),
        "examples": sum(1 for a in assets if a["asset_type"] in ("example", "example_page")),
        "total": len(assets),
        "is_scanned": is_scanned,
        "manifest_path": str(manifest_path),
    }


def get_course_assets(course_id: str) -> list[dict]:
    """Return all extracted assets for a course."""
    manifest = ASSET_DIR / course_id / "asset_manifest.json"
    if not manifest.exists():
        return []
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return []


def find_assets_for_keywords(course_id: str, keywords: list[str], top_n: int = 10) -> list[dict]:
    """Find textbook assets matching given keywords."""
    all_assets = get_course_assets(course_id)
    if not all_assets or not keywords:
        return all_assets[:top_n]

    scored = []
    for asset in all_assets:
        haystack = (
            (asset.get("title_guess", "") or "")
            + " "
            + " ".join(asset.get("related_keywords", []))
        ).lower()
        score = sum(1 for kw in keywords if kw.lower() in haystack)
        if score > 0:
            scored.append((score, asset))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:top_n]]


# ---- internal extractors ---------------------------------------------------

def _extract_page_images(
    page: fitz.Page, page_number: int, filename: str,
    course_id: str, resource_id: str, base: Path,
) -> list[dict]:
    """Extract embedded raster images from a page."""
    assets: list[dict] = []
    image_list = page.get_images(full=True)

    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            base_image = page.parent.extract_image(xref)
            if not base_image:
                continue
            image_bytes = base_image.get("image")
            if not image_bytes or len(image_bytes) < 2000:  # skip tiny images
                continue

            ext = base_image.get("ext", "png")
            asset_id = f"fig_{course_id}_{page_number}_{img_index}"
            img_path = base / "figures" / f"{asset_id}.{ext}"
            img_path.write_bytes(image_bytes)

            # Get image position on page
            bbox = _image_bbox_on_page(page, img_info)

            assets.append({
                "asset_id": asset_id,
                "course_id": course_id,
                "resource_id": resource_id,
                "source_pdf": filename,
                "page": page_number,
                "asset_type": "figure",
                "bbox": bbox,
                "title_guess": f"{Path(filename).stem} 第{page_number}页 图{img_index + 1}",
                "related_keywords": [],
                "image_path": str(img_path),
                "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception:
            continue

    return assets


def _detect_formula_regions(
    page: fitz.Page, page_number: int, filename: str,
    course_id: str, resource_id: str, base: Path,
) -> list[dict]:
    """Detect formula-like text blocks on a page and render them as images."""
    assets: list[dict] = []
    blocks = page.get_text("dict").get("blocks", [])
    page_rect = page.rect

    for block_index, block in enumerate(blocks):
        if block.get("type") != 0:  # text block only
            continue

        text = _block_text(block)
        if not _looks_like_formula(text):
            continue

        bbox = list(block["bbox"])
        # Expand bbox slightly for context
        bbox[0] = max(0, bbox[0] - 10)
        bbox[1] = max(0, bbox[1] - 5)
        bbox[2] = min(page_rect.width, bbox[2] + 10)
        bbox[3] = min(page_rect.height, bbox[3] + 5)

        # Skip if bbox is too large (whole page) or too small
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w > page_rect.width * 0.8 or h < 8:
            continue

        asset_id = f"form_{course_id}_{page_number}_{block_index}"
        img_path = base / "formulas" / f"{asset_id}.png"

        # Render the formula region at high resolution
        _render_region_to_image(page, bbox, img_path, zoom=3.0)

        if img_path.exists() and img_path.stat().st_size > 500:
            keywords = _formula_keywords(text)
            assets.append({
                "asset_id": asset_id,
                "course_id": course_id,
                "resource_id": resource_id,
                "source_pdf": filename,
                "page": page_number,
                "asset_type": "formula",
                "bbox": bbox,
                "title_guess": _formula_title(text),
                "related_keywords": keywords,
                "image_path": str(img_path),
                "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    return assets


def _detect_example_boxes(
    page: fitz.Page, page_number: int, filename: str,
    course_id: str, resource_id: str, base: Path,
) -> list[dict]:
    """Detect example/definition boxes on a page."""
    assets: list[dict] = []

    # Strategy 1: Look for "例"/"例题"/"Example" text near rectangle drawings
    drawings = page.get_drawings()
    blocks = page.get_text("dict").get("blocks", [])

    # Find rectangles that might be example boxes
    rect_candidates = []
    for drawing in drawings:
        for item in drawing.get("items", []):
            if item[0] == "re":  # rectangle
                r = item[1]  # the rect coordinates
                w, h = r.width, r.height
                if 100 < w < page.rect.width * 0.95 and 40 < h < page.rect.height * 0.6:
                    rect_candidates.append(fitz.Rect(r))

    # Strategy 2: Find text blocks containing example markers
    example_keywords = ["例题", "例", "Example", "习题", "题目", "定义", "定理", "证明"]
    for block_index, block in enumerate(blocks):
        if block.get("type") != 0:
            continue
        text = _block_text(block)
        if not any(kw in text for kw in example_keywords):
            continue

        bbox = list(block["bbox"])

        # Try to extend bbox to include nearby example content
        # Check if this block is inside a rectangle
        block_rect = fitz.Rect(bbox)
        for cand_rect in rect_candidates:
            if cand_rect.contains(block_rect) or cand_rect.intersects(block_rect):
                bbox = list(cand_rect)
                break

        # Expand moderately
        bbox[0] = max(0, bbox[0] - 15)
        bbox[1] = max(0, bbox[1] - 10)
        bbox[2] = min(page.rect.width, bbox[2] + 15)
        bbox[3] = min(page.rect.height, bbox[3] + 15)

        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if h < 30 or w < 100:
            continue

        asset_id = f"ex_{course_id}_{page_number}_{block_index}"
        img_path = base / "examples" / f"{asset_id}.png"
        _render_region_to_image(page, bbox, img_path, zoom=2.5)

        if img_path.exists() and img_path.stat().st_size > 1000:
            assets.append({
                "asset_id": asset_id,
                "course_id": course_id,
                "resource_id": resource_id,
                "source_pdf": filename,
                "page": page_number,
                "asset_type": "example",
                "bbox": bbox,
                "title_guess": _example_title(text),
                "related_keywords": _example_keywords(text),
                "image_path": str(img_path),
                "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    return assets


# ---- scanned PDF helpers ---------------------------------------------------

def _is_scanned_pdf(doc: fitz.Document) -> bool:
    """Detect whether a PDF is primarily image-based (scanned)."""
    sample_pages = min(10, len(doc))
    text_chars = 0
    for i in range(sample_pages):
        text_chars += len(doc[i].get_text("text").strip())
    # If average chars per page < 20, it's likely scanned
    return (text_chars / sample_pages) < 20


def _add_page_crop_asset(
    page: fitz.Page, page_number: int, filename: str,
    course_id: str, resource_id: str, base: Path,
    assets: list[dict], asset_type: str,
) -> None:
    """Add a full-page render as a textbook asset (for scanned PDFs)."""
    asset_id = f"{asset_type}_{course_id}_{page_number}"
    if "formula" in asset_type:
        img_path = base / "formulas" / f"{asset_id}.png"
    elif "example" in asset_type:
        img_path = base / "examples" / f"{asset_id}.png"
    else:
        img_path = base / "figures" / f"{asset_id}.png"
    img_path.parent.mkdir(parents=True, exist_ok=True)

    _render_region_to_image(page, list(page.rect), img_path, zoom=1.5)

    if img_path.exists() and img_path.stat().st_size > 2000:
        ref_map = {"formula_page": "公式参考", "example_page": "例题参考", "figure_page": "插图参考"}
        type_label = asset_type if asset_type in ref_map else "formula_page"
        assets.append({
            "asset_id": asset_id,
            "course_id": course_id,
            "resource_id": resource_id,
            "source_pdf": filename,
            "page": page_number,
            "asset_type": type_label,
            "bbox": list(page.rect),
            "title_guess": f"{Path(filename).stem} 第{page_number}页（{ref_map.get(type_label, '参考')}）",
            "related_keywords": [],
            "image_path": str(img_path),
            "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_scanned_page": True,
        })


# ---- detection helpers -----------------------------------------------------

def _block_text(block: dict) -> str:
    """Extract plain text from a text block dict."""
    parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            parts.append(span.get("text", ""))
    return "".join(parts).strip()


def _looks_like_formula(text: str) -> bool:
    """Heuristic: does this text block look like it contains math?"""
    if len(text) < 5 or len(text) > 500:
        return False

    # Math symbol density
    math_symbols = set("∫∮∂∇√∑∏∞→⇒⇔±×·÷≤≥≠≈≡≪≫∝∼∧∨⊕⊗∈∉⊂⊃∪∩∅")
    greek = set("αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ")
    latex_markers = ["frac", "sqrt", "int", "sum", "lim", "partial", "mathbf"]

    symbols = sum(1 for c in text if c in math_symbols or c in greek)
    # Also check for LaTeX-like patterns
    latex_score = sum(1 for marker in latex_markers if marker in text.lower())

    # Formula-like if: has math symbols, or has LaTeX, or is short and centered-like
    if symbols >= 2 or latex_score >= 1:
        return True
    # Short line with = sign and greek/symbols → likely formula
    if len(text) < 80 and "=" in text and symbols >= 1:
        return True
    return False


def _formula_title(text: str) -> str:
    """Generate a short title for a formula block."""
    cleaned = text.strip()[:60]
    return f"公式：{cleaned}"


def _formula_keywords(text: str) -> list[str]:
    """Extract keyword hints from formula text."""
    keywords = []
    if "高斯" in text or "Gauss" in text:
        keywords.append("高斯定理")
    if "库仑" in text or "Coulomb" in text:
        keywords.append("库仑定律")
    if "镜像" in text:
        keywords.append("镜像法")
    if "电容" in text:
        keywords.append("电容")
    if "电位" in text or "电势" in text:
        keywords.append("电位")
    if "边界" in text:
        keywords.append("边界条件")
    if "能量" in text:
        keywords.append("电场能量")
    if "∇" in text or "梯度" in text:
        keywords.append("梯度")
    if "∮" in text or "通量" in text:
        keywords.append("通量")
    if "ε" in text or "ε₀" in text:
        keywords.append("介电常数")
    return keywords[:5]


def _example_title(text: str) -> str:
    """Generate a title for an example/definition box."""
    for kw in ["例题", "例", "Example"]:
        if kw in text:
            idx = text.find(kw)
            return text[idx:idx + 30].strip()
    return text[:40].strip()


def _example_keywords(text: str) -> list[str]:
    """Extract keywords from example text."""
    return _formula_keywords(text)


def _image_bbox_on_page(page: fitz.Page, img_info: tuple) -> list[float]:
    """Try to find the bounding box of an embedded image on the page."""
    xref = img_info[0]
    # Search for image placement in page content
    blocks = page.get_text("dict").get("blocks", [])
    for block in blocks:
        if block.get("type") == 1:  # image block
            return list(block["bbox"])
    # Fallback: return a reasonable default
    return [50, 50, page.rect.width - 50, page.rect.height - 50]


def _cleanup_asset_file(asset: dict) -> None:
    """Remove the image file for a skipped asset."""
    try:
        p = Path(asset.get("image_path", ""))
        if p.exists():
            p.unlink()
    except Exception:
        pass


def _render_region_to_image(page: fitz.Page, bbox: list[float], output_path: Path, zoom: float = 3.0) -> None:
    """Render a page region to a high-resolution PNG image."""
    clip = fitz.Rect(bbox)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csRGB)
    pix.save(str(output_path))


# ---- backward compatibility with asset_id format used in PDF rendering -----

def format_asset_ref(asset: dict, index: int = 1) -> str:
    """Format an asset as a Markdown image reference for PDF embedding."""
    asset_type_cn = {"figure": "教材原图", "formula": "教材公式", "example": "教材例题"}
    atype = asset_type_cn.get(asset.get("asset_type", ""), "教材资产")
    page = asset.get("page", "?")
    path = asset.get("image_path", "")
    title = asset.get("title_guess", "教材资产")

    return (
        f"![{atype}：{title}]({path})\n\n"
        f"*{atype}，来源：{asset.get('source_pdf', '教材')} 第{page}页*\n"
    )
