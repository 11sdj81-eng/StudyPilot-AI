"""Load v4.1 exam pattern datasets."""

from __future__ import annotations

import json
from pathlib import Path

from core.exam_engine.exam_pattern import ExamPattern


PATTERN_DIR = Path("data/exam_patterns/engineering/electromagnetic_static_chapter1")


def load_patterns(base: str | Path = PATTERN_DIR) -> list[ExamPattern]:
    data = json.loads((Path(base) / "patterns.json").read_text(encoding="utf-8"))
    return [ExamPattern(**item) for item in data]


def load_json(name: str, base: str | Path = PATTERN_DIR) -> dict | list:
    return json.loads((Path(base) / name).read_text(encoding="utf-8"))
