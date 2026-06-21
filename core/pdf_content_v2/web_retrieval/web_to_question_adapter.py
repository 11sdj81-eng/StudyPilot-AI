"""WebToQuestionAdapter — convert web snippets into usable question patterns."""

from __future__ import annotations

import re
from typing import Any

from core.pdf_content_v2.web_retrieval.web_result_schema import WebResult


class WebToQuestionAdapter:
    """Extract question patterns from web results for AI-assisted generation.

    NEVER copies full questions — only extracts structural patterns.
    """

    def extract_patterns(self, results: list[WebResult]) -> list[dict]:
        """Extract question type patterns from web results."""
        patterns = []
        for r in results:
            if r.confidence < 0.3:
                continue
            p = self._parse_snippet(r)
            if p:
                p["source"] = r.label()
                patterns.append(p)
        return patterns

    def _parse_snippet(self, result: WebResult) -> dict | None:
        snippet = result.snippet
        # Detect question type from snippet structure
        qtype = self._detect_type(snippet)
        if not qtype:
            return None

        return {
            "question_type": qtype,
            "concept_hint": result.query.split()[-1] if result.query else "",
            "pattern_example": snippet[:150],
            "source_domain": result.source_domain,
            "source_level": "WEB_RETRIEVED",
            "allowed_use": "题型模式参考（非原题复制）",
        }

    def _detect_type(self, snippet: str) -> str | None:
        if re.search(r'[设已知].*求|判断.*是否|证明.*', snippet):
            return "计算题"
        if re.search(r'下列|正确.*是|错误.*是|选择', snippet):
            return "选择题"
        if re.search(r'填写|填空|______', snippet):
            return "填空题"
        return None

    def adapt_for_ai_generation(self, pattern: dict, concept: dict) -> dict:
        """Generate an AI prompt constraint from a web pattern. NEVER copies content."""
        return {
            "constraint": "参照题型模式（非原题）",
            "question_type": pattern.get("question_type", ""),
            "source_level": "AI_DERIVED (pattern from WEB_RETRIEVED)",
            "concept": concept.get("display_name", concept.get("title", "")),
            "instruction": f"生成一道{pattern['question_type']}，考查{concept.get('display_name', '')}。"
                          f"题型参考自{pattern.get('source_domain', '公开资源')}的公开习题模式，"
                          f"不得复制原题，仅参考题型结构。",
        }
