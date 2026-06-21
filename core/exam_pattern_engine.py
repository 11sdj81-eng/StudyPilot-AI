"""Exam Pattern Engine — powers "怎么考" with real exam pattern data.

Loads exam patterns from golden_chapters and exam_patterns directories.
If no exam data exists, clearly states "无真题数据" so LLM doesn't fabricate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.config import DATA_DIR

# ═══════════════════════════════════════════════════════════════════════════
# Course ID → golden chapter path mapping
# ═══════════════════════════════════════════════════════════════════════════

COURSE_EXAM_PATHS = {
    "probability_ch2": [
        DATA_DIR / "exam_patterns" / "probability_ch2.json",
        DATA_DIR / "golden_chapters" / "math" / "probability_random_var_ch2" / "exam_patterns.json",
    ],
    "field_wave_ch1": [
        DATA_DIR / "golden_chapters" / "engineering" / "electromagnetic_static_chapter1" / "exam_patterns.json",
        DATA_DIR / "exam_patterns" / "engineering" / "electromagnetic_static_chapter1" / "patterns.json",
    ],
    "digital_logic_ch3": [
        DATA_DIR / "exam_patterns" / "digital_logic_ch3.json",
        DATA_DIR / "golden_chapters" / "engineering" / "digital_logic_ch3_demo" / "exam_patterns.json",
    ],
}

# Fallback concepts file for each course (used when no exam patterns exist)
COURSE_CONCEPT_PATHS = {
    "probability_ch2": DATA_DIR / "golden_chapters" / "math" / "probability_random_var_ch2" / "concepts.json",
    "field_wave_ch1": DATA_DIR / "golden_chapters" / "engineering" / "electromagnetic_static_chapter1" / "concepts.json",
    "digital_logic_ch3": DATA_DIR / "golden_chapters" / "engineering" / "digital_logic_ch3_demo" / "concepts.json",
}


class ExamPatternEngine:
    """Load, search, and format exam patterns for AI tutor responses."""

    def __init__(self):
        self._cache: dict[str, list[dict]] = {}

    # ═══════════════════════════════════════════════════════════════════
    # Loading
    # ═══════════════════════════════════════════════════════════════════

    def load(self, course_id: str) -> list[dict]:
        """Load exam patterns for a course. Returns empty list if none found."""
        if course_id in self._cache:
            return self._cache[course_id]

        paths = COURSE_EXAM_PATHS.get(course_id, [])
        all_patterns: list[dict] = []

        for path in paths:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        all_patterns.extend(data)
                    elif isinstance(data, dict):
                        # Some files have patterns wrapped in a dict
                        all_patterns.extend(data.get("patterns", data.get("cases", [])))
                except (json.JSONDecodeError, FileNotFoundError):
                    continue

        self._cache[course_id] = all_patterns
        return all_patterns

    def has_exam_data(self, course_id: str) -> bool:
        """Check if real exam pattern data exists for this course."""
        return len(self.load(course_id)) > 0

    # ═══════════════════════════════════════════════════════════════════
    # Search
    # ═══════════════════════════════════════════════════════════════════

    def search(
        self,
        course_id: str,
        concept_or_keyword: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Search exam patterns by concept or keyword.

        Matches against: concept_ids, display_name, how_tested, id, type fields.
        Returns top_k best matches sorted by relevance score.
        """
        patterns = self.load(course_id)
        if not patterns:
            return []

        keyword = concept_or_keyword.strip().lower()
        scored: list[tuple[int, dict]] = []

        for idx, pat in enumerate(patterns):
            score = 0

            # Exact match in concept_ids
            concept_ids = pat.get("concept_ids", [])
            if isinstance(concept_ids, list):
                for cid in concept_ids:
                    if keyword in str(cid).lower():
                        score += 10
                        break

            # Display name match
            display = str(pat.get("display_name", pat.get("source_label", ""))).lower()
            if keyword in display:
                score += 8

            # how_tested match
            how = str(pat.get("how_tested", "")).lower()
            if keyword in how:
                score += 5

            # Pattern id match
            pid = str(pat.get("id", pat.get("pattern_id", ""))).lower()
            if keyword in pid:
                score += 3

            # Type match
            qtype = str(pat.get("type", pat.get("question_type", ""))).lower()
            if keyword in qtype:
                score += 2

            # Trap match (secondary signal)
            trap = str(pat.get("trap", pat.get("common_traps", ""))).lower()
            if keyword in trap:
                score += 1

            # source_label match
            label = str(pat.get("source_label", "")).lower()
            if keyword in label:
                score += 3

            # teacher_intent match
            intent = str(pat.get("teacher_intent", "")).lower()
            if keyword in intent:
                score += 2

            if score > 0:
                scored.append((score, pat))

        # Sort by score descending, return top_k
        scored.sort(key=lambda x: -x[0])
        return [pat for _, pat in scored[:top_k]]

    # ═══════════════════════════════════════════════════════════════════
    # Formatting for LLM
    # ═══════════════════════════════════════════════════════════════════

    def format_for_llm(
        self,
        course_id: str,
        concept: str,
        patterns: list[dict] | None = None,
    ) -> dict:
        """Format exam patterns as structured text for the LLM system prompt.

        Returns dict with:
            exam_context: str — text to inject into LLM prompt
            has_real_data: bool — whether this is real exam data or needs disclaimer
            pattern_count: int
        """
        if patterns is None:
            patterns = self.search(course_id, concept)

        if not patterns:
            return {
                "exam_context": self._no_data_message(course_id, concept),
                "has_real_data": False,
                "pattern_count": 0,
            }

        lines = [f"## 真实真题数据 — {concept}"]
        lines.append("以下考试模式来自往年真题和教材分析：\n")

        for i, pat in enumerate(patterns, 1):
            # Normalize field names across different pattern formats
            qtype = pat.get("type") or pat.get("question_type") or "未知"
            how = pat.get("how_tested") or ""
            trap = pat.get("trap") or pat.get("common_traps") or ""
            if isinstance(trap, list):
                trap = "；".join(trap)
            score_w = pat.get("score_weight") or pat.get("score") or ""
            display = pat.get("display_name") or pat.get("source_label") or ""
            intent = pat.get("teacher_intent") or ""
            steps = pat.get("required_steps") or []
            if isinstance(steps, list):
                steps = " → ".join(steps)
            sample = pat.get("sample_problem") or ""
            grading = pat.get("grading_points") or []
            if isinstance(grading, list):
                grading = "；".join(grading)

            # Source refs
            sources = pat.get("source_refs", [])
            source_str = ""
            if sources:
                parts = []
                for s in sources[:2]:
                    fn = s.get("file_name", "")
                    yr = s.get("year", "")
                    qn = s.get("question_no", "")
                    note = s.get("note", "")
                    parts.append(f"{fn} {yr} {qn} {note}".strip())
                source_str = "；".join(parts)

            lines.append(
                f"**题型{i}: [{qtype}] {display}**（分值: {score_w}）\n"
                f"- 考法: {how}\n"
                f"- 易错点: {trap}"
            )
            if intent:
                lines.append(f"- 出题意图: {intent}")
            if steps:
                lines.append(f"- 解题步骤: {steps}")
            if sample:
                lines.append(f"- 样题: {sample}")
            if grading:
                lines.append(f"- 评分要点: {grading}")
            if source_str:
                lines.append(f"- 来源: {source_str}")
            lines.append("")

        return {
            "exam_context": "\n".join(lines),
            "has_real_data": True,
            "pattern_count": len(patterns),
        }

    # ═══════════════════════════════════════════════════════════════════
    # No-data fallback
    # ═══════════════════════════════════════════════════════════════════

    def _no_data_message(self, course_id: str, concept: str) -> str:
        """Message when no exam data exists — honest, not fabricated."""
        return (
            f"⚠️ 该课程暂无 {concept} 的真实真题数据。"
            f"\n请在回答中明确说明：「暂无真题数据，以下为基于通用教学规律的分析（AI_GENERAL）」。"
            f"\n不要编造真题年份、题型分布或分值信息。"
        )

    # ═══════════════════════════════════════════════════════════════════
    # Concept-level exam info (from concepts.json)
    # ═══════════════════════════════════════════════════════════════════

    def get_concept_exam_info(self, course_id: str, concept: str) -> str:
        """Get exam-related info from concepts.json as supplementary context."""
        path = COURSE_CONCEPT_PATHS.get(course_id)
        if not path or not path.exists():
            return ""

        try:
            concepts = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return ""

        for c in concepts:
            cid = c.get("id", "")
            name = c.get("name", c.get("display_name", ""))
            # Match by id or name
            if concept.lower() in str(cid).lower() or concept in name:
                parts = []
                exam_usage = c.get("exam_usage", [])
                if exam_usage:
                    parts.append("常见考法：" + "；".join(exam_usage))
                exam_reminder = c.get("exam_reminder", "")
                if exam_reminder:
                    parts.append("考试提醒：" + exam_reminder)
                common_mistakes = c.get("common_mistakes", [])
                if common_mistakes:
                    parts.append("易错点：" + "；".join(common_mistakes))
                why = c.get("why_important", "")
                if why:
                    parts.append("重要性：" + why)
                return "\n".join(parts)

        return ""


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

_exam_engine: ExamPatternEngine | None = None


def get_exam_engine() -> ExamPatternEngine:
    global _exam_engine
    if _exam_engine is None:
        _exam_engine = ExamPatternEngine()
    return _exam_engine
