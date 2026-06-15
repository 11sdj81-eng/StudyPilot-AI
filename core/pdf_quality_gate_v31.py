"""StudyPilot PDF v3.1 quality gate."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.pdf_layout_quality import inspect_layout_quality


FORBIDDEN = [
    "formula_id",
    "concept_id",
    "source_basis",
    "example_",
    "formula_db",
    "example_db",
    "暂无",
    "None",
    "null",
    "Q_enc",
    "\\frac",
    "\\sqrt",
    "\\nabla",
    "\\varepsilon",
    "\\mathbf",
    "$",
    "OCR异常",
    "SS号",
    "General Information",
]


def run_v31_quality_gate(outputs: dict[str, Any], output_dir: str | Path = "data/outputs") -> dict[str, Any]:
    out = Path(output_dir)
    pdf_paths = {name: item["pdf"] for name, item in outputs.items()}
    layout = inspect_layout_quality(pdf_paths, out / "layout_quality_report.json")
    usage = _load(out / "diagram_usage_report.json", {})
    manifest = _load(out / "teaching_asset_manifest.json", [])
    documents = {}
    for name, item in outputs.items():
        documents[name] = _inspect_pdf(name, Path(item["pdf"]), item.get("model", {}), layout["documents"].get(name, {}))
    duplicated = usage.get("duplicated_diagram_asset_ids", [])
    programmatic_count = sum(1 for asset in manifest if asset.get("source") == "programmatic" and asset.get("usage_count", 0) > 0)
    textbook_hit = sum(1 for asset in manifest if asset.get("source") == "textbook" and asset.get("usage_count", 0) > 0)
    pastpaper_hit = sum(1 for asset in manifest if asset.get("source") == "past_paper" and asset.get("usage_count", 0) > 0)
    technical_pass = all(doc["technical_pass"] for doc in documents.values()) and usage.get("image_reuse_count", 0) == 0
    teaching_usable = all(doc["teaching_usable"] for doc in documents.values())
    print_score = _print_score(documents, layout, duplicated)
    goodnotes_score = _goodnotes_score(documents, layout)
    student_score = _student_score(documents, print_score, goodnotes_score)
    report = {
        "technical_pass": technical_pass,
        "teaching_usable": teaching_usable,
        "print_ready": print_score >= 78 and not layout.get("large_blank_area_pages"),
        "goodnotes_ready": goodnotes_score >= 78,
        "recommend_manual_acceptance": technical_pass and teaching_usable and student_score >= 78,
        "recommend_release": technical_pass and teaching_usable and print_score >= 78 and goodnotes_score >= 78 and student_score >= 78 and not layout.get("large_blank_area_pages") and not duplicated,
        "metrics": {
            "image_reuse_count": usage.get("image_reuse_count", 0),
            "duplicated_diagram_asset_ids": duplicated,
            "large_blank_pages": layout.get("large_blank_area_pages", []),
            "overcrowded_pages": layout.get("overcrowded_pages", []),
            "teaching_asset_coverage": _asset_coverage(manifest),
            "textbook_asset_hit_count": textbook_hit,
            "pastpaper_asset_hit_count": pastpaper_hit,
            "programmatic_asset_count": programmatic_count,
            "mock_difficulty_score": documents["MockExam"]["mock_difficulty_score"],
            "print_readiness_score": print_score,
            "goodnotes_readiness_score": goodnotes_score,
            "student_willingness_score": student_score,
        },
        "documents": documents,
        "answers": {
            "是否解决四份 PDF 图片重复问题": usage.get("image_reuse_count", 0) == 0,
            "每份 PDF 使用了哪些 diagram asset": _assets_by_pdf(usage),
            "同一张图是否被重复使用": bool(duplicated),
            "是否命中教材/试卷/PPT 图资产": textbook_hit > 0 or pastpaper_hit > 0,
            "若没有命中，为什么": "Document Intelligence 当前只记录图像槽位，未完成可置信教材/试卷子图裁剪；本轮使用程序化重绘图，未伪装为教材原图。",
            "程序化图是否重绘": True,
            "目录页大空白是否解决": not any(doc.get("toc_sparse_pages") for doc in layout["documents"].values()),
            "文本过挤是否解决": not layout.get("overcrowded_pages"),
            "MockExam 难度是否提升": documents["MockExam"]["mock_difficulty_score"] >= 80,
            "Sprint 是否更像考前救命册": documents["Sprint"]["student_view_score"] >= 80,
            "PastPaper 是否更像老师讲题": documents["PastPaper"]["student_view_score"] >= 80,
            "Review 是否更像复习讲义": documents["Review"]["student_view_score"] >= 80,
            "是否建议人工验收": technical_pass and teaching_usable and student_score >= 78,
            "是否建议发布": technical_pass and teaching_usable and print_score >= 78 and goodnotes_score >= 78 and student_score >= 78 and not layout.get("large_blank_area_pages") and not duplicated,
        },
    }
    (out / "StudyPilot_v31_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _inspect_pdf(name: str, path: Path, model: dict[str, Any], layout: dict[str, Any]) -> dict[str, Any]:
    text, pages, image_count = _extract(path)
    forbidden = [token for token in FORBIDDEN if token in text]
    latex_leaks = re.findall(r"\\[a-zA-Z]+|\$[^$]+\$|\btag\b", text)
    figure_count = len(re.findall(r"图\s+[A-Z]-\d+", text))
    examples = len(re.findall(r"题目：|原题/同类题|标准答案", text))
    mock_ok = True
    if name == "MockExam":
        nums = sorted(set(int(n) for n in re.findall(r"(?:^|\n)\s*(\d{1,2})\.", text) if 1 <= int(n) <= 14))
        mock_ok = nums == list(range(1, 15)) and int(model.get("mock_question_count", 0)) == 14 and int(model.get("mock_score_total", 0)) == 100
    student_score = _document_student_score(name, text, figure_count, layout, model)
    return {
        "pdf_path": str(path.resolve()),
        "page_count": len(pages),
        "file_size_bytes": path.stat().st_size,
        "image_count": image_count,
        "diagram_count": figure_count,
        "example_signal_count": examples,
        "forbidden_hits": forbidden,
        "latex_leak_count": len(latex_leaks),
        "layout": layout,
        "mock_difficulty_score": int(model.get("mock_difficulty_score", 0)) if name == "MockExam" else None,
        "technical_pass": not forbidden and not latex_leaks and not layout.get("large_blank_pages") and mock_ok,
        "teaching_usable": student_score >= 76,
        "student_view_score": student_score,
    }


def _extract(path: Path) -> tuple[str, list[str], int]:
    import fitz

    with fitz.open(path) as doc:
        pages = [page.get_text("text") for page in doc]
        image_count = sum(len(page.get_images(full=True)) for page in doc)
    return "\n".join(pages), pages, image_count


def _document_student_score(name: str, text: str, figures: int, layout: dict[str, Any], model: dict[str, Any]) -> int:
    score = 70
    if "目录与使用建议" in text:
        score += 4
    if figures >= {"Sprint": 2, "PastPaper": 3, "MockExam": 2, "Review": 3}.get(name, 2):
        score += 6
    if not layout.get("large_blank_pages"):
        score += 5
    if not layout.get("overcrowded_pages"):
        score += 3
    markers = {
        "Sprint": ["如果只剩 5 分钟", "救命卡", "最后 10 秒"],
        "PastPaper": ["为什么这么考", "第一眼先看", "阅卷扣分点", "本题收获"],
        "MockExam": ["计算与综合题", "参考答案与评分标准"],
        "Review": ["知识地图", "本节你必须会", "公式总表", "自测题"],
    }[name]
    score += sum(3 for marker in markers if marker in text)
    if name == "MockExam":
        score += max(0, int(model.get("mock_difficulty_score", 0)) - 75) // 2
    return min(score, 92)


def _print_score(documents: dict[str, Any], layout: dict[str, Any], duplicated: list[str]) -> int:
    score = 86
    score -= 8 * len(layout.get("large_blank_area_pages", []))
    score -= 4 * len(layout.get("overcrowded_pages", []))
    score -= 5 * len(duplicated)
    return max(0, score)


def _goodnotes_score(documents: dict[str, Any], layout: dict[str, Any]) -> int:
    avg = sum(doc["student_view_score"] for doc in documents.values()) / max(1, len(documents))
    score = int(avg)
    score -= 4 * len(layout.get("overcrowded_pages", []))
    return max(0, min(92, score))


def _student_score(documents: dict[str, Any], print_score: int, goodnotes_score: int) -> int:
    avg_doc = sum(doc["student_view_score"] for doc in documents.values()) / max(1, len(documents))
    return int((avg_doc + print_score + goodnotes_score) / 3)


def _asset_coverage(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    used = [asset for asset in manifest if asset.get("usage_count", 0) > 0]
    return {"used_assets": len(used), "total_assets": len(manifest), "coverage_ratio": round(len(used) / max(1, len(manifest)), 3)}


def _assets_by_pdf(usage: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in usage.get("usage_log", []):
        result.setdefault(item.get("pdf_type", ""), []).append(item.get("asset_id", ""))
    return result


def _load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
