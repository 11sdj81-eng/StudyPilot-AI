"""WebResult schema and WebRetrievalReport."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WebResult:
    query: str
    title: str = ""
    url: str = ""
    snippet: str = ""
    retrieved_at: str = ""
    source_domain: str = ""
    source_level: str = "WEB_RETRIEVED"
    confidence: float = 0.0
    allowed_use: str = "题型参考"  # what this result can be used for
    extracted_patterns: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.url and not self.source_domain:
            self.source_domain = self._extract_domain(self.url)

    @staticmethod
    def _extract_domain(url: str) -> str:
        import re
        m = re.search(r'https?://([^/]+)', url)
        return m.group(1) if m else ""

    def label(self) -> str:
        return f"WEB_RETRIEVED · {self.source_domain} · {self.allowed_use}"

    def to_dict(self) -> dict:
        return {
            "query": self.query, "title": self.title, "url": self.url,
            "snippet": self.snippet[:200], "retrieved_at": self.retrieved_at,
            "source_domain": self.source_domain, "source_level": self.source_level,
            "confidence": self.confidence, "allowed_use": self.allowed_use,
            "extracted_patterns": self.extracted_patterns,
        }


@dataclass
class WebRetrievalReport:
    enabled: bool = False
    trigger_reason: str = ""
    query_count: int = 0
    result_count: int = 0
    accepted_result_count: int = 0
    rejected_result_count: int = 0
    web_retrieval_failed: bool = False
    fallback_used: bool = False
    web_retrieved_question_count: int = 0
    fallback_level: str = ""       # AI_DERIVED or AI_GENERATED
    results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled, "trigger_reason": self.trigger_reason,
            "query_count": self.query_count, "result_count": self.result_count,
            "accepted_result_count": self.accepted_result_count,
            "rejected_result_count": self.rejected_result_count,
            "web_retrieval_failed": self.web_retrieval_failed,
            "fallback_used": self.fallback_used,
            "web_retrieved_question_count": self.web_retrieved_question_count,
            "fallback_level": self.fallback_level,
        }
