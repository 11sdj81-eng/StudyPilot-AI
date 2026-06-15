"""Final PDF quality gate for StudyPilot v3 outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FORBIDDEN_TOKENS = [
    "formula_id",
    "concept_id",
    "source_basis",
    "example_",
    "formula_db",
    "example_db",
    "暂无",
    "None",
    "null",
    "empty",
    "Q_enc",
    "frac",
    "sqrt",
    "tag",
    "\\frac",
    "\\sqrt",
    "\\nabla",
    "\\varepsilon",
    "\\mathbf",
    "$",
    "乱码方块",
    "OCR异常",
    "SS号",
    "General Information",
]

EMPTY_FORMULA_PATTERNS = [
    "必背公式：；",
    "所用公式：；",
    "公式来源：",
    "公式总结表空公式",
]


def run_v3_quality_gate(outputs: dict[str, Any], output_path: str | Path = "data/outputs/StudyPilot_v3_quality_report.json") -> dict[str, Any]:
    report = {
        "technical_pass": True,
        "teaching_usable": True,
        "recommend_manual_acceptance": True,
        "documents": {},
        "summary": {
            "empty_formula_count": 0,
            "exposed_internal_field_count": 0,
            "latex_leak_count": 0,
            "blank_page_count": 0,
            "question_numbering_pass": True,
            "answer_alignment_pass": True,
        },
    }
    for name, item in outputs.items():
        pdf = Path(item["pdf"])
        doc_report = inspect_pdf_v3(pdf, item.get("model", {}), name)
        report["documents"][name] = doc_report
        report["summary"]["empty_formula_count"] += len(doc_report["empty_formula_hits"])
        report["summary"]["exposed_internal_field_count"] += len(doc_report["internal_field_hits"])
        report["summary"]["latex_leak_count"] += len(doc_report["latex_leaks"])
        report["summary"]["blank_page_count"] += len(doc_report["blank_pages"])
        if name == "MockExam":
            report["summary"]["question_numbering_pass"] = doc_report["mock_exam"]["question_numbering_pass"]
            report["summary"]["answer_alignment_pass"] = doc_report["mock_exam"]["answer_alignment_pass"]
        if not doc_report["technical_pass"]:
            report["technical_pass"] = False
        if not doc_report["teaching_usable"]:
            report["teaching_usable"] = False
    report["recommend_manual_acceptance"] = bool(report["technical_pass"] and report["teaching_usable"])
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def inspect_pdf_v3(pdf_path: str | Path, model: dict[str, Any] | None = None, document_name: str = "") -> dict[str, Any]:
    path = Path(pdf_path)
    text, pages = _extract_text(path)
    forbidden = _hits(text, FORBIDDEN_TOKENS)
    empty_formula_hits = _hits(text, EMPTY_FORMULA_PATTERNS)
    latex_leaks = _latex_leaks(text)
    blank_pages = [i + 1 for i, page in enumerate(pages) if len(_clean_page_text(page)) < 24]
    repeated_titles = _repeated_titles(pages)
    figure_count = len(re.findall(r"图\s+1-\d+", text))
    example_count = len(re.findall(r"(基础题|计算题|综合题|提高题)", text))
    page_count = len(pages)
    size = path.stat().st_size if path.exists() else 0
    mock_exam = _mock_exam_check(text, model or {}) if document_name == "MockExam" else {}
    technical_pass = not forbidden and not empty_formula_hits and not latex_leaks and not blank_pages and not repeated_titles
    if document_name == "MockExam":
        technical_pass = technical_pass and mock_exam.get("question_count") == 14 and mock_exam.get("score_total") == 100 and mock_exam.get("question_numbering_pass") and mock_exam.get("answer_alignment_pass")
    teaching_usable = _teaching_usable(document_name, text, figure_count, example_count, page_count)
    return {
        "pdf_path": str(path.resolve()),
        "page_count": page_count,
        "file_size_bytes": size,
        "figure_count": figure_count,
        "example_count": example_count,
        "empty_formula_hits": empty_formula_hits,
        "internal_field_hits": [h for h in forbidden if h in {"formula_id", "concept_id", "source_basis", "example_", "formula_db", "example_db"}],
        "forbidden_hits": forbidden,
        "latex_leaks": latex_leaks,
        "blank_pages": blank_pages,
        "repeated_titles": repeated_titles,
        "mock_exam": mock_exam,
        "technical_pass": technical_pass,
        "teaching_usable": teaching_usable,
        "manual_acceptance_note": _manual_note(document_name, technical_pass, teaching_usable),
    }


def _extract_text(path: Path) -> tuple[str, list[str]]:
    try:
        import fitz

        with fitz.open(path) as doc:
            pages = [page.get_text("text") for page in doc]
        return "\n".join(pages), pages
    except Exception as exc:
        return f"PDF_TEXT_EXTRACTION_FAILED: {exc}", []


def _hits(text: str, tokens: list[str]) -> list[str]:
    return sorted({token for token in tokens if token and token in text})


def _latex_leaks(text: str) -> list[str]:
    leaks = []
    for pattern in [r"\\[a-zA-Z]+", r"\$[^$]+\$", r"\bquad\b", r"\btag\s*\d"]:
        if re.search(pattern, text):
            leaks.append(pattern)
    return leaks


def _clean_page_text(text: str) -> str:
    text = re.sub(r"StudyPilot AI · .*", "", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _repeated_titles(pages: list[str]) -> list[str]:
    titles = []
    for page in pages:
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        if lines:
            titles.append(lines[0])
    repeated = []
    for title in set(titles):
        if title and titles.count(title) >= 3 and "StudyPilot" not in title:
            repeated.append(title)
    return repeated


def _mock_exam_check(text: str, model: dict[str, Any]) -> dict[str, Any]:
    question_count = int(model.get("mock_question_count", 0))
    score_total = int(model.get("mock_score_total", 0))
    visible_numbers = [int(n) for n in re.findall(r"(?:^|\n)\s*(\d{1,2})\.", text)]
    body_numbers = [n for n in visible_numbers if 1 <= n <= 14]
    unique = sorted(set(body_numbers))
    answer_hits = [int(n) for n in re.findall(r"(?:^|\n)\s*(\d{1,2})\.\s*[A-D一-龥0-9]", text)]
    return {
        "question_count": question_count,
        "score_total": score_total,
        "visible_question_numbers": unique,
        "question_numbering_pass": unique == list(range(1, 15)),
        "answer_alignment_pass": question_count == 14 and score_total == 100 and len(set(answer_hits) & set(range(1, 15))) >= 14,
    }


def _teaching_usable(name: str, text: str, figure_count: int, example_count: int, page_count: int) -> bool:
    if name == "Sprint":
        return 4 <= page_count <= 12 and "最后 30 分钟" in text and "必背公式" in text
    if name == "PastPaper":
        return "审题与建模" in text and "评分扣分点" in text and figure_count >= 2
    if name == "MockExam":
        return "100 分" in text and "参考答案与评分标准" in text
    if name == "Review":
        return figure_count >= 3 and example_count >= 3 and "知识地图" in text and "自测题" in text
    return True


def _manual_note(name: str, technical_pass: bool, teaching_usable: bool) -> str:
    if technical_pass and teaching_usable:
        return f"{name} 通过技术门禁，建议进入人工抽查。"
    if not technical_pass:
        return f"{name} 存在技术问题，不建议人工验收通过。"
    return f"{name} 技术通过，但教学可用性仍需人工复核。"
