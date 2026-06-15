"""StudyPilot AI — 🐰 Study Bunny assistant state (v1.3).

Profile-aware contextual tips, encouragement messages, and mood state.
Text-only for v1.x; 3D rabbit reserved for future.
"""

from __future__ import annotations

import random
from typing import Any

# ── Bunny tips by context ───────────────────────────────────────────────────

BUNNY_TIPS: dict[str, list[str]] = {
    "home": [
        "告诉我你的学习目标，我来帮你规划～",
        "上传教材和真题，我能更准确地帮你复习。",
        "今天不用学完全部，只要比昨天清楚一点。",
    ],
    "home_with_profile": [
        "欢迎回来！继续你的复习计划吧～",
        "上次的复习计划还记得吗？可以先看看今天的状态卡。",
        "你的薄弱点我已经记住了，生成了针对性资料～",
    ],
    "goal": [
        "设定清晰的目标，学习更有方向感！",
        "把薄弱点告诉我，我会重点帮你攻克。",
    ],
    "upload": [
        "教材用来提取概念和公式，真题用来分析考法。",
        "上传越多资料，我越了解老师的出题风格～",
        "PPT 解析当前为 Beta，优先提取文本与标题结构。",
    ],
    "ai_recognition": [
        "我根据文件名和内容做了初步识别，你可以手动调整。",
        "确认课程和章节信息，我会更准确地匹配考点。",
    ],
    "preferences": [
        "选择你喜欢的输出风格，让资料更适合你的学习习惯。",
        "开启真题驱动模式，我会优先匹配历年高频考点。",
        "插图可以帮助理解空间关系，但太多可能影响打印。",
    ],
    "progress": [
        "正在帮你找老师最爱考的点…",
        "正在整理公式，不让 AI 乱写符号…",
        "正在检查有没有空公式和科学垃圾…",
        "正在生成适合打印的讲义…",
        "快了快了，我在努力让你的复习更有底气！",
        "每份资料都是为你定制的，值得等待～",
        "正在对齐教材符号体系，确保公式一致…",
    ],
    "results_sprint": [
        "检测到你正在考前冲刺，建议先生成 Sprint。",
        "这份 Sprint 适合考前 30 分钟，不建议作为唯一复习资料。",
    ],
    "results_mock": [
        "做完 MockExam 后，建议生成 PastPaper 对照高频题。",
        "模拟考试帮你查漏，看看哪个知识点还薄弱～",
    ],
    "results_review": [
        "建议考前再生成一份 Sprint 快速过一遍。",
        "Review 是系统学习的核心，配合 Sprint 效果更好。",
    ],
    "results_past_paper": [
        "真题帮你了解老师的出题思路，不是背答案哦～",
    ],
    "next_steps": [
        "继续生成下一份资料，让复习更完整。",
        "也可以回到首页，重新告诉我你的需求。",
    ],
    "cleanup": [
        "清理旧文件可以释放磁盘空间，建议只保留最近几次生成。",
        "标记为 final 的文件不会被清理哦～",
    ],
    "error": [
        "生成好像遇到了一点问题，试试重新生成？",
        "如果一直失败，可以尝试简化需求再试～",
    ],
}

BUNNY_MOODS = {
    "neutral": "🐰",
    "happy": "🐰✨",
    "thinking": "🐰💭",
    "working": "🐰📝",
    "excited": "🐰🎉",
    "encourage": "🐰💪",
    "warning": "🐰⚠️",
    "error": "🐰😢",
}


# ── Profile-aware message ──────────────────────────────────────────────────


def get_bunny_message(
    step: str,
    context: dict | None = None,
    profile: Any = None,
) -> str:
    """Return a context-appropriate bunny tip.

    Args:
        step: Current wizard step key.
        context: Optional dict with task_type, quality_score, mode, etc.
        profile: Optional UserProfile for personalized messages.

    Returns:
        A short, encouraging message string.
    """
    context = context or {}

    # Map task_type to more specific results tips
    if step == "results":
        task_type = context.get("task_type", "")
        if task_type in ("exam_sprint", "考前冲刺"):
            step = "results_sprint"
        elif task_type in ("mock_exam", "模拟试卷"):
            step = "results_mock"
        elif task_type in ("past_paper", "真题精讲"):
            step = "results_past_paper"
        else:
            step = "results_review"

    # ── Profile-aware personalization ──
    if profile is not None:
        try:
            plan = None
            from core.personalization_engine import PersonalizationEngine
            engine = PersonalizationEngine(profile)
            plan = engine.build_plan()

            if step in ("home",):
                return plan.bunny_message
            if step.startswith("results"):
                task_type = context.get("task_type", "")
                gen_types = []
                if task_type == "exam_sprint":
                    gen_types = ["Sprint"]
                elif task_type == "past_paper":
                    gen_types = ["PastPaper"]
                elif task_type == "mock_exam":
                    gen_types = ["MockExam"]
                else:
                    gen_types = ["Review"]
                return engine._bunny_for_results(gen_types)
        except Exception:
            pass  # fall through to generic tips

    # ── Special: home with profile ──
    if step == "home" and profile is not None:
        try:
            if profile.course_name or profile.weak_points:
                tips = BUNNY_TIPS.get("home_with_profile", BUNNY_TIPS["home"])
                return random.choice(tips)
        except Exception:
            pass

    # ── Generic fallback ──
    tips = BUNNY_TIPS.get(step, BUNNY_TIPS["home"])
    return random.choice(tips)


def get_bunny_emoji(mood: str = "neutral") -> str:
    return BUNNY_MOODS.get(mood, BUNNY_MOODS["neutral"])


def render_bunny_bubble(message: str, mood: str = "neutral") -> str:
    """Return an HTML string for a bunny speech bubble."""
    emoji = get_bunny_emoji(mood)
    return (
        f'<div class="bunny-bubble">'
        f"{emoji}  {message}"
        f"</div>"
    )


def render_bunny_card(message: str, mood: str = "neutral") -> str:
    """Return an HTML string for a fixed bunny recommendation card.

    Use for sidebar or result page — non-intrusive, cream background,
    green accent.
    """
    emoji = get_bunny_emoji(mood)
    return (
        f'<div style="background:#fefaf3;border:1px solid #d6c89c;'
        f'border-radius:12px;padding:16px;margin:12px 0;font-size:14px;'
        f'line-height:1.6;color:#4a4035;">'
        f'<div style="font-size:20px;margin-bottom:6px;">{emoji}</div>'
        f'{message}'
        f'</div>'
    )
