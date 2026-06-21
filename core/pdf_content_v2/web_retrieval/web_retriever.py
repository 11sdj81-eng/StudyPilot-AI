"""WebRetriever — controlled web search with course-agnostic query generation.

When ENABLE_WEB_RETRIEVAL=false: returns empty results, marks fallback_used=true.
"""

from __future__ import annotations

from typing import Any

from core.pdf_content_v2.web_retrieval.web_retrieval_config import WebRetrievalConfig
from core.pdf_content_v2.web_retrieval.web_result_schema import WebResult, WebRetrievalReport


# ═══════════════════════════════════════════════════════════════════════════
# Course-agnostic query templates — keyed by subject_type, not course name
# ═══════════════════════════════════════════════════════════════════════════

QUERY_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "math": {
        "概念": ["{chapter_name} {concept} 习题", "{course_name} {concept} 例题"],
        "题型": ["{chapter_name} 期末题 {concept}", "{course_name} 期末考试 {concept}"],
        "易错": ["{concept} 常见错误", "{concept} 易错点"],
        "公式": ["{concept} 公式 条件", "{concept} 适用条件"],
    },
    "engineering": {
        "概念": ["{chapter_name} {concept} 习题", "{course_name} {concept} 例题"],
        "题型": ["{chapter_name} 期末题 {concept}", "{course_name} 考试 {concept}"],
        "易错": ["{concept} 常见错误", "{concept} 易错点"],
        "公式": ["{concept} 公式 条件", "{concept} 适用条件"],
    },
}


class WebRetriever:
    """Controlled web retrieval — only activates when enabled AND needed.

    Source priority (immutable):
        教材/PPT/真题 > AI_DERIVED > WEB_RETRIEVED > AI_GENERATED
    """

    def __init__(self, config: WebRetrievalConfig | None = None):
        self.config = config or WebRetrievalConfig()
        self._results: list[WebResult] = []

    def should_retrieve(self, missing_concepts: list[str] | None = None,
                         missing_examples: int = 0,
                         missing_patterns: int = 0) -> bool:
        """Check if web retrieval is justified."""
        if not self.config.enabled:
            return False
        if not missing_concepts and missing_examples == 0 and missing_patterns == 0:
            return False  # no gap to fill
        return True

    def generate_queries(self, course_name: str, chapter_name: str,
                          concepts: list[str], subject_type: str = "math") -> list[str]:
        """Generate search queries from course profile. Course-agnostic."""
        templates = QUERY_TEMPLATES.get(subject_type, QUERY_TEMPLATES["math"])
        queries = []
        for category, patterns in templates.items():
            for concept in concepts[:3]:  # top 3 missing concepts
                for pattern in patterns[:1]:  # one query per category
                    q = pattern.format(
                        course_name=course_name, chapter_name=chapter_name, concept=concept
                    )
                    queries.append(q)
        return queries[:self.config.max_queries_per_session]

    def retrieve(self, queries: list[str], trigger_reason: str = "") -> WebRetrievalReport:
        """Execute web retrieval. Returns empty when disabled."""
        report = WebRetrievalReport(
            enabled=self.config.enabled,
            trigger_reason=trigger_reason,
            query_count=len(queries),
        )

        if not self.config.enabled:
            report.web_retrieval_failed = False  # not failed, just disabled
            report.fallback_used = True
            report.fallback_level = "AI_DERIVED"
            return report

        # ── Actual retrieval would go here ──
        # When ENABLE_WEB_RETRIEVAL=true, this would:
        # 1. For each query, call a search API
        # 2. Parse results into WebResult objects
        # 3. Filter by allowed_domains
        # 4. Extract short patterns/snippets (never full pages)
        #
        # For now: gracefully return empty with fallback
        report.web_retrieval_failed = True
        report.fallback_used = True
        report.fallback_level = "AI_DERIVED"
        return report

    def mock_result(self, query: str, concept: str, course_name: str) -> WebResult:
        """Generate a mock web result for testing. NOT for production use."""
        return WebResult(
            query=query, title=f"{concept} - {course_name}",
            url=f"https://example.edu/{concept}",
            snippet=f"{concept}是{course_name}中的重要知识点...",
            source_domain="example.edu",
            confidence=0.3, allowed_use="题型参考",
            extracted_patterns=[f"{concept}常见题型"],
        )

    def get_source_priority(self) -> list[str]:
        """Return immutable source priority order."""
        return ["textbook", "ppt", "past_exam", "ai_derived", "web_retrieved", "ai_generated"]
