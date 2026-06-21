"""WebSourceValidator — ensure web content doesn't overwrite textbook/exam evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.web_retrieval.web_result_schema import WebResult


@dataclass
class SourceValidationResult:
    passed: bool = False
    rejected_count: int = 0
    accepted_count: int = 0
    rejection_reasons: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed, "rejected_count": self.rejected_count,
            "accepted_count": self.accepted_count, "rejection_reasons": self.rejection_reasons,
        }


class WebSourceValidator:
    """Validate web results before they enter the quality pipeline.

    Rules:
        1. Never overwrite textbook evidence
        2. Never overwrite past exam evidence
        3. Never copy full pages (max snippet length)
        4. Must have recognizable domain
        5. Must not be from blocked domains
    """

    BLOCKED_KEYWORDS = [
        "盗版", "破解", "VIP", "付费", "注册", "充值",
        "z-lib", "libgen", "pdf下载", "免费下载",
    ]

    def validate(self, results: list[WebResult],
                 existing_textbook_evidence: bool = False,
                 existing_exam_evidence: bool = False,
                 max_snippet_length: int = 300) -> SourceValidationResult:
        """Validate web results. Reject if they would overwrite existing evidence."""
        result = SourceValidationResult()
        accepted = []

        for r in results:
            accept = True

            # 1. Never let web result claim to be textbook if textbook exists
            if existing_textbook_evidence and "教材" in r.allowed_use:
                result.rejection_reasons.append(f"Rejected {r.url}: textbook evidence already exists")
                accept = False

            # 2. Never let web result claim to be exam
            if existing_exam_evidence and ("真题" in r.allowed_use or "exam" in r.url.lower()):
                result.rejection_reasons.append(f"Rejected {r.url}: exam evidence already exists")
                accept = False

            # 3. Check snippet length
            if len(r.snippet) > max_snippet_length:
                result.rejection_reasons.append(f"Rejected {r.url}: snippet too long ({len(r.snippet)} chars)")
                r.snippet = r.snippet[:max_snippet_length]  # truncate, don't reject

            # 4. Check blocked keywords
            for kw in self.BLOCKED_KEYWORDS:
                if kw in r.snippet or kw in r.title or kw in r.url:
                    result.rejection_reasons.append(f"Rejected {r.url}: blocked keyword '{kw}'")
                    accept = False
                    break

            # 5. Must have a domain
            if not r.source_domain:
                result.rejection_reasons.append(f"Rejected: no domain")
                accept = False

            if accept:
                accepted.append(r)

        result.accepted_count = len(accepted)
        result.rejected_count = len(results) - result.accepted_count
        result.passed = result.rejected_count == 0
        result.checks = {"total": len(results), "accepted": result.accepted_count, "rejected": result.rejected_count}
        return result
