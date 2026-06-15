"""Source image asset extraction interface for StudyPilot v3.1.

This module records source image slots from Document Intelligence results.  It
does not pretend that scanned textbook figures have been precisely cropped when
the parser cannot provide bounding boxes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def collect_source_image_assets(parser_results: list[dict[str, Any]], output_root: str | Path = "data/teaching_assets/engineering/electromagnetic_static_chapter1") -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for result in parser_results:
        source_file = Path(result.get("file_path", "")).name
        for page in result.get("pages", []):
            for image in page.get("images", []):
                assets.append(
                    {
                        "source_file": source_file,
                        "page": page.get("page_number"),
                        "bbox": image.get("metadata", {}).get("bbox"),
                        "confidence": 0.35 if result.get("is_scanned") else 0.55,
                        "possible_concept": "",
                        "image_path": image.get("path", ""),
                        "note": "仅记录来源图像槽位；当前未执行精确教材/试卷图裁剪。",
                    }
                )
    return assets
