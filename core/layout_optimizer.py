"""Small layout guidance helpers for v6 PDF reports."""

from __future__ import annotations


def layout_policy() -> dict:
    return {
        "avoid_orphans": ["图片", "公式", "例题卡片"],
        "max_blank_ratio": 0.4,
        "notes": "v6 CSS allows knowledge cards to split, but keeps examples, figures and formulas together.",
    }
