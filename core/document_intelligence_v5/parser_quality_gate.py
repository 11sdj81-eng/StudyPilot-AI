"""Quality gate for Document Intelligence v5 parser outputs."""

from __future__ import annotations

from core.document_intelligence_v5.document_blocks import DocumentParseResult


def inspect_parse_result(result: DocumentParseResult) -> dict:
    text_len = sum(len(page.text.strip()) for page in result.pages)
    figure_count = len(result.figures)
    formula_count = len(result.formulas)
    table_count = len(result.tables)
    question_count = len(result.questions)
    low_confidence = result.quality_score < 0.5
    full_page_scan_risk = any(fig.metadata.get("full_page_risk") for fig in result.figures)
    return {
        "document_id": result.document_id,
        "file_path": result.file_path,
        "parser_name": result.parser_name,
        "parse_success": bool(result.pages or result.markdown or result.assets),
        "is_scanned": result.is_scanned,
        "text_extracted": text_len > 0,
        "text_length": text_len,
        "figure_count": figure_count,
        "formula_count": formula_count,
        "table_count": table_count,
        "question_count": question_count,
        "low_confidence": low_confidence,
        "full_page_scan_risk": full_page_scan_risk,
        "concept_match_count": 0,
        "review_queue": low_confidence or full_page_scan_risk or (result.is_scanned and result.parser_name == "fallback"),
        "warnings": result.warnings,
        "quality_score": result.quality_score,
    }


def summarize_quality(results: list[DocumentParseResult]) -> dict:
    docs = [inspect_parse_result(r) for r in results]
    return {
        "document_count": len(docs),
        "parsed_count": sum(1 for d in docs if d["parse_success"]),
        "scanned_count": sum(1 for d in docs if d["is_scanned"]),
        "fallback_count": sum(1 for d in docs if d["parser_name"] == "fallback"),
        "text_extracted_count": sum(1 for d in docs if d["text_extracted"]),
        "figure_count": sum(d["figure_count"] for d in docs),
        "formula_count": sum(d["formula_count"] for d in docs),
        "table_count": sum(d["table_count"] for d in docs),
        "question_count": sum(d["question_count"] for d in docs),
        "review_queue_count": sum(1 for d in docs if d["review_queue"]),
        "documents": docs,
    }
