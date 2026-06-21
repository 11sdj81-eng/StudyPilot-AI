"""AITeacher — transforms structured concept/formula/pattern data into teacher-quality notes.

Course-agnostic: all course differences come from COURSE_TEACHER_RULES.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TeacherNote:
    """A teacher-quality annotation for one concept."""
    concept_id: str
    why_exam_likes_it: str = ""        # 为什么考
    how_it_is_tested: list[str] = field(default_factory=list)  # 怎么考
    common_mistakes: list[str] = field(default_factory=list)   # 怎么错
    scoring_strategy: list[str] = field(default_factory=list)  # 怎么拿分
    beginner_explanation: str = ""     # 基础弱学生解释
    exam_tip: str = ""                # 考前一句提醒
    time_suggestion: str = ""         # 建议用时
    source_level: str = "structured_evidence"
    confidence: float = 0.85

    def is_empty(self) -> bool:
        """Check if any key fields are empty/generic."""
        empty_count = sum(1 for f in [
            self.why_exam_likes_it, self.beginner_explanation, self.exam_tip,
        ] if not f or len(f) < 10)
        return empty_count >= 2

    def teacher_score(self) -> int:
        """Score 0-100 on teacher-likeness."""
        score = 0
        if self.why_exam_likes_it and len(self.why_exam_likes_it) > 15: score += 20
        if self.how_it_is_tested: score += min(20, len(self.how_it_is_tested) * 10)
        if self.common_mistakes: score += min(20, len(self.common_mistakes) * 10)
        if self.scoring_strategy: score += min(15, len(self.scoring_strategy) * 5)
        if self.beginner_explanation and len(self.beginner_explanation) > 20: score += 15
        if self.exam_tip and len(self.exam_tip) > 10: score += 10
        return min(100, score)

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id, "why_exam_likes_it": self.why_exam_likes_it,
            "how_it_is_tested": self.how_it_is_tested, "common_mistakes": self.common_mistakes,
            "scoring_strategy": self.scoring_strategy, "beginner_explanation": self.beginner_explanation,
            "exam_tip": self.exam_tip, "time_suggestion": self.time_suggestion,
            "source_level": self.source_level, "confidence": self.confidence,
            "teacher_score": self.teacher_score(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Course-agnostic teacher rules — keyed by subject_type
# ═══════════════════════════════════════════════════════════════════════════

COURSE_TEACHER_RULES: dict[str, dict] = {
    "math": {
        "subject_type": "math",
        "teacher_style_rules": [
            "强调公式适用条件",
            "强调分布识别（先判断类型再选公式）",
            "强调概率区间（注意开闭区间）",
            "强调标准化步骤（减均值除标准差）",
            "强调补事件技巧（至少问题用 1-P）",
        ],
        "common_exam_language": [
            "求分布律", "求分布函数", "求概率", "求期望和方差",
            "判断分布类型", "求参数", "标准化", "求随机变量函数的分布",
        ],
        "common_mistake_patterns": [
            "忘记归一化条件", "分布类型识别错误",
            "区间开闭搞混", "标准化除以方差而非标准差",
            "二项和超几何混淆", "补事件忘记 1-P",
        ],
        "scoring_style": ["公式选择 2 分", "代入计算 2 分", "结果正确 1 分"],
        "concept_explanation_style": "先直觉→再定义→再公式→再条件→再例题",
    },
    "engineering": {
        "subject_type": "engineering",
        "teacher_style_rules": [
            "强调物理图像和几何对称性",
            "强调边界条件和适用条件",
            "强调方向和单位",
            "强调高斯面选择技巧",
            "强调分段讨论（球内/球外，界面上/下）",
        ],
        "common_exam_language": [
            "求电场强度", "求电位", "判断边界条件",
            "求镜像电荷", "求电容", "求静电能量",
        ],
        "common_mistake_patterns": [
            "对称性不够硬提场强", "高斯面选择不当",
            "球内包围电荷写成总电荷", "切向法向混淆",
            "镜像法忘记说明求解区域", "漏掉负号",
        ],
        "scoring_style": ["公式选择 2 分", "对称性分析 2 分", "计算正确 1 分"],
        "concept_explanation_style": "先物理图像→再数学表达→再适用条件→再典型场景",
    },
}


class AITeacher:
    """Generate TeacherNotes from structured concept/pattern data.

    Course-agnostic: reads teacher rules from COURSE_TEACHER_RULES keyed by subject_type.
    """

    def __init__(self, subject_type: str = "math"):
        self.subject_type = subject_type
        self.rules = COURSE_TEACHER_RULES.get(subject_type, COURSE_TEACHER_RULES["math"])

    def generate(self, concept: dict) -> TeacherNote:
        """Generate a TeacherNote from concept dict data."""
        cid = concept.get("id", concept.get("concept_id", "unknown"))
        title = concept.get("display_name", concept.get("title", cid))
        explanation = concept.get("plain_explanation", concept.get("explanation", ""))
        why = concept.get("why_important", "")
        mistakes = concept.get("common_mistakes", [])
        exam_usage = concept.get("exam_usage", [])
        exam_reminder = concept.get("exam_reminder", "")

        # Build teacher-quality content from structured data
        note = TeacherNote(concept_id=cid)

        # why_exam_likes_it — transform importance into teacher language
        note.why_exam_likes_it = self._build_why(why, title, exam_usage)

        # how_it_is_tested — from exam patterns
        note.how_it_is_tested = list(exam_usage) if exam_usage else [
            f"{title}常在选择题和计算题中出现",
        ]

        # common_mistakes — enhance generic mistakes with course-specific patterns
        note.common_mistakes = self._enhance_mistakes(mistakes, title)

        # scoring_strategy — course-specific scoring rules
        note.scoring_strategy = list(self.rules.get("scoring_style", []))

        # beginner_explanation — simplify the formal explanation
        note.beginner_explanation = self._build_beginner(explanation, title)

        # exam_tip — the one-line reminder
        note.exam_tip = exam_reminder if exam_reminder else self._build_default_tip(title)

        # time_suggestion
        note.time_suggestion = self._time_estimate(cid)

        return note

    def generate_all(self, concepts: list[dict]) -> list[TeacherNote]:
        return [self.generate(c) for c in concepts]

    # ── Internal builders ─────────────────────────────────────────────────

    def _build_why(self, why: str, title: str, exam_usage: list[str]) -> str:
        if why and len(why) > 15:
            return f"{title}是考试重点。{why}"
        if exam_usage:
            types = "、".join(exam_usage[:3])
            return f"{title}常在{types}等题型中出现，是后续知识点的基础。"
        return f"{title}是本章核心概念，多次出现在历年真题中。"

    def _enhance_mistakes(self, mistakes: list[str], title: str) -> list[str]:
        enhanced = list(mistakes) if mistakes else []
        # Add course-specific patterns
        course_patterns = self.rules.get("common_mistake_patterns", [])
        relevant = [p for p in course_patterns if any(
            kw in p for kw in [title[:2], title[-2:]]
        )]
        for p in relevant[:2]:
            if p not in enhanced:
                enhanced.append(p)
        # Ensure at least 2 specific mistakes
        if len(enhanced) < 2:
            enhanced.append(f"{title}相关公式的适用条件容易忽略")
        return enhanced[:4]

    def _build_beginner(self, explanation: str, title: str) -> str:
        """Transform formal explanation into beginner-friendly language."""
        if not explanation:
            return f"{title}是本章的基础概念，建议先看教材定义和一道例题，理解基本含义后再做题。"
        # Simplify: remove equations, keep intuition
        simplified = explanation.replace("设", "假设").replace("若", "如果").replace("则", "那么")
        if len(simplified) > 120:
            simplified = simplified[:120] + "..."
        return f"通俗理解：{simplified}"

    def _build_default_tip(self, title: str) -> str:
        tips = {
            "random_variable": "先区分离散还是连续，再选对应的工具。",
            "distribution_function": "看到分布函数先查两端极限（0和1），再查单调性，最后查右连续。",
            "discrete_random_variable": "列分布律三步：找取值→算概率→验证和为1。",
            "continuous_random_variable": "密度值不是概率！曲线下面积才是。单点概率恒为零。",
            "binomial": "看到'固定次数+独立重复+成功概率不变'→二项分布。",
            "poisson": "看到'稀有事件+单位时间/空间次数'→泊松分布。不要一看到次数就套泊松！",
            "normal": "正态先标准化 Z=(X-μ)/σ，注意除以标准差不是方差！",
            "exponential": "指数分布有无记忆性，均值为1/λ（不是λ！）。",
            "uniform": "均匀分布等可能，密度为1/(b-a)，区间外为0。",
            "rv_function_distribution": "先判断g(x)单调性。单调用公式，非单调用分布函数法分区讨论。",
        }
        for key, tip in tips.items():
            if key in title.lower().replace(" ", "_") or key in title:
                return tip
        return f"{title}：记住公式条件比记住公式本身更重要。"

    def _time_estimate(self, concept_id: str) -> str:
        times = {
            "random_variable": "5分钟理解定义",
            "distribution_function": "15分钟（含性质验证）",
            "discrete_random_variable": "10分钟（含分布律练习）",
            "continuous_random_variable": "15分钟（含密度函数积分）",
            "binomial": "15分钟（含二项公式和泊松近似）",
            "poisson": "10分钟（含近似条件）",
            "normal": "20分钟（含标准化和查表）",
            "exponential": "10分钟（含无记忆性）",
            "uniform": "5分钟",
            "rv_function_distribution": "25分钟（含单调/非单调）",
        }
        return times.get(concept_id, "10分钟")
