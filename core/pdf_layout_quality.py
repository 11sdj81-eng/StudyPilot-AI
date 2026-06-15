"""Layout quality inspection for StudyPilot PDF v3.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.pdf_design_system import DESIGN_TOKENS


def inspect_layout_quality(pdf_paths: dict[str, str], output_path: str | Path = "data/outputs/layout_quality_report.json") -> dict[str, Any]:
    report = {"documents": {}, "large_blank_area_pages": [], "overcrowded_pages": [], "layout_warning_count": 0}
    for name, path in pdf_paths.items():
        doc_report = inspect_single_pdf_layout(path, name)
        report["documents"][name] = doc_report
        report["large_blank_area_pages"].extend([{"document": name, "page": p} for p in doc_report["large_blank_pages"]])
        report["overcrowded_pages"].extend([{"document": name, "page": p} for p in doc_report["overcrowded_pages"]])
    report["layout_warning_count"] = len(report["large_blank_area_pages"]) + len(report["overcrowded_pages"])
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def inspect_single_pdf_layout(pdf_path: str | Path, document_name: str = "") -> dict[str, Any]:
    min_ratio = DESIGN_TOKENS["layout"]["page_min_content_ratio"]
    max_ratio = DESIGN_TOKENS["layout"]["page_overcrowded_ratio"]
    ratios: list[float] = []
    large_blank: list[int] = []
    overcrowded: list[int] = []
    isolated_visual_pages: list[int] = []
    toc_sparse_pages: list[int] = []
    try:
        import fitz

        with fitz.open(pdf_path) as doc:
            for index, page in enumerate(doc, start=1):
                page_area = page.rect.width * page.rect.height
                blocks = page.get_text("blocks")
                drawings = page.get_drawings()
                images = page.get_images(full=True)
                content_area = 0.0
                text_chars = 0
                y_values: list[float] = []
                for block in blocks:
                    x0, y0, x1, y1, text = block[:5]
                    if str(text).strip():
                        text_chars += len(str(text).strip())
                        y_values.extend([y0, y1])
                        content_area += max(0.0, (x1 - x0) * (y1 - y0))
                visual_bonus = min(page_area * 0.22, (len(drawings) * 1300) + (len(images) * 26000))
                ink_ratio = (content_area + visual_bonus) / page_area
                vertical_ratio = 0.0
                if y_values:
                    top = max(0, min(y_values) - 18)
                    bottom = min(page.rect.height, max(y_values) + 18)
                    vertical_ratio = max(0.0, (bottom - top) / page.rect.height)
                density_ratio = min(0.88, text_chars / 1450)
                visual_ratio = min(0.36, len(images) * 0.16)
                ratio = min(1.0, max(ink_ratio, vertical_ratio * 0.75, density_ratio + visual_ratio))
                ratios.append(round(ratio, 3))
                text = page.get_text("text")
                has_substantial_content = text_chars >= 260 or len(images) > 0 or len(drawings) >= 12
                if index > 1 and ratio < min_ratio and not has_substantial_content:
                    large_blank.append(index)
                if ratio > max_ratio:
                    overcrowded.append(index)
                if len(images) + len(drawings) > 10 and len(text.strip()) < 80:
                    isolated_visual_pages.append(index)
                if "目录与使用建议" in text and ratio < 0.40:
                    toc_sparse_pages.append(index)
    except Exception as exc:
        return {"error": str(exc), "large_blank_pages": [0], "overcrowded_pages": [], "content_ratios": []}
    return {
        "pdf_path": str(Path(pdf_path).resolve()),
        "content_ratios": ratios,
        "large_blank_pages": large_blank,
        "overcrowded_pages": overcrowded,
        "isolated_visual_pages": isolated_visual_pages,
        "toc_sparse_pages": toc_sparse_pages,
        "average_content_ratio": round(sum(ratios) / len(ratios), 3) if ratios else 0,
    }
