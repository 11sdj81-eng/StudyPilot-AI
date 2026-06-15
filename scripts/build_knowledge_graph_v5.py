#!/usr/bin/env python3
"""Build KnowledgeGraph v5 report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.v5_common import load_parse_results
from core.knowledge_builder_v5 import build_knowledge_graph_v5


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/parsed/v5")
    parser.add_argument("--output", default="data/outputs/v5_reports/knowledge_graph_v5_report.json")
    args = parser.parse_args()
    build_knowledge_graph_v5(load_parse_results(args.input), args.output)


if __name__ == "__main__":
    main()
