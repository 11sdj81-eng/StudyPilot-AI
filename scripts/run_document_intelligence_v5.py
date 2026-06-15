#!/usr/bin/env python3
"""Run Document Intelligence v5 parsing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.document_intelligence_v5.parse_pipeline import parse_inputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="data/parsed/v5")
    parser.add_argument("--report-dir", default="data/outputs/v5_reports")
    args = parser.parse_args()
    parse_inputs(args.input, args.output, args.report_dir)


if __name__ == "__main__":
    main()
