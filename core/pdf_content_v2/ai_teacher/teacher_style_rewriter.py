"""TeacherStyleRewriter — rewrites AI explanations into teacher voice.

PDF 5.0: Transforms generic AI summaries into teacher-style lecture notes
with exam tips, warnings, and conversational tone. Scores teacher-likeness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TeacherStyleReport:
    """Result of teacher style rewriting."""
    concept_id: str
    original: str
    rewritten: str
    teacher_like_score: int = 0
    improvements: list[str] = field(default_factory=list)
    source_level: str = "AI_REWRITTEN"


class TeacherStyleRewriter:
    """Rewrites concept explanations into teacher lecture voice.

    Rules-based approach (no LLM dependency). Falls back gracefully.
    Applies teaching patterns, exam tips, warning phrases, and conversational tone.
    """

    # Phrases that indicate teacher voice (used for scoring)
    TEACHER_PHRASES = [
        "注意", "考点", "易错", "提醒", "记住", "关键", "重点",
        "考试中", "真题中", "每年都考", "必考", "高频",
        "不要", "避免", "千万", "务必",
        "举个例子", "通俗地说", "简单理解",
    ]

    # Phrases that indicate generic AI summary (penalized)
    AI_SUMMARY_PHRASES = [
        "该知识点很重要", "建议掌握", "需要理解",
        "在考试中经常出现", "是重点内容",
    ]

    # Teaching patterns to apply
    TEACHING_PATTERNS = {
        "why_tested": [
            "老师提醒：考试中这个知识点主要考察{context}。",
            "考点定位：{context} — 近5年出现{freq}次。",
        ],
        "how_tested": [
            "常见题型：{types}",
            "考法总结：通常以{types}形式出现。",
        ],
        "mistake_warning": [
            "⚠️ 易错警告：{mistake}",
            "做错最多的三种情况：{mistakes}",
        ],
        "scoring_tip": [
            "拿分关键：{tip}",
            "评分标准：{points}",
        ],
        "beginner_help": [
            "通俗理解：{explanation}",
            "零基础入门：先记住{key_point}，再理解{deeper}。",
        ],
        "exam_sprint": [
            "考前必背：{formula}",
            "最后5分钟检查：{checklist}",
        ],
    }

    def __init__(self, subject_type: str = "unknown", course_name: str = ""):
        self.subject_type = subject_type
        self.course_name = course_name

    def rewrite(self, concept_id: str, original_explanation: str,
                concept_data: dict | None = None,
                exam_patterns: list[dict] | None = None) -> TeacherStyleReport:
        """Rewrite an explanation into teacher voice.

        Args:
            concept_id: Concept identifier
            original_explanation: Raw AI/structured explanation
            concept_data: Optional concept metadata (formulas, mistakes, etc.)
            exam_patterns: Optional exam pattern data

        Returns:
            TeacherStyleReport with rewritten text and score
        """
        report = TeacherStyleReport(
            concept_id=concept_id,
            original=original_explanation,
            rewritten=original_explanation,  # default: no change
        )

        concept_data = concept_data or {}
        improvements = []

        # 1. Add "为什么考" if missing
        if "为什么" not in original_explanation and "考" not in original_explanation:
            why = self._build_why_tested(concept_data, exam_patterns)
            if why:
                improvements.append("added_why_tested")

        # 2. Add "怎么考" if exam data available
        how = self._build_how_tested(exam_patterns)
        if how:
            improvements.append("added_how_tested")

        # 3. Add "易错点" if mistakes available
        mistakes = concept_data.get("common_mistakes", [])
        if mistakes:
            improvements.append("added_mistake_warnings")

        # 4. Add "怎么拿分"
        scoring = concept_data.get("grading_points", [])
        if scoring:
            improvements.append("added_scoring_tips")

        # 5. Assemble rewritten text
        parts = []
        if "added_why_tested" in improvements:
            parts.append(why)
        parts.append(original_explanation)
        if "added_how_tested" in improvements:
            parts.append(how)
        if "added_mistake_warnings" in improvements and mistakes:
            parts.append(f"⚠️ 易错警告：{'；'.join(mistakes[:3])}")
        if "added_scoring_tips" in improvements and scoring:
            parts.append(f"拿分关键：{'；'.join(str(s) for s in scoring[:3])}")

        report.rewritten = "\n\n".join(parts)
        report.improvements = improvements
        report.teacher_like_score = self._score(report.rewritten)
        report.source_level = "AI_REWRITTEN" if improvements else "AI_DERIVED"

        return report

    def rewrite_batch(self, concepts: list[dict]) -> list[TeacherStyleReport]:
        """Rewrite multiple concept explanations."""
        return [
            self.rewrite(
                concept_id=c.get("concept_id", c.get("id", "")),
                original_explanation=c.get("explanation", c.get("definition", "")),
                concept_data=c,
                exam_patterns=c.get("exam_patterns"),
            )
            for c in concepts
        ]

    def score_teacher_likeness(self, text: str) -> int:
        """Score a text 0-100 on teacher-likeness."""
        return self._score(text)

    def _score(self, text: str) -> int:
        """Internal scoring based on teacher phrases, conversational tone, etc."""
        score = 40  # base

        # Teacher phrase bonuses
        teacher_count = sum(1 for p in self.TEACHER_PHRASES if p in text)
        score += min(30, teacher_count * 5)

        # AI summary penalties
        ai_count = sum(1 for p in self.AI_SUMMARY_PHRASES if p in text)
        score -= min(20, ai_count * 10)

        # Length bonus (teachers are verbose in a good way)
        if len(text) > 200:
            score += 10
        elif len(text) < 50:
            score -= 10

        # Specificity bonus (numbers, formulas, references = concrete)
        import re
        has_numbers = bool(re.search(r'\d', text))
        has_formulas = bool(re.search(r'[=→+]', text))
        if has_numbers:
            score += 10
        if has_formulas:
            score += 10

        return max(0, min(100, score))

    def _build_why_tested(self, concept_data: dict,
                          exam_patterns: list[dict] | None) -> str:
        """Build '为什么考' section."""
        freq = concept_data.get("exam_frequency", 0)
        if exam_patterns:
            freq = len(exam_patterns)

        if freq >= 3:
            return f"老师提醒：这个知识点是高频考点，近5年出现{freq}次，务必掌握所有考法。"
        elif freq >= 1:
            return f"考点定位：基础必会内容，考试中通常出现{freq}次，建议做至少1道例题。"
        return ""

    def _build_how_tested(self, exam_patterns: list[dict] | None) -> str:
        """Build '怎么考' section."""
        if not exam_patterns:
            return ""
        types = list(set(p.get("type", p.get("question_type", ""))
                        for p in exam_patterns))
        if types:
            return f"常见题型：{' / '.join(types[:3])}"
        return ""


def rewrite_teacher_style(concept_id: str, explanation: str,
                          concept_data: dict | None = None,
                          subject_type: str = "unknown") -> TeacherStyleReport:
    """Convenience function for teacher style rewriting."""
    rewriter = TeacherStyleRewriter(subject_type=subject_type)
    return rewriter.rewrite(concept_id, explanation, concept_data)
