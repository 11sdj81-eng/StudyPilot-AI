#!/usr/bin/env python3
"""Build FigureBank v2 report from v5 parse JSON files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.v5_common import load_parse_results
from core.figure_engine.figure_engine_v2 import build_from_parse_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/parsed/v5")
    parser.add_argument("--output", default="data/outputs/v5_reports/figure_bank_v2_report.json")
    args = parser.parse_args()
    build_from_parse_results(load_parse_results(args.input), args.output)


if __name__ == "__main__":
    main()
