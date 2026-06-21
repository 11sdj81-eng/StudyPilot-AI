"""StudentProfileAdapter — adapts PDF content based on student profile.

PDF 5.0: Extends StudentLevelAdapter with full student profile support.
Adjusts explanation depth, example difficulty, and content emphasis
based on: foundation, target score, remaining time, weak points, preference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StudyPreference(Enum):
    SPRINT = "sprint"           # 考前冲刺 — compressed, exam-focused
    SYSTEMATIC = "systematic"   # 系统复习 — deep understanding
    EXAM_DRILL = "exam_drill"   # 真题模拟 — mock exam heavy
    MIXED = "mixed"             # 混合 — balanced


@dataclass
class StudentProfile:
    """Complete student profile for content adaptation.

    PDF 5.0: Drives content variation in all PDF types.
    """
    foundation: str = "normal"       # beginner / normal / advanced
    target_score: float = 75.0       # 0-100
    remaining_weeks: int = 4         # weeks until exam
    weak_points: list[str] = field(default_factory=list)  # concept IDs student struggles with
    study_progress: float = 0.0      # 0.0-1.0 fraction completed
    preference: StudyPreference = StudyPreference.MIXED

    # Derived flags
    @property
    def is_exam_close(self) -> bool:
        return self.remaining_weeks <= 2

    @property
    def is_beginner(self) -> bool:
        return self.foundation == "beginner"

    @property
    def is_advanced(self) -> bool:
        return self.foundation == "advanced"

    @property
    def needs_high_score(self) -> bool:
        return self.target_score >= 85

    @property
    def is_sprint_mode(self) -> bool:
        return (self.preference == StudyPreference.SPRINT or
                self.is_exam_close)

    def to_dict(self) -> dict:
        return {
            "foundation": self.foundation,
            "target_score": self.target_score,
            "remaining_weeks": self.remaining_weeks,
            "weak_points": self.weak_points,
            "study_progress": self.study_progress,
            "preference": self.preference.value,
            "is_exam_close": self.is_exam_close,
            "is_sprint_mode": self.is_sprint_mode,
        }


# ── Profile-based adaptation configs ────────────────────────────────────

PROFILE_CONFIGS = {
    # ── Foundation level + preference ──
    ("beginner", "sprint"): {
        "explanation_style": "minimal — only key points and must-memorize formulas",
        "example_count_multiplier": 0.5,
        "formula_detail": "minimal",
        "emphasis": ["必背公式", "最后5分钟检查", "常见陷阱"],
        "skip_long_explanations": True,
    },
    ("beginner", "systematic"): {
        "explanation_style": "verbose — step-by-step with intuition and examples",
        "example_count_multiplier": 2.0,
        "formula_detail": "full",
        "emphasis": ["为什么这样做", "每一步的依据", "先理解再记公式"],
        "skip_long_explanations": False,
    },
    ("normal", "sprint"): {
        "explanation_style": "compact — key formulas + exam tips + one example",
        "example_count_multiplier": 1.0,
        "formula_detail": "standard",
        "emphasis": ["高频考点", "必背公式", "易错提醒"],
        "skip_long_explanations": True,
    },
    ("normal", "systematic"): {
        "explanation_style": "balanced — formula + example + mistakes + scoring",
        "example_count_multiplier": 1.0,
        "formula_detail": "standard",
        "emphasis": ["公式适用条件", "典型例题", "易错点", "评分标准"],
        "skip_long_explanations": False,
    },
    ("advanced", "sprint"): {
        "explanation_style": "ultra-compact — only complex variants and traps",
        "example_count_multiplier": 0.8,
        "formula_detail": "compact",
        "emphasis": ["变式题", "综合题", "边界情况", "陷阱识别"],
        "skip_long_explanations": True,
    },
    ("advanced", "systematic"): {
        "explanation_style": "comprehensive — variants, proofs, edge cases",
        "example_count_multiplier": 1.5,
        "formula_detail": "compact",
        "emphasis": ["变式题", "综合题", "证明推导", "边界情况"],
        "skip_long_explanations": False,
    },
}

# Default config for unlisted combinations
DEFAULT_PROFILE_CONFIG = {
    "explanation_style": "balanced",
    "example_count_multiplier": 1.0,
    "formula_detail": "standard",
    "emphasis": ["公式", "例题", "易错", "评分"],
    "skip_long_explanations": False,
}


class StudentProfileAdapter:
    """Adapts PDF content generation based on complete student profile.

    PDF 5.0: Replaces the simpler StudentLevelAdapter with full profile support.
    Integration point: called before content assembly in UniversalRenderPipeline.
    """

    def __init__(self, profile: StudentProfile | None = None):
        self.profile = profile or StudentProfile()
        self.config = self._resolve_config()

    def _resolve_config(self) -> dict:
        """Resolve the appropriate config for this student profile."""
        key = (self.profile.foundation, self.profile.preference.value)
        # Handle exam_drill — use systematic for foundation, sprint for delivery
        if self.profile.preference == StudyPreference.EXAM_DRILL:
            key = (self.profile.foundation, "sprint")
        # Handle mixed
        if self.profile.preference == StudyPreference.MIXED:
            key = (self.profile.foundation, "systematic")
        return PROFILE_CONFIGS.get(key, DEFAULT_PROFILE_CONFIG)

    def adapt_example_count(self, base_count: int, concept_id: str = "") -> int:
        """Adjust number of examples based on profile."""
        multiplier = self.config.get("example_count_multiplier", 1.0)
        # Boost for weak points
        if concept_id and concept_id in self.profile.weak_points:
            multiplier *= 1.5
        # Reduce for sprint mode on non-weak points
        if self.profile.is_sprint_mode and concept_id not in self.profile.weak_points:
            multiplier *= 0.7
        return max(1, int(base_count * multiplier))

    def adapt_explanation_depth(self, explanation: str) -> str:
        """Adjust explanation depth."""
        if self.config.get("skip_long_explanations"):
            # Keep only first 2-3 sentences
            sentences = explanation.split("。")
            return "。".join(sentences[:3]) + "。"
        return explanation

    def adapt_difficulty_distribution(self) -> dict:
        """Get the difficulty distribution for MockExam.

        Default: easy 30%, medium 50%, hard 20%
        Adjusts based on foundation level.
        """
        if self.profile.is_beginner:
            return {"easy": 0.40, "medium": 0.45, "hard": 0.15}
        elif self.profile.is_advanced:
            return {"easy": 0.15, "medium": 0.45, "hard": 0.40}
        elif self.profile.is_sprint_mode and self.profile.needs_high_score:
            return {"easy": 0.20, "medium": 0.50, "hard": 0.30}
        else:
            return {"easy": 0.30, "medium": 0.50, "hard": 0.20}

    def adapt_section_emphasis(self, concept_id: str) -> list[str]:
        """Get the emphasis tags for a concept section."""
        emphasis = list(self.config.get("emphasis", []))
        if concept_id in self.profile.weak_points:
            emphasis.insert(0, "薄弱点强化")
        if self.profile.is_exam_close:
            emphasis.insert(0, "考前必看")
        return emphasis

    def get_formula_detail_level(self) -> str:
        """Get the formula detail level for rendering."""
        return self.config.get("formula_detail", "standard")

    def should_include_proofs(self) -> bool:
        """Whether to include mathematical proofs."""
        if self.profile.is_beginner:
            return False
        if self.profile.is_sprint_mode:
            return False
        return self.profile.is_advanced

    def get_study_recommendations(self) -> dict:
        """Generate study recommendations based on profile."""
        recs = {
            "focus_areas": [],
            "time_allocation": {},
            "suggested_pdfs": [],
        }

        if self.profile.is_sprint_mode:
            recs["suggested_pdfs"] = ["Sprint", "MockExam"]
            recs["focus_areas"] = self.profile.weak_points
            recs["time_allocation"] = {"Sprint": "40%", "MockExam": "40%", "Review": "20%"}
        elif self.profile.is_beginner:
            recs["suggested_pdfs"] = ["Review", "Sprint"]
            recs["focus_areas"] = ["基础概念"]
            recs["time_allocation"] = {"Review": "60%", "Sprint": "25%", "PastPaper": "15%"}
        elif self.profile.needs_high_score:
            recs["suggested_pdfs"] = ["Review", "PastPaper", "MockExam"]
            recs["focus_areas"] = ["综合题", "变式题"]
            recs["time_allocation"] = {"Review": "30%", "PastPaper": "30%", "MockExam": "40%"}
        else:
            recs["suggested_pdfs"] = ["Review", "Sprint", "MockExam"]
            recs["time_allocation"] = {"Review": "40%", "Sprint": "30%", "MockExam": "30%"}

        return recs

    def to_dict(self) -> dict:
        return {
            "profile": self.profile.to_dict(),
            "config": self.config,
            "recommendations": self.get_study_recommendations(),
        }


# ── Factory ─────────────────────────────────────────────────────────────

def create_default_adapter() -> StudentProfileAdapter:
    """Create an adapter with default ('normal') student profile."""
    return StudentProfileAdapter(StudentProfile())


def create_sprint_adapter(target_score: float = 75.0) -> StudentProfileAdapter:
    """Create an adapter optimized for exam sprint mode."""
    return StudentProfileAdapter(StudentProfile(
        foundation="normal",
        target_score=target_score,
        remaining_weeks=1,
        preference=StudyPreference.SPRINT,
    ))


def create_beginner_adapter() -> StudentProfileAdapter:
    """Create an adapter for beginner students."""
    return StudentProfileAdapter(StudentProfile(
        foundation="beginner",
        target_score=60.0,
        remaining_weeks=8,
        preference=StudyPreference.SYSTEMATIC,
    ))
