#!/usr/bin/env python3
"""Run the full StudyPilot v5 document intelligence demo pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.document_intelligence_v5.parse_pipeline import parse_inputs
from core.exam_engine.exam_pattern_extractor_v5 import extract_exam_patterns_v5
from core.figure_engine.figure_engine_v2 import build_from_parse_results
from core.knowledge_builder_v5 import build_knowledge_graph_v5
from core.rag_v5 import build_rag_v5_report
from scripts.v5_common import write_acknowledgement_draft


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/uploads")
    parser.add_argument("--output", default="data/parsed/v5")
    parser.add_argument("--report-dir", default="data/outputs/v5_reports")
    args = parser.parse_args()
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    pipeline = parse_inputs(args.input, args.output, args.report_dir)
    results = pipeline["results"]
    build_from_parse_results(results, Path(args.report_dir) / "figure_bank_v2_report.json")
    build_knowledge_graph_v5(results, Path(args.report_dir) / "knowledge_graph_v5_report.json")
    extract_exam_patterns_v5(results, Path(args.report_dir) / "exam_pattern_v5_report.json")
    build_rag_v5_report(results, Path(args.report_dir) / "rag_v5_report.json")
    write_acknowledgement_draft(Path(args.report_dir) / "open_source_acknowledgement_draft.md")


if __name__ == "__main__":
    main()
