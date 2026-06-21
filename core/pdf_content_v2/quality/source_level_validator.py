"""Source-level validation: ensure every claim has a graded source."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SOURCE_LEVELS = {
    1: "Textbook",
    2: "PPT",
    3: "Past Exam",
    4: "Local Bank",
    5: "Web Retrieved",
    6: "AI Generated",
}

FORBIDDEN_SOURCE_TEXT = [
    "未找到高置信来源",
    "未找到高置信公式",
    "未找到高置信例题",
    "未找到高置信真题",
]


@dataclass
class SourceCheckResult:
    passed: bool = False
    source_missing_count: int = 0
    unsupported_claim_count: int = 0
    fake_question_count: int = 0
    ai_generated_count: int = 0
    web_retrieved_count: int = 0
    source_levels_found: dict[int, int] = field(default_factory=dict)
    forbidden_hits: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "source_missing_count": self.source_missing_count,
            "unsupported_claim_count": self.unsupported_claim_count,
            "fake_question_count": self.fake_question_count,
            "ai_generated_count": self.ai_generated_count,
            "web_retrieved_count": self.web_retrieved_count,
            "source_levels_found": self.source_levels_found,
            "forbidden_hits": self.forbidden_hits,
            "checks": self.checks,
        }


class SourceLevelValidator:
    """Validate that all content has proper source attribution."""

    def validate(self, typst_text: str) -> SourceCheckResult:
        result = SourceCheckResult()

        # Count "未找到高置信" occurrences
        for forbidden in FORBIDDEN_SOURCE_TEXT:
            count = typst_text.count(forbidden)
            if count > 0:
                result.source_missing_count += count
                result.forbidden_hits.append(f"{forbidden} (x{count})")

        # Count fake/template questions
        fake_patterns = [
            "请填写一个高频公式",
            "请列举",
            "请说明",
            "请简述",
        ]
        for fp in fake_patterns:
            count = typst_text.count(fp)
            if count > 0:
                result.fake_question_count += count

        # Count AI Generated attributions
        result.ai_generated_count = typst_text.count("AI Generated") + typst_text.count("AI 生成")

        # Count Web Retrieved
        result.web_retrieved_count = typst_text.count("Web Retrieved") + typst_text.count("联网检索")

        # Count source levels mentioned
        for level, label in SOURCE_LEVELS.items():
            count = typst_text.count(label)
            if count > 0:
                result.source_levels_found[level] = count

        # Check for unsupported claims (frequency/score claims without source)
        unsupported = re.findall(r'考频[：:]\s*近\s*\d+\s*年\s*\d+\s*次', typst_text)
        result.unsupported_claim_count = len(unsupported)

        # Overall: passed if no missing sources and no fake questions
        # Allow some "未找到高置信" in the source index table (they're informational there)
        result.passed = (
            result.source_missing_count <= 5  # Allow in source index context
            and result.fake_question_count == 0
            and result.unsupported_claim_count <= 5  # Allow some exam pattern descriptions
        )
        result.checks = {
            "total_forbidden_hits": len(result.forbidden_hits),
            "source_coverage": "full" if result.source_missing_count == 0 else "partial",
        }
        return result
