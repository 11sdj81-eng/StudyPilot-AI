"""Figure Engine v2 bridge from Document Intelligence v5."""

from __future__ import annotations

import json
from pathlib import Path

from core.document_intelligence_v5.asset_mapper import build_figure_bank_v2
from core.document_intelligence_v5.document_blocks import DocumentParseResult


def build_from_parse_results(results: list[DocumentParseResult], output_path: str | Path = "data/outputs/v5_reports/figure_bank_v2_report.json") -> dict:
    report = build_figure_bank_v2(results)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
