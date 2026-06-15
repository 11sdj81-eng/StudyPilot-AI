"""Document Intelligence v5 parse pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from core.document_intelligence_v5.fallback_parser import detect_scanned_pdf
from core.document_intelligence_v5.parser_quality_gate import summarize_quality
from core.document_intelligence_v5.parser_registry import ParserRegistry
from core.document_intelligence_v5.parser_report import write_json_report


SUPPORTED = {".pdf", ".pptx", ".ppt", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md"}


def parse_file(file_path: str | Path, output_dir: str | Path = "data/parsed/v5", registry: ParserRegistry | None = None):
    registry = registry or ParserRegistry()
    path = Path(file_path)
    is_scanned = detect_scanned_pdf(path) if path.suffix.lower() == ".pdf" else False
    parser = registry.select(path, is_scanned=is_scanned)
    result = parser.parse(path, output_dir)
    result.metadata["selection_parser"] = parser.name
    result.metadata["detected_scanned"] = is_scanned
    _write_parse_result(result, output_dir)
    return result


def parse_inputs(input_path: str | Path, output_dir: str | Path = "data/parsed/v5", report_dir: str | Path = "data/outputs/v5_reports") -> dict:
    input_path = Path(input_path)
    registry = ParserRegistry()
    files = _collect_files(input_path)
    results = [parse_file(path, output_dir, registry) for path in files]
    report_dir = Path(report_dir)
    write_json_report(registry.dependency_report(), report_dir / "dependency_check_report.json")
    registry.write_selection_report(report_dir / "parser_selection_report.json")
    parse_summary = summarize_quality(results)
    write_json_report(parse_summary, report_dir / "document_parse_report.json")
    return {"results": results, "dependency_report": registry.dependency_report(), "parse_summary": parse_summary}


def _collect_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted([p for p in input_path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED])


def _write_parse_result(result, output_dir: str | Path) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{result.document_id}_{Path(result.file_path).stem}.json"
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
