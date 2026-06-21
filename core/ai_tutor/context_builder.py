"""ContextBuilder — builds course context for LLM. Enhancement, not a gate."""

from __future__ import annotations

from typing import Any

COURSE_NAMES = {
    "probability_ch2": "概率论与随机过程 第二章 随机变量及其分布",
    "field_wave_ch1": "电磁场与电磁波 第一章 静电场",
    "digital_logic_ch3": "数字电路逻辑设计 第三章 组合逻辑电路（Demo，无教材）",
}

COURSE_TOPICS = {
    "probability_ch2": ["随机变量", "分布函数", "离散型", "连续型", "二项分布", "泊松分布", "正态分布", "指数分布"],
    "field_wave_ch1": ["静电场", "电场强度", "高斯定理", "电位", "镜像法", "边界条件", "导体", "介质"],
    "digital_logic_ch3": ["逻辑代数", "卡诺图", "组合逻辑", "触发器", "译码器", "数据选择器", "加法器", "真值表"],
}


class ContextBuilder:
    """Builds course context for LLM prompts. Never blocks answering."""

    def __init__(self):
        self._last_citations = []
        self._last_rejected_citations = []

    def get_citations(self) -> list[dict]:
        """Get structured citations from last RAG retrieval."""
        return getattr(self, '_last_citations', [])

    def get_rejected_citations(self) -> list[dict]:
        """Get rejected citation diagnostics from last RAG retrieval."""
        return getattr(self, '_last_rejected_citations', [])

    def build(self, course_id: str, user_query: str) -> dict:
        """Build context dict. Always returns something — never empty."""
        course_name = COURSE_NAMES.get(course_id, "未知课程")
        topics = COURSE_TOPICS.get(course_id, [])

        # Check if query is about THIS course
        query_is_about_this_course = any(t in user_query for t in topics)

        # Try RAG
        rag_context = self._try_rag(course_id, user_query)

        # Try seed data
        seed_context = self._try_seed_data(course_id, user_query)

        return {
            "course_id": course_id,
            "course_name": course_name,
            "course_topics": topics,
            "query_is_about_this_course": query_is_about_this_course,
            "rag_context": rag_context,
            "seed_context": seed_context,
            "has_materials": bool(rag_context),
            "has_seed_data": bool(seed_context),
        }

    def _try_rag(self, course_id: str, query: str) -> str:
        try:
            from core.hybrid_retrieval import hybrid_search
            from core.ai_tutor.citation_quality import filter_citations

            raw_results = hybrid_search(course_id, query, top_k=8)
            results, rejected = filter_citations(raw_results, query)
            # Build text context AND structured citations
            texts = []
            self._last_citations = []
            self._last_rejected_citations = rejected
            for r in results:
                chunk_id = r.get("chunk_id", "")
                score = r.get("score", 0)
                text = r.get("text", "")
                source_file = r.get("source_file", r.get("source", ""))
                page = r.get("page", "")
                preview = r.get("preview", text[:120].replace("\n", " "))
                # Include more context for LLM (500 chars vs old 300)
                texts.append(text[:500])
                self._last_citations.append({
                    "chunk_id": str(chunk_id),
                    "score": round(float(score) if score else 0, 4),
                    "source_file": str(source_file)[:80] if source_file else "",
                    "page": str(page) if page else "",
                    "preview": str(preview)[:150],
                    "resource_type": r.get("resource_type", ""),
                    "citation_quality_score": r.get("citation_quality_score", 0),
                })
            return "\n---\n".join(texts)
        except Exception:
            self._last_citations = []
            self._last_rejected_citations = []
            return ""

    def _try_seed_data(self, course_id: str, query: str) -> str:
        try:
            from core.pdf_content_v2.builder import build_evidence_deck
            deck = build_evidence_deck(course_id)
            concepts = deck.get("concepts", {})
            for cid, cdata in concepts.items():
                title = cdata.get("title", "") if isinstance(cdata, dict) else ""
                expl = cdata.get("explanation", "") if isinstance(cdata, dict) else ""
                if title and any(title[i:i+2] in query for i in range(len(title)-1) if len(title[i:i+2])==2):
                    return f"{title}: {expl[:500]}"
            return ""
        except Exception:
            return ""


def detect_course_mismatch(course_id: str, query: str) -> dict | None:
    """Detect if query is about a different course. Returns suggestion."""
    for cid, topics in COURSE_TOPICS.items():
        if cid == course_id:
            continue
        matched = [t for t in topics if t in query]
        if matched:
            return {
                "matched_course_id": cid,
                "matched_course_name": COURSE_NAMES.get(cid, cid),
                "matched_topics": matched,
                "current_course_id": course_id,
            }
    return None
