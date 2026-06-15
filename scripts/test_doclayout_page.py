#!/usr/bin/env python3
"""Test DocLayout-YOLO on scanned textbook pages for layout detection and cropping.

Usage: python scripts/test_doclayout_page.py
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "data" / "outputs" / "v5_reports"
OUTPUT_DIR = ROOT / "data" / "parsed" / "doclayout_yolo"
CROP_DIR = OUTPUT_DIR / "crops"
REPORT_PATH = REPORT_DIR / "doclayout_yolo_report.json"


def _check_doclayout_available() -> bool:
    try:
        import doclayout_yolo  # noqa
        from ultralytics import YOLO  # noqa
        return True
    except ImportError:
        return False


def _extract_pages_from_pdf(
    pdf_path: Path, output_dir: Path, max_pages: int = 5
) -> list[Path]:
    """Render PDF pages as images using PyMuPDF."""
    import fitz

    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path] = []

    doc = fitz.open(str(pdf_path))
    try:
        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img_path = output_dir / f"page_{page_num:03d}.png"
            pix.save(str(img_path))
            image_paths.append(img_path)
            print(f"  Rendered page {page_num}: {img_path}")
    finally:
        doc.close()

    return image_paths


def _run_doclayout_on_page(
    model: Any, image_path: Path
) -> list[dict[str, Any]]:
    """Run DocLayout-YOLO layout detection on a page image."""
    import cv2
    import numpy as np

    results = model.predict(
        source=str(image_path),
        conf=0.25,
        iou=0.45,
        verbose=False,
    )

    regions: list[dict[str, Any]] = []
    if not results or len(results) == 0:
        return regions

    result = results[0]
    if result.boxes is None:
        return regions

    img = cv2.imread(str(image_path))
    h, w = img.shape[:2] if img is not None else (0, 0)

    class_names = result.names if hasattr(result, 'names') else {}

    for box in result.boxes:
        cls_id = int(box.cls[0]) if hasattr(box, 'cls') else -1
        conf = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
        xyxy = box.xyxy[0].cpu().numpy() if hasattr(box, 'xyxy') else None
        if xyxy is None:
            continue

        x1, y1, x2, y2 = [int(v) for v in xyxy]
        label = class_names.get(cls_id, f"class_{cls_id}")

        regions.append({
            "label": label,
            "class_id": cls_id,
            "confidence": round(conf, 4),
            "bbox": [x1, y1, x2, y2],
            "area": (x2 - x1) * (y2 - y1),
        })

    return regions


def _crop_regions(
    image_path: Path, regions: list[dict], output_dir: Path, page_num: int
) -> list[dict]:
    """Crop detected figure/table regions and save to output."""
    import cv2

    output_dir.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(image_path))
    if img is None:
        return []

    crops: list[dict] = []
    for i, region in enumerate(regions):
        label = region["label"]
        x1, y1, x2, y2 = region["bbox"]

        # Only crop figure/table/formula regions
        crop_types = {"figure", "table", "formula", "equation", "image", "chart"}
        if label.lower() not in crop_types:
            continue

        # Ensure bounds
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 <= x1 or y2 <= y1:
            continue

        crop = img[y1:y2, x1:x2]
        crop_path = output_dir / f"crop_p{page_num:03d}_{label}_{i}.png"
        cv2.imwrite(str(crop_path), crop)

        crops.append({
            "crop_path": str(crop_path),
            "label": label,
            "page": page_num,
            "bbox": [x1, y1, x2, y2],
            "confidence": region["confidence"],
            "width": x2 - x1,
            "height": y2 - y1,
        })

    return crops


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CROP_DIR.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "success": False,
        "page_count": 0,
        "region_count": 0,
        "figure_region_count": 0,
        "formula_region_count": 0,
        "table_region_count": 0,
        "question_region_count": 0,
        "crop_count": 0,
        "output_dir": str(CROP_DIR),
        "warnings": [],
    }

    if not _check_doclayout_available():
        report["warnings"].append("DocLayout-YOLO not available. Run: pip install doclayout-yolo ultralytics")
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print("[DocLayout] NOT AVAILABLE.")
        return

    print("[DocLayout] Available. Loading model...")

    try:
        from doclayout_yolo import YOLOv10
        model = YOLOv10.from_pretrained("juliozhao/DocLayout-YOLO-DocStructBench")
        print("  Model loaded: DocLayout-YOLO-DocStructBench")
    except Exception as e:
        # Fallback: try generic YOLO loading
        print(f"  Pre-trained loading failed: {e}")
        try:
            from ultralytics import YOLO
            model = YOLO("yolov10n.pt")  # fallback
            report["warnings"].append(f"Using fallback YOLO model (yolov10n.pt), not DocLayout-YOLO. Error: {e}")
        except Exception as e2:
            report["warnings"].append(f"Cannot load any model: {e2}")
            REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(f"[DocLayout] Cannot load model: {e2}")
            return

    # Find PDF - prefer textbook
    uploads = ROOT / "data" / "uploads" / "course_bb15e787"
    pdfs = sorted(uploads.rglob("*.pdf"))
    textbook = [p for p in pdfs if "电磁场" in p.name and "期末" not in p.name]
    if not textbook:
        report["warnings"].append("No textbook PDF found; using first available PDF.")
        textbook = pdfs[:1]
    pdf_path = textbook[0]

    print(f"[DocLayout] Processing: {pdf_path.name}")

    # Extract pages
    page_dir = OUTPUT_DIR / "pages"
    page_images = _extract_pages_from_pdf(pdf_path, page_dir, max_pages=3)
    report["page_count"] = len(page_images)

    # Detect layout on each page
    all_crops = []
    for i, img_path in enumerate(page_images):
        print(f"  Detecting layout on page {i}...")
        try:
            regions = _run_doclayout_on_page(model, img_path)
        except Exception as e:
            report["warnings"].append(f"Layout detection failed on page {i}: {e}")
            continue

        report["region_count"] += len(regions)

        for r in regions:
            label = r["label"].lower()
            if label in {"figure", "image", "chart", "picture"}:
                report["figure_region_count"] += 1
            elif label in {"formula", "equation"}:
                report["formula_region_count"] += 1
            elif label in {"table"}:
                report["table_region_count"] += 1
            elif label in {"question", "problem"}:
                report["question_region_count"] += 1

        print(f"    Found {len(regions)} regions: {[(r['label'], r['confidence']) for r in regions[:10]]}")

        # Crop figure/table regions
        crops = _crop_regions(img_path, regions, CROP_DIR, i)
        all_crops.extend(crops)

    report["crop_count"] = len(all_crops)
    report["success"] = report["region_count"] > 0

    if report["crop_count"] == 0:
        report["warnings"].append("No figure/table regions detected for cropping. The model may not have detected any.")
        report["next_action"] = "Try with a different PDF or adjust confidence threshold."
    else:
        report["next_action"] = f"{report['crop_count']} crops ready for FigureBank v2."

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DocLayout] Report: {REPORT_PATH}")
    print(f"[DocLayout] Success: {report['success']}, regions: {report['region_count']}, crops: {report['crop_count']}")
    print(f"  figure: {report['figure_region_count']}, formula: {report['formula_region_count']}, table: {report['table_region_count']}")


if __name__ == "__main__":
    main()
