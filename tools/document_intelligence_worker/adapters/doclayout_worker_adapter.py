"""DocLayout-YOLO adapter — layout detection + figure/table cropping."""

from __future__ import annotations

from pathlib import Path

import cv2
import fitz
from schemas.document_parse_schema import Block, DocumentParseResult, Page


def parse_with_doclayout(
    input_path: Path,
    output_dir: Path,
    doc_id: str,
    max_pages: int = 5,
    save_crops: str = "true",
) -> DocumentParseResult:
    from ultralytics import YOLO

    warnings: list[str] = []
    pages: list[Page] = []
    assets: list[str] = []

    pages_dir = output_dir / "assets" / "pages"
    crops_dir = output_dir / "assets" / "crops"
    pages_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    # Load model — try DocLayout-YOLO first, fallback to YOLOv8
    model = None
    try:
        from doclayout_yolo import YOLOv10
        model = YOLOv10.from_pretrained("juliozhao/DocLayout-YOLO-DocStructBench")
    except Exception:
        warnings.append("DocLayout-YOLO weights unavailable, using YOLOv8n fallback")
        model = YOLO("yolov8n.pt")

    doc = fitz.open(str(input_path))
    try:
        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]

            # Render page
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            img_path = pages_dir / f"page_{page_num:03d}.png"
            pix.save(str(img_path))
            assets.append(str(img_path))

            # Detect layout
            results = model.predict(source=str(img_path), conf=0.25, iou=0.45, verbose=False)
            blocks: list[Block] = []

            if results and results[0].boxes is not None:
                img = cv2.imread(str(img_path))
                class_names = results[0].names

                for i, box in enumerate(results[0].boxes):
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = [int(v) for v in xyxy]
                    label = class_names.get(cls_id, f"cls_{cls_id}")

                    # Map to block type
                    block_type = "text"
                    if label.lower() in ("figure", "image", "picture", "chart"):
                        block_type = "figure"
                    elif label.lower() in ("table",):
                        block_type = "table"
                    elif label.lower() in ("formula", "equation"):
                        block_type = "formula"
                    elif label.lower() in ("title", "header"):
                        block_type = "title"
                    elif label.lower() in ("question",):
                        block_type = "question"

                    crop_path = ""
                    if save_crops == "true" and block_type in ("figure", "table", "formula"):
                        h, w = img.shape[:2]
                        cx1, cy1 = max(0, x1), max(0, y1)
                        cx2, cy2 = min(w, x2), min(h, y2)
                        crop = img[cy1:cy2, cx1:cx2]
                        crop_file = crops_dir / f"crop_p{page_num}_{block_type}_{i}.png"
                        cv2.imwrite(str(crop_file), crop)
                        crop_path = str(crop_file)
                        assets.append(crop_path)

                    blocks.append(Block(
                        block_id=f"dl_p{page_num}_{i}",
                        block_type=block_type,
                        bbox=[x1, y1, x2, y2],
                        confidence=round(conf, 4),
                        asset_path=crop_path,
                        metadata={"label": label, "class_id": cls_id},
                    ))

            pages.append(Page(page_number=page_num, blocks=blocks))
    finally:
        doc.close()

    figure_count = sum(1 for p in pages for b in p.blocks if b.block_type == "figure")
    crop_count = sum(1 for p in pages for b in p.blocks if b.asset_path)

    return DocumentParseResult(
        document_id=doc_id,
        file_path=str(input_path),
        file_type=input_path.suffix.lstrip("."),
        parser_used="doclayout",
        success=len(pages) > 0,
        pages=pages,
        assets=assets,
        warnings=warnings,
        metadata={
            "figure_regions": figure_count,
            "crop_count": crop_count,
            "total_regions": sum(len(p.blocks) for p in pages),
        },
    )
