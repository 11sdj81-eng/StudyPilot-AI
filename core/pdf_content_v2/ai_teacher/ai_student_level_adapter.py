"""Student level adaptation — adjust teaching depth for different learner profiles."""

from __future__ import annotations

from enum import Enum
from typing import Any

from core.pdf_content_v2.ai_teacher.ai_teacher import TeacherNote


class StudentLevel(Enum):
    BEGINNER = "beginner"
    NORMAL = "normal"
    ADVANCED = "advanced"
    EXAM_SPRINT = "exam_sprint"


LEVEL_CONFIG: dict[StudentLevel, dict] = {
    StudentLevel.BEGINNER: {
        "label": "基础弱",
        "explanation_style": "多直觉、多比喻、少公式、明确步骤",
        "example_count": 2,  # more basic examples
        "formula_detail": "full",  # show every step
        "skip_proofs": True,
        "emphasis": ["为什么这样做", "每一步的依据", "别怕，先理解再记公式"],
    },
    StudentLevel.NORMAL: {
        "label": "普通",
        "explanation_style": "公式+例题+易错点平衡",
        "example_count": 1,
        "formula_detail": "standard",
        "skip_proofs": False,
        "emphasis": ["公式适用条件", "典型例题", "易错点"],
    },
    StudentLevel.ADVANCED: {
        "label": "强化",
        "explanation_style": "增加变式题、综合题、推导",
        "example_count": 2,  # more complex examples
        "formula_detail": "compact",  # concise
        "skip_proofs": False,
        "emphasis": ["变式题", "综合题", "证明推导", "边界情况"],
    },
    StudentLevel.EXAM_SPRINT: {
        "label": "考前冲刺",
        "explanation_style": "只保留高频考点、必背公式、最后检查清单",
        "example_count": 1,  # one key example per concept
        "formula_detail": "minimal",  # just the formula
        "skip_proofs": True,
        "emphasis": ["高频考法", "必背公式", "最后5分钟检查", "常见陷阱"],
    },
}


class StudentLevelAdapter:
    """Adapt TeacherNote content for different student proficiency levels."""

    def __init__(self, level: StudentLevel = StudentLevel.NORMAL):
        self.level = level
        self.config = LEVEL_CONFIG.get(level, LEVEL_CONFIG[StudentLevel.NORMAL])

    def adapt(self, note: TeacherNote) -> TeacherNote:
        """Adapt a TeacherNote to the current student level."""
        adapted = TeacherNote(concept_id=note.concept_id)

        if self.level == StudentLevel.BEGINNER:
            adapted.why_exam_likes_it = self._beginner_why(note)
            adapted.beginner_explanation = self._expand_beginner(note)
            adapted.common_mistakes = [f"⚠️ 易错：{m}" for m in note.common_mistakes[:3]]
            adapted.exam_tip = f"💡 基础弱学生建议：{note.exam_tip}"
            adapted.time_suggestion = f"{note.time_suggestion}（建议延长 1.5 倍）"

        elif self.level == StudentLevel.NORMAL:
            adapted.why_exam_likes_it = note.why_exam_likes_it
            adapted.how_it_is_tested = note.how_it_is_tested
            adapted.common_mistakes = note.common_mistakes
            adapted.scoring_strategy = note.scoring_strategy
            adapted.beginner_explanation = note.beginner_explanation
            adapted.exam_tip = note.exam_tip
            adapted.time_suggestion = note.time_suggestion

        elif self.level == StudentLevel.ADVANCED:
            adapted.why_exam_likes_it = f"{note.why_exam_likes_it} 进阶提示：注意变式和综合题中与其他知识点的交叉考法。"
            adapted.how_it_is_tested = list(note.how_it_is_tested) + ["综合题中常与其它知识点联合考查"]
            adapted.common_mistakes = [f"进阶易错：{m}" for m in note.common_mistakes[:2]]
            adapted.scoring_strategy = note.scoring_strategy
            adapted.exam_tip = f"强化：{note.exam_tip}"

        elif self.level == StudentLevel.EXAM_SPRINT:
            adapted.why_exam_likes_it = f"⚡ 高频考点：{note.why_exam_likes_it[:60]}"
            adapted.how_it_is_tested = [h for h in note.how_it_is_tested[:1]]
            adapted.common_mistakes = [f"⚠️ {m}" for m in note.common_mistakes[:2]]
            adapted.scoring_strategy = note.scoring_strategy[:1]
            adapted.exam_tip = f"⚡ {note.exam_tip}"
            adapted.time_suggestion = f"冲刺：{note.time_suggestion.split('（')[0]}"

        adapted.source_level = note.source_level
        adapted.confidence = note.confidence
        return adapted

    def _beginner_why(self, note: TeacherNote) -> str:
        return f"别怕，{note.concept_id}其实不难理解。{note.why_exam_likes_it}"

    def _expand_beginner(self, note: TeacherNote) -> str:
        base = note.beginner_explanation or ""
        if len(base) < 30:
            base = f"建议先看一遍教材上关于{note.concept_id}的定义和第一道例题，再回来看这个解释。"
        return f"【基础弱学生友好版】{base}"
