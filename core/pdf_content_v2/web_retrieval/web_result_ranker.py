"""WebResultRanker — score and filter web results by relevance and quality."""

from __future__ import annotations

from core.pdf_content_v2.web_retrieval.web_result_schema import WebResult


class WebResultRanker:
    """Rank web results by domain authority, snippet relevance, and confidence."""

    DOMAIN_AUTHORITY: dict[str, float] = {
        ".edu": 0.9, "edu.cn": 0.85, "khanacademy.org": 0.8,
        "wikipedia.org": 0.7, "github.com": 0.6, "zhihu.com": 0.4, "csdn.net": 0.35,
    }

    def rank(self, results: list[WebResult], query: str = "") -> list[WebResult]:
        """Rank results by combined score: domain × snippet relevance."""
        scored = []
        for r in results:
            domain_score = self._domain_score(r.source_domain)
            snippet_score = self._snippet_relevance(r.snippet, query) if query else 0.5
            r.confidence = 0.5 * domain_score + 0.5 * snippet_score
            scored.append(r)
        scored.sort(key=lambda x: x.confidence, reverse=True)
        return scored

    def filter_acceptable(self, results: list[WebResult], min_confidence: float = 0.4) -> list[WebResult]:
        """Filter to results with acceptable confidence."""
        return [r for r in results if r.confidence >= min_confidence]

    def _domain_score(self, domain: str) -> float:
        for key, score in self.DOMAIN_AUTHORITY.items():
            if key in domain:
                return score
        return 0.3  # unknown domain

    def _snippet_relevance(self, snippet: str, query: str) -> float:
        if not snippet or not query:
            return 0.3
        query_terms = set(query.replace(" ", ""))
        snippet_terms = set(snippet.replace(" ", ""))
        if not query_terms:
            return 0.3
        overlap = len(query_terms & snippet_terms) / len(query_terms)
        return min(0.9, overlap * 1.5)  # boost but cap
