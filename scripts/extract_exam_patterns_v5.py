#!/usr/bin/env python3
"""Extract ExamPattern candidates from v5 parse results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.v5_common import load_parse_results
from core.exam_engine.exam_pattern_extractor_v5 import extract_exam_patterns_v5


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/parsed/v5")
    parser.add_argument("--output", default="data/outputs/v5_reports/exam_pattern_v5_report.json")
    args = parser.parse_args()
    extract_exam_patterns_v5(load_parse_results(args.input), args.output)


if __name__ == "__main__":
    main()
