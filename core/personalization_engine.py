"""StudyPilot v1.3 — Personalization Engine.

Generates PersonalizedPlan from UserProfile, driving:
- Today's learning suggestion
- Recommended PDF types
- Learning path & time allocation
- Result-page study advice
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.user_profile import UserProfile, load_profile


@dataclass
class PersonalizedPlan:
    """A personalized learning plan generated from user profile."""

    scenario: str
    recommended_outputs: list[str]
    focus_points: list[str]
    time_plan: list[dict[str, Any]]
    next_actions: list[str]
    warning: str | None
    bunny_message: str
    summary_text: str = ""


# ── Knowledge-graph-aware learning path ────────────────────────────────────

DEFAULT_LEARNING_PATH = [
    {"id": "electric_field", "name": "电场强度", "order": 1},
    {"id": "gauss_law", "name": "高斯定理", "order": 2},
    {"id": "potential_gradient", "name": "电位与梯度", "order": 3},
    {"id": "boundary_condition", "name": "边界条件", "order": 4},
    {"id": "mirror_method", "name": "镜像法", "order": 5},
    {"id": "electrostatic_energy", "name": "静电能量", "order": 6},
]

CONCEPT_PDF_MAP = {
    "gauss_law": ["Review", "PastPaper"],
    "electric_field": ["Review"],
    "potential_gradient": ["Review"],
    "boundary_condition": ["Review", "PastPaper", "MockExam"],
    "mirror_method": ["Review", "PastPaper", "MockExam"],
    "electrostatic_energy": ["Review"],
}


# ── Engine ──────────────────────────────────────────────────────────────────


class PersonalizationEngine:
    """Generate personalized learning plans from a UserProfile."""

    def __init__(self, profile: UserProfile | None = None):
        self.profile = profile or load_profile()

    # ── Main plan ────────────────────────────────────────────────────────

    def build_plan(self) -> PersonalizedPlan:
        """Build a full personalized plan."""
        scenario = self.profile.scenario
        outputs = self._recommend_outputs(scenario)
        focus = self._compute_focus_points()
        time_plan = self._build_time_plan(scenario, focus)
        next_actions = self._build_next_actions(outputs)
        warning = self._compute_warning(scenario)
        bunny = self._bunny_for_plan(scenario, focus, outputs)

        return PersonalizedPlan(
            scenario=scenario,
            recommended_outputs=outputs,
            focus_points=focus,
            time_plan=time_plan,
            next_actions=next_actions,
            warning=warning,
            bunny_message=bunny,
        )

    def build_today_card(self) -> dict[str, Any]:
        """Build the 'Today's Status' card data for the home page."""
        p = self.profile
        plan = self.build_plan()

        if not p.course_name and not p.weak_points:
            return {
                "has_profile": False,
                "message": "先告诉 StudyPilot：你要考什么、剩多少时间、哪里不会。",
                "action_hint": "在下方输入框中告诉我你的学习目标～",
            }

        return {
            "has_profile": True,
            "course": p.course_name or "未设置",
            "chapter": p.chapter_name or "未设置",
            "target_score": p.target_score,
            "remaining_time": (
                f"{p.remaining_hours_today}小时"
                if p.remaining_hours_today
                else f"{p.remaining_days}天" if p.remaining_days else "未设置"
            ),
            "weak_points": p.weak_points if p.weak_points else ["未设置"],
            "scenario": plan.scenario,
            "scenario_label": _scenario_label(plan.scenario),
            "recommended_action": plan.next_actions[0] if plan.next_actions else "生成 Review",
            "bunny_message": plan.bunny_message,
        }

    def build_result_advice(self, generated_types: list[str]) -> dict[str, Any]:
        """Build result-page learning advice based on what was generated."""
        p = self.profile
        plan = self.build_plan()

        study_order: list[str] = []
        if "Sprint" in generated_types:
            study_order.append("1. 先看 Sprint 第 2–4 页的核心图像和救命卡")
        if "PastPaper" in generated_types:
            study_order.append("2. 做 PastPaper 题，重点关注老师怎么考")
        if "MockExam" in generated_types:
            study_order.append("3. 用 MockExam 大题自测，检查步骤完整性")
        if "Review" in generated_types:
            study_order.append("4. Review 建议逐节阅读，配合公式系统消化")

        # Coverage
        covered = set()
        for c in plan.focus_points:
            covered.add(c)
        for wp in p.weak_points[:3]:
            covered.add(wp)

        coverage = list(covered) if covered else plan.focus_points

        return {
            "study_order": study_order if study_order else ["按生成顺序复习，重点看高频考点。"],
            "coverage": coverage,
            "usage_tags": _build_usage_tags(generated_types),
            "next_suggestions": plan.next_actions,
            "bunny_message": self._bunny_for_results(generated_types),
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _recommend_outputs(self, scenario: str) -> list[str]:
        """Recommend PDF types based on scenario and profile."""
        p = self.profile

        if scenario == "exam_sprint":
            return ["Sprint", "PastPaper"]
        elif scenario == "targeted_improvement":
            return ["PastPaper", "MockExam", "Review"]
        elif scenario == "intensive_review":
            return ["Review", "PastPaper", "Sprint"]
        else:  # systematic_study
            return ["Review", "PastPaper"]

    def _compute_focus_points(self) -> list[str]:
        """Determine which concepts to focus on."""
        p = self.profile
        if p.weak_points:
            return p.weak_points[:4]
        # Default: all concepts in path
        return [node["name"] for node in DEFAULT_LEARNING_PATH[:4]]

    def _build_time_plan(self, scenario: str, focus: list[str]) -> list[dict[str, Any]]:
        """Build a time-allocation plan."""
        p = self.profile
        hours = p.remaining_hours_today or 4.0

        if scenario == "exam_sprint":
            return [
                {"duration": f"0–{int(hours * 0.25 * 60)} 分钟", "action": "看 Sprint 核心图像和救命卡"},
                {"duration": f"{int(hours * 0.25 * 60)}–{int(hours * 0.75 * 60)} 分钟", "action": f"做 PastPaper 重点题：{', '.join(focus[:2])}"},
                {"duration": f"{int(hours * 0.75 * 60)}–{int(hours * 60)} 分钟", "action": "回看错题和公式"},
            ]
        elif scenario == "targeted_improvement":
            return [
                {"duration": "第 1 天", "action": f"Review 精读薄弱点：{', '.join(focus[:2])}"},
                {"duration": "第 2 天", "action": f"PastPaper + MockExam 刷题"},
                {"duration": "第 3 天", "action": "错题回顾 + Sprint 速记"},
            ]
        else:
            return [
                {"duration": "每次 60–90 分钟", "action": "逐节阅读 Review + 做对应 PastPaper 题"},
                {"duration": "每周 1 次", "action": "MockExam 自测"},
                {"duration": "考前 1 天", "action": "Sprint 速记 + 公式卡"},
            ]

    def _build_next_actions(self, outputs: list[str]) -> list[str]:
        """Suggest the next actions for the user."""
        return [f"生成 {o}" for o in outputs]

    def _compute_warning(self, scenario: str) -> str | None:
        p = self.profile
        if scenario == "exam_sprint" and not p.weak_points:
            return "你没有指定薄弱点，Sprint 将使用默认重点。建议明确告诉我不稳的知识点。"
        if p.remaining_hours_today and p.remaining_hours_today <= 1:
            return f"时间非常紧张（{p.remaining_hours_today}小时），建议只做 Sprint，放弃完整 Review。"
        return None

    def _bunny_for_plan(
        self, scenario: str, focus: list[str], outputs: list[str]
    ) -> str:
        p = self.profile
        hours = p.remaining_hours_today

        if scenario == "exam_sprint":
            if hours and hours <= 3:
                return f"🐰 你现在只有 {hours:.0f} 小时，不建议完整学 Review，先看 Sprint 和 PastPaper。"
            return "🐰 考前冲刺模式！稳住高频大题入口，不要贪多。"

        if p.weak_points:
            wp_str = "、".join(p.weak_points[:2])
            return f"🐰 {wp_str} 都是大题入口，建议先做这两类题。"

        return f"🐰 建议从 {outputs[0] if outputs else 'Review'} 开始，系统掌握每个概念。"

    def _bunny_for_results(self, generated_types: list[str]) -> str:
        if "MockExam" in generated_types:
            return "🐰 这份 MockExam 适合用来检查你能不能把步骤写完整。"
        if "Sprint" in generated_types:
            return "🐰 考前 30 分钟再把 Sprint 拿出来看一遍。"
        if "Review" in generated_types:
            return "🐰 Review 是系统学习的核心，配合 PastPaper 效果更好。"
        return "🐰 资料已就绪，开始复习吧！"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _scenario_label(scenario: str) -> str:
    return {
        "exam_sprint": "🚨 考前冲刺",
        "targeted_improvement": "🎯 针对性提升",
        "intensive_review": "📚 集中复习",
        "systematic_study": "📖 系统学习",
    }.get(scenario, scenario)


def _build_usage_tags(generated_types: list[str]) -> list[dict[str, str]]:
    tag_map = {
        "Sprint": {"label": "考前 30 分钟", "icon": "⚡"},
        "PastPaper": {"label": "做题后复盘", "icon": "🎯"},
        "MockExam": {"label": "完整自测", "icon": "📝"},
        "Review": {"label": "章节复习", "icon": "📖"},
    }
    return [tag_map[t] for t in generated_types if t in tag_map]


def build_learning_path_nodes(
    profile: UserProfile | None = None,
) -> list[dict[str, Any]]:
    """Build learning path nodes, highlighting weak points."""
    profile = profile or load_profile()
    weak_ids = {wp for wp in profile.weak_points}
    nodes = []

    for node in DEFAULT_LEARNING_PATH:
        is_weak = node["name"] in weak_ids
        nodes.append({
            **node,
            "is_weak": is_weak,
            "priority_label": "⚠️ 优先复习" if is_weak else None,
            "recommended_pdfs": CONCEPT_PDF_MAP.get(node["id"], ["Review"]),
        })

    return nodes
