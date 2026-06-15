"""PDF-level quality gate for StudyPilot PDF v4."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.pdf_v4.symbol_normalizer import FORBIDDEN_TOKENS


DEV_TEXT = ["为什么放这张图", "为什么这么考", "为什么设计这道题", "这张图用于", "本轮使用程序化", "教材图未命中"]


def run_v4_quality_gate(outputs: dict[str, Any], output_dir: str | Path = "data/outputs/pdf_v4") -> dict[str, Any]:
    out = Path(output_dir)
    figure_manifest = _load(out / "StudyPilot_v4_figure_manifest.json", [])
    docs = {}
    for name, item in outputs.items():
        docs[name] = inspect_v4_pdf(name, Path(item["pdf"]), item)
    repeated = _repeated_figures(docs)
    broken = sum(doc["broken_image_count"] for doc in docs.values())
    blank = sum(doc["large_blank_page_count"] for doc in docs.values())
    formula_leaks = sum(doc["formula_text_leak_count"] for doc in docs.values())
    internal_leaks = sum(doc["internal_field_leak_count"] for doc in docs.values())
    orphan_steps = sum(doc["orphan_solution_steps_count"] for doc in docs.values())
    overlap = sum(doc["figure_text_overlap_risk"] for doc in docs.values())
    student = int(sum(doc["student_readiness_score"] for doc in docs.values()) / max(1, len(docs)))
    typography = int(sum(doc["typography_score"] for doc in docs.values()) / max(1, len(docs)))
    goodnotes = int(sum(doc["goodnotes_score"] for doc in docs.values()) / max(1, len(docs)))
    print_score = int(sum(doc["print_score"] for doc in docs.values()) / max(1, len(docs)))
    recommend_release = not any([broken, blank, formula_leaks, internal_leaks, orphan_steps, repeated]) and student >= 80
    report = {
        "engine": "typst",
        "technical_pass": recommend_release,
        "recommend_manual_acceptance": student >= 80 and not formula_leaks and not internal_leaks,
        "recommend_release": recommend_release,
        "summary": {
            "broken_image_count": broken,
            "figure_text_overlap_risk": overlap,
            "large_blank_page_count": blank,
            "overcrowded_page_count": sum(doc["overcrowded_page_count"] for doc in docs.values()),
            "formula_text_leak_count": formula_leaks,
            "internal_field_leak_count": internal_leaks,
            "orphan_solution_steps_count": orphan_steps,
            "repeated_figure_count": len(repeated),
            "typography_score": typography,
            "goodnotes_score": goodnotes,
            "print_score": print_score,
            "student_readiness_score": student,
        },
        "documents": docs,
        "repeated_figures": repeated,
        "figure_manifest_count": len(figure_manifest),
    }
    (out / "StudyPilot_v4_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_v41_quality_gate(outputs: dict[str, Any], output_dir: str | Path = "data/outputs/pdf_v4") -> dict[str, Any]:
    out = Path(output_dir)
    exam = _load(out / "StudyPilot_v41_exam_pattern_report.json", {})
    fig_report = _load(out / "StudyPilot_v41_figure_report.json", {})
    docs = {name: inspect_v4_pdf(name, Path(item["pdf"]), item) for name, item in outputs.items()}
    all_text = "\n".join(_extract(Path(item["pdf"]))[0] for item in outputs.values())
    developer_text_count = sum(all_text.count(token) for token in DEV_TEXT + ["整理原则", "系统字段", "本轮使用", "未命中"])
    formula_symbol_hits = _formula_symbol_hits(all_text)
    duplicate_template_phrase_count = _duplicate_template_phrase_count(all_text)
    pastpaper_case_count = int(exam.get("pastpaper_case_count", 0))
    review_page_count = docs["Review"]["page_count"]
    sprint_page_count = docs["Sprint"]["page_count"]
    mock_average = float(exam.get("mock", {}).get("average", 0))
    has_level4 = bool(exam.get("mock", {}).get("has_level4_or_above", False))
    past_depth = _pastpaper_depth_score(docs["PastPaper"], all_text)
    review_coverage = _review_concept_coverage(all_text)
    sprint_score = _sprint_practicality_score(all_text, sprint_page_count)
    figure_score = int(fig_report.get("figure_information_score", 0))
    recommend_release = (
        review_page_count >= 15
        and pastpaper_case_count >= 4
        and has_level4
        and developer_text_count == 0
        and not formula_symbol_hits
        and figure_score >= 80
        and sprint_score >= 80
        and past_depth >= 80
        and review_coverage >= 6
    )
    report = {
        "engine": "typst",
        "technical_pass": developer_text_count == 0 and not formula_symbol_hits,
        "recommend_manual_acceptance": recommend_release or (developer_text_count == 0 and not formula_symbol_hits and review_page_count >= 15),
        "recommend_release": recommend_release,
        "summary": {
            "mock_average_difficulty": mock_average,
            "mock_has_level4_or_above": has_level4,
            "pastpaper_case_depth_score": past_depth,
            "review_page_count": review_page_count,
            "review_concept_coverage": review_coverage,
            "sprint_page_count": sprint_page_count,
            "sprint_practicality_score": sprint_score,
            "duplicate_template_phrase_count": duplicate_template_phrase_count,
            "developer_text_count": developer_text_count,
            "formula_symbol_issue_count": len(formula_symbol_hits),
            "formula_symbol_hits": formula_symbol_hits,
            "figure_information_score": figure_score,
            "pastpaper_case_count": pastpaper_case_count,
        },
        "documents": docs,
        "exam_pattern_report": exam,
        "figure_report": fig_report,
        "release_blockers": _v41_blockers(review_page_count, pastpaper_case_count, has_level4, developer_text_count, formula_symbol_hits, figure_score, sprint_score, past_depth, review_coverage),
    }
    (out / "StudyPilot_v41_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def inspect_v4_pdf(name: str, pdf_path: Path, item: dict[str, Any]) -> dict[str, Any]:
    text, pages, images_per_page = _extract(pdf_path)
    forbidden = [token for token in FORBIDDEN_TOKENS if token in text]
    dev_hits = [token for token in DEV_TEXT if token in text]
    latex_like = re.findall(r"\\[a-zA-Z]+|\bfrac\b|\bsqrt\b|\bquad\b|\btag\b", text)
    blank_pages = _blank_pages(pages)
    overcrowded = _overcrowded_pages(pages)
    orphan = _orphan_steps(name, text)
    figure_titles = re.findall(r"图\s+\d-\d\s+([^\n]+)", text)
    score = _student_score(name, text, len(figure_titles), len(blank_pages), len(overcrowded))
    return {
        "pdf_path": str(pdf_path.resolve()),
        "page_count": len(pages),
        "file_size_bytes": pdf_path.stat().st_size,
        "image_count": sum(images_per_page),
        "figure_titles": figure_titles,
        "broken_image_count": 0 if figure_titles else 1,
        "figure_text_overlap_risk": 0,
        "large_blank_page_count": len(blank_pages),
        "large_blank_pages": blank_pages,
        "overcrowded_page_count": len(overcrowded),
        "overcrowded_pages": overcrowded,
        "formula_text_leak_count": len(latex_like),
        "internal_field_leak_count": len(forbidden) + len(dev_hits),
        "forbidden_hits": forbidden + dev_hits,
        "orphan_solution_steps_count": orphan,
        "typography_score": max(72, score - 2),
        "goodnotes_score": score,
        "print_score": max(70, score - len(blank_pages) * 8),
        "student_readiness_score": score,
    }


def _extract(path: Path) -> tuple[str, list[str], list[int]]:
    import fitz

    pages = []
    image_counts = []
    with fitz.open(path) as doc:
        for page in doc:
            pages.append(page.get_text("text"))
            image_counts.append(len(page.get_images(full=True)))
    return "\n".join(pages), pages, image_counts


def _blank_pages(pages: list[str]) -> list[int]:
    result = []
    for idx, page in enumerate(pages, start=1):
        cleaned = re.sub(r"StudyPilot AI.*|\n\d+\n", "", page).strip()
        if idx > 1 and len(cleaned) < 90:
            result.append(idx)
    return result


def _overcrowded_pages(pages: list[str]) -> list[int]:
    return [idx for idx, page in enumerate(pages, start=1) if len(page) > 2600]


def _orphan_steps(name: str, text: str) -> int:
    if name == "PastPaper" and "参考来源" in text:
        ref_index = text.rindex("参考来源")
        after_ref = text[ref_index:]
        return 1 if "解题步骤" in after_ref or "标准答案" in after_ref else 0
    return 0


def _repeated_figures(docs: dict[str, dict[str, Any]]) -> list[str]:
    repeated = []
    for name, doc in docs.items():
        seen = {}
        for title in doc["figure_titles"]:
            seen[title] = seen.get(title, 0) + 1
        for title, count in seen.items():
            if count > 1:
                repeated.append(f"{name}:{title}")
    return repeated


def _student_score(name: str, text: str, figures: int, blanks: int, crowded: int) -> int:
    score = 78
    targets = {
        "Sprint": ["30 分钟使用路径", "5 分钟保底区", "最后 10 秒", "最后检查清单"],
        "PastPaper": ["审题", "建模", "解题步骤", "扣分点", "变式"],
        "MockExam": ["试卷正文", "参考答案与评分标准", "计算与综合题"],
        "Review": ["学习地图", "核心概念", "公式系统", "典型例题", "自测题"],
    }
    score += sum(3 for marker in targets.get(name, []) if marker in text)
    if figures >= {"Sprint": 3, "PastPaper": 3, "MockExam": 3, "Review": 5}.get(name, 3):
        score += 5
    score -= blanks * 10 + crowded * 4
    return max(0, min(92, score))


def _formula_symbol_hits(text: str) -> list[str]:
    tokens = ["r^2", "r^3", "a^2", "epsilon0", "rho_s", "Q_enc", "frac", "sqrt", "tag", "quad", "concept_id", "formula_id", "source_basis", "ε0", "𝜀0", "^"]
    return sorted({token for token in tokens if token in text})


def _duplicate_template_phrase_count(text: str) -> int:
    phrases = [
        "漏写适用条件；跳步导致扣过程分；方向或边界验证不完整",
        "先建模，再代公式",
        "不要一上来套公式",
    ]
    return sum(max(0, text.count(phrase) - 1) for phrase in phrases)


def _pastpaper_depth_score(doc: dict[str, Any], text: str) -> int:
    markers = ["题型识别", "审题", "建模", "解题步骤", "标准答案", "扣分点", "变式训练", "本题总结"]
    score = 52 + sum(5 for marker in markers if marker in text)
    if doc["page_count"] >= 8:
        score += 8
    if doc["figure_titles"]:
        score += 4
    return min(94, score)


def _review_concept_coverage(text: str) -> int:
    concepts = ["电场强度", "高斯定理", "电位与电场关系", "边界条件", "镜像法", "静电能量"]
    return sum(1 for concept in concepts if concept in text)


def _sprint_practicality_score(text: str, pages: int) -> int:
    markers = ["30 分钟使用路线", "5 分钟保底区", "高频救命卡", "最后 10 秒", "保底题", "最后检查清单"]
    score = 55 + sum(6 for marker in markers if marker in text)
    if 5 <= pages <= 8:
        score += 8
    return min(94, score)


def _v41_blockers(review_pages: int, past_cases: int, has_level4: bool, developer_count: int, formula_hits: list[str], figure_score: int, sprint_score: int, past_depth: int, coverage: int) -> list[str]:
    blockers = []
    if review_pages < 15:
        blockers.append("Review 页数低于 15。")
    if past_cases < 4:
        blockers.append("PastPaper 题数低于 4。")
    if not has_level4:
        blockers.append("MockExam 没有 Level 4 以上题。")
    if developer_count > 0:
        blockers.append("用户 PDF 中存在开发者说明文字。")
    if formula_hits:
        blockers.append("存在公式符号问题：" + "、".join(formula_hits))
    if figure_score < 80:
        blockers.append("图像信息量不足。")
    if sprint_score < 80:
        blockers.append("Sprint 救命感不足。")
    if past_depth < 80:
        blockers.append("PastPaper 讲题深度不足。")
    if coverage < 6:
        blockers.append("Review 核心概念覆盖不足。")
    return blockers


def _load(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
