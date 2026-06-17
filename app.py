"""StudyPilot AI v1.2 — AI Study Coach with Wizard Flow.

Session-state-driven wizard: Home → Goal → Upload → Recognition →
Preferences → Progress → Results → Next Steps.
"""

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

from core.config import ensure_json_files, DATA_DIR
from core.content_utils import format_sources_for_display, get_quality_warnings
from core.course_manager import create_course, get_course, load_courses, update_course
from core.deepseek_client import DeepSeekConfigError
from core.export_utils import list_outputs, markdown_to_pdf, save_markdown
from core.i18n import CANONICAL, LANG
from core.learning_planner import get_profile, save_profile
from core.metadata_manager import add_resource_metadata, delete_resource_metadata, resources_for_course
from core.pdf_loader import load_pdf_pages
from core.resource_analyzer import analyze_pdf
from core.task_manager import (
    create_task,
    delete_task,
    get_all_tasks,
    get_task,
    run_task_in_background,
)
from core.text_splitter import split_text_pages
from core.vector_store import rebuild_course_store, remove_resource_chunks
from core.textbook_asset_extractor import extract_textbook_assets
from core.theme import inject_theme
from core.goal_parser import parse_goal_input
from core.assistant_state import get_bunny_message, get_bunny_emoji, render_bunny_bubble, render_bunny_card
from core.course_classifier import CourseClassifier
from core.user_profile import load_profile, save_profile, update_profile_from_goal_text, export_profile_summary
from core.personalization_engine import PersonalizationEngine, build_learning_path_nodes
from core.output_manager import (
    generate_demo_manifest,
    create_run,
    finalize_run,
    list_runs,
    get_run,
    delete_run,
    mark_final,
    get_storage_stats,
    cleanup_old_runs,
    cleanup_orphaned_outputs,
    cleanup_non_final,
    cleanup_all,
)

# ── Bootstrap ──────────────────────────────────────────────────────────────

ensure_json_files()
st.set_page_config(
    page_title="StudyPilot AI — 你的 AI 学习教练",
    page_icon="🐰",
    layout="wide",
)
inject_theme()

# ── Constants ──────────────────────────────────────────────────────────────

PAGE_KEYS = ["dashboard", "courses", "profile", "upload", "library", "ai", "outputs"]
NAV_LABEL_KEYS = {
    "dashboard": "nav_dashboard",
    "courses": "nav_courses",
    "profile": "nav_profile",
    "upload": "nav_upload",
    "library": "nav_library",
    "ai": "nav_ai",
    "outputs": "nav_outputs",
}
RESOURCE_TYPE_KEYS = ["resource_textbook", "resource_ppt", "resource_past_exam", "resource_notes", "resource_lab"]
GOAL_KEYS = ["goal_pass", "goal_80", "goal_90", "goal_postgraduate", "goal_custom"]
LEVEL_KEYS = ["level_zero", "level_normal", "level_good"]
PREFERRED_STYLE_KEYS = [
    "style_detailed_explanation", "style_classic_examples", "style_pitfalls",
    "style_exam_notes", "style_formula_derivation", "style_exam_analysis",
    "style_mind_map", "style_teaching_diagrams",
]
PHASE_KEYS = [
    "phase_from_zero", "phase_following_class", "phase_exam_review",
    "phase_postgraduate", "phase_gap_filling",
]
TASK_OPTIONS = {
    "single_chapter": "task_single_chapter",
    "chapter_review": "task_chapter_review",
    "exam_sprint": "task_exam_sprint",
    "hotspots": "task_hotspots",
    "mock_exam": "task_mock_exam",
    "past_paper": "task_past_paper",
    "learning_plan": "task_learning_plan",
    "qa": "task_qa",
    "custom": "task_custom",
}

CARD_TO_TASK_TYPE = {
    "systematic_study": "single_chapter",
    "exam_sprint": "exam_sprint",
    "mock_exam": "mock_exam",
    "past_paper": "past_paper",
}

TASK_CARDS = [
    {
        "key": "systematic_study",
        "icon": "📖",
        "label_key": "card_systematic_study",
        "desc_key": "card_systematic_study_desc",
        "output": "Review",
    },
    {
        "key": "exam_sprint",
        "icon": "⚡",
        "label_key": "card_exam_sprint",
        "desc_key": "card_exam_sprint_desc",
        "output": "Sprint",
    },
    {
        "key": "mock_exam",
        "icon": "📝",
        "label_key": "card_mock_exam",
        "desc_key": "card_mock_exam_desc",
        "output": "MockExam",
    },
    {
        "key": "past_paper",
        "icon": "🎯",
        "label_key": "card_past_paper",
        "desc_key": "card_past_paper_desc",
        "output": "PastPaper",
    },
]

DETAIL_LEVELS = ["prefs_detail_compact", "prefs_detail_standard", "prefs_detail_comprehensive"]
ILLUSTRATION_OPTIONS = ["prefs_illustration_rich", "prefs_illustration_balanced", "prefs_illustration_off"]
OUTPUT_STYLES = ["GoodNotes 友好", "打印友好", "屏幕阅读友好"]

PROGRESS_PHASES = [
    ("progress_phase_1", 5),
    ("progress_phase_2", 15),
    ("progress_phase_3", 25),
    ("progress_phase_4", 40),
    ("progress_phase_5", 55),
    ("progress_phase_6", 70),
    ("progress_phase_7", 85),
    ("progress_phase_8", 95),
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_lang() -> str:
    return st.session_state.get("lang", "zh")


def tr(key: str, **kwargs: object) -> str:
    text = LANG[get_lang()].get(key, LANG["zh"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def canonical(key: str) -> str:
    return CANONICAL.get(key, key)


def current_course() -> dict | None:
    return get_course(st.session_state.get("course_id"))


def select_course_widget() -> dict | None:
    courses = load_courses()
    if not courses:
        return None
    labels = {
        f"{c['course_name']} · {c.get('university', '')} · {c['course_id']}": c["course_id"]
        for c in courses
    }
    selected_label = st.sidebar.selectbox(
        tr("current_course"), list(labels.keys()), index=0
    )
    st.session_state["course_id"] = labels[selected_label]
    return current_course()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_session_value(key: str, value: object) -> None:
    """Set a session_state key *only* if it hasn't been initialised yet.

    Safe to call before widget creation — avoids the Streamlit error
    ``cannot be modified after the widget with key … is instantiated``.
    """
    if key not in st.session_state:
        st.session_state[key] = value


def _sync_active_course_to_course_id() -> None:
    """Ensure course_id matches active_course to prevent sidebar mismatch."""
    active_course = st.session_state.get("active_course")
    if not active_course:
        return
    courses = load_courses()
    # Try to find matching course by name
    for c in courses:
        if c.get("course_name", "").strip() == active_course.strip():
            st.session_state["course_id"] = c["course_id"]
            return
    # If no match found, create a new course entry
    university = st.session_state.get("active_subject_label") or ""
    new_course = create_course(university, active_course)
    st.session_state["course_id"] = new_course["course_id"]


# ── Session Initialisation ─────────────────────────────────────────────────

def init_session() -> None:
    defaults: dict[str, object] = {
        "lang": "zh",
        "course_id": "",
        "watching_task_id": None,
        "delete_confirming": None,
        # Wizard state
        "current_step": "home",
        "agent_input": "",
        "parsed_goal": {},
        "selected_task_type": None,
        "goal": "80+",
        "level": "一般",
        "weak_points": [],
        "weak_points_raw": "",
        "detected_materials": [],
        "prefs_detail_level": "prefs_detail_standard",
        "prefs_illustration": "prefs_illustration_balanced",
        "prefs_output_style": "GoodNotes 友好",
        "prefs_exam_mode": False,
        "prefs_request": "",
        "debug_mode": False,
        "current_run_id": None,
        "bunny_mood": "neutral",
        # ── Unified course state (v1.3 fix) ──
        "active_course": None,          # 唯一课程状态源
        "active_chapter": None,         # 当前识别章节
        "active_subject": None,         # 当前学科类型
        "active_subject_label": None,   # 学科中文标签
        "recognition_source": {},       # 识别来源信息 {course_source, chapter_source, subject_source}
        "uploaded_file_hashes": [],     # 已上传文件哈希列表（用于检测新文件）
        "uploaded_file_names": [],      # 已上传文件名列表
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def navigate_to(step: str) -> None:
    st.session_state.current_step = step
    moods = {
        "home": "neutral",
        "goal": "thinking",
        "upload": "neutral",
        "ai_recognition": "thinking",
        "preferences": "happy",
        "progress": "working",
        "results": "excited",
        "next_steps": "encourage",
    }
    st.session_state.bunny_mood = moods.get(step, "neutral")


# ── Sidebar ─────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    st.sidebar.title("🐰 StudyPilot AI")

    # Language
    st.sidebar.selectbox(
        tr("language_label"), ["zh", "en"],
        index=0 if get_lang() == "zh" else 1,
        format_func=lambda v: LANG[v][f"language_{v}"],
        key="lang",
    )

    # Course selector
    course = select_course_widget()
    st.sidebar.markdown("---")

    # Project status
    st.sidebar.caption(f"📊 {tr('sidebar_status')}")
    courses = load_courses()
    stats = get_storage_stats()

    col1, col2, col3 = st.sidebar.columns(3)
    col1.metric(tr("course_count"), len(courses))
    col2.metric(tr("resource_count"), len(resources_for_course(st.session_state.get("course_id", ""))) if st.session_state.get("course_id") else 0)
    col3.metric(tr("output_count"), stats["total_runs"])

    # Storage
    if stats["total_mb"] > 0:
        st.sidebar.caption(
            f"💾 {tr('storage_stats')}：{stats['total_mb']} MB · "
            f"{stats['total_runs']} {tr('storage_runs')}"
        )

    # Recent generations
    st.sidebar.markdown("---")
    st.sidebar.caption(f"🕐 {tr('sidebar_recent')}")
    recent = list_runs(limit=3)
    if recent:
        for r in recent:
            status_icon = {"completed": "✅", "warning": "⚠️", "running": "🔄", "failed": "❌"}.get(
                r.get("status", ""), "📄"
            )
            final_badge = " ⭐" if r.get("is_final") else ""
            st.sidebar.caption(
                f"{status_icon} {r.get('task_type', '?')}{final_badge} · "
                f"{r.get('created_at', '')[:16]}"
            )
    else:
        st.sidebar.caption(tr("history_empty"))

    # Cleanup
    st.sidebar.markdown("---")
    with st.sidebar.expander(f"🧹 {tr('sidebar_cleanup')}", expanded=False):
        st.caption(f"{tr('storage_stats')}：{stats['total_mb']} MB")
        if st.button(tr("sidebar_cleanup_orphaned"), use_container_width=True):
            result = cleanup_orphaned_outputs()
            st.success(f"✅ {result['files_removed']} files, {result['bytes_freed'] / 1024:.0f} KB freed")
            time.sleep(0.5)
            st.rerun()
        if st.button(tr("sidebar_cleanup_old"), use_container_width=True):
            result = cleanup_old_runs(keep_last=5)
            st.success(f"✅ {result['runs_removed']} runs removed, {result['bytes_freed'] / 1024:.0f} KB freed")
            time.sleep(0.5)
            st.rerun()
        if st.button(tr("sidebar_cleanup_non_final"), use_container_width=True):
            result = cleanup_non_final()
            st.success(f"✅ {result['runs_removed']} runs removed, {result['bytes_freed'] / 1024:.0f} KB freed")
            time.sleep(0.5)
            st.rerun()
        if st.button("⚠️ " + tr("sidebar_cleanup_all"), use_container_width=True):
            st.session_state.cleanup_confirm = True
        if st.session_state.get("cleanup_confirm"):
            st.warning(tr("sidebar_cleanup_all_confirm"))
            c1, c2 = st.columns(2)
            if c1.button("✓ 确认", use_container_width=True):
                result = cleanup_all()
                st.success(f"✅ {result['runs_removed']} runs removed")
                st.session_state.cleanup_confirm = False
                time.sleep(0.5)
                st.rerun()
            if c2.button("✗ 取消", use_container_width=True):
                st.session_state.cleanup_confirm = False
                st.rerun()

    # Settings
    st.sidebar.markdown("---")
    with st.sidebar.expander(f"⚙️ {tr('sidebar_settings')}", expanded=False):
        st.toggle(
            f"🔧 {tr('sidebar_debug')}",
            value=st.session_state.get("debug_mode", False),
            key="debug_mode",
            help=tr("sidebar_debug_desc"),
        )

    # 🐰 Bunny mascot
    _render_sidebar_bunny()


def _render_sidebar_bunny() -> None:
    step = st.session_state.get("current_step", "home")
    mood = st.session_state.get("bunny_mood", "neutral")
    try:
        profile = load_profile()
    except Exception:
        profile = None
    tip = get_bunny_message(step, context={}, profile=profile)
    emoji = get_bunny_emoji(mood)
    st.sidebar.markdown(
        f'<div class="bunny-bubble" style="margin-top:1rem;">{emoji} {tip}</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Wizard Pages
# ═══════════════════════════════════════════════════════════════════════════

# ── HOME ───────────────────────────────────────────────────────────────────

def page_home() -> None:
    # Hero
    st.markdown(
        '<div class="hero-banner">'
        f'<h1>🐰 <span class="brand-accent">StudyPilot AI</span></h1>'
        f'<p class="subtitle" style="font-size:1.15rem;">你的 AI 学习教练</p>'
        f'<p class="subtitle" style="font-size:0.9rem;margin-top:0.3rem;color:#888;">'
        f'上传教材、PPT 和真题，让 AI 帮你规划复习、生成讲义、模拟卷和高频题精讲。</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Today's Status Card ──
    profile = load_profile()
    engine = PersonalizationEngine(profile)
    today = engine.build_today_card()

    # ── Override with active_course (unified state source) ──
    active_course = st.session_state.get("active_course")
    active_chapter = st.session_state.get("active_chapter")
    if active_course:
        today["course"] = active_course
        today["has_profile"] = True
    if active_chapter:
        today["chapter"] = active_chapter

    st.markdown("---")
    if today["has_profile"]:
        st.markdown("#### 📊 今天的学习状态")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("课程", today["course"])
            st.metric("目标", today["target_score"])
        with col_s2:
            st.metric("章节", today["chapter"])
            st.metric("剩余时间", today["remaining_time"])
        with col_s3:
            st.metric("场景", today["scenario_label"])
            if today.get("weak_points") and today["weak_points"] != ["未设置"]:
                st.caption(f"薄弱点：{'、'.join(today['weak_points'][:3])}")

        st.info(f"💡 推荐动作：**{today['recommended_action']}**")
    else:
        st.info("💡 先告诉 StudyPilot：你要考什么、剩多少时间、哪里不会。")

    # ── Agent input with AI understanding ──
    st.markdown("<br>", unsafe_allow_html=True)
    agent_input = st.text_area(
        "🎯 告诉我你的学习目标",
        value=st.session_state.get("agent_input", ""),
        placeholder="例如：明天考电磁场，我只有3小时，高斯定理和镜像法不稳，帮我安排复习。",
        height=85,
        key="agent_input",
        label_visibility="visible",
    )

    col_a, col_b, col_c = st.columns([2, 1, 2])
    with col_b:
        if st.button("🚀 开始规划", type="primary", use_container_width=True):
            if st.session_state.agent_input.strip():
                # Parse goal & update profile
                st.session_state.parsed_goal = parse_goal_input(st.session_state.agent_input)
                update_profile_from_goal_text(st.session_state.agent_input)
            navigate_to("goal")
            st.rerun()

    # Show AI understanding if parsed
    parsed = st.session_state.get("parsed_goal", {})
    if parsed and parsed.get("raw_input"):
        with st.container(border=True):
            st.markdown("**🤖 AI 识别结果：**")
            time_str = parsed.get("remaining_time") or "未识别"
            score_str = parsed.get("target_score") or "未识别"
            course_str = parsed.get("course") or "未识别"
            chapter_str = parsed.get("chapter") or "未识别"
            mode_str = {
                "systematic_study": "📖 系统学习",
                "exam_sprint": "⚡ 考前冲刺",
                "mock_exam": "📝 模拟考试",
                "past_paper": "🎯 高频题精讲",
            }.get(parsed.get("mode", ""), parsed.get("mode") or "未识别")
            wp_str = "、".join(parsed.get("weak_points", [])) or "未识别"

            st.caption(f"📚 课程：{course_str} | 章节：{chapter_str}")
            st.caption(f"⏱ 剩余时间：{time_str} | 🎯 目标：{score_str}")
            st.caption(f"💪 薄弱点：{wp_str}")
            st.caption(f"🎯 推荐模式：{mode_str}")

    # 🐰 Bunny tip
    st.markdown(
        render_bunny_card(
            get_bunny_message("home", context={}, profile=profile),
            st.session_state.get("bunny_mood", "neutral"),
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Learning Path ──
    render_learning_path(profile)

    # Task cards
    st.markdown("#### 或者，直接选择学习模式：")
    cols = st.columns(4)
    for i, card in enumerate(TASK_CARDS):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"### {card['icon']}")
                st.markdown(f"**{tr(card['label_key'])}**")
                st.caption(tr(card['desc_key']))
                st.caption(f"📤 {tr('card_output')}：{card['output']}")
                if st.button(tr("home_start_planning"), key=f"card_{card['key']}", use_container_width=True):
                    st.session_state.selected_task_type = card["key"]
                    navigate_to("goal")
                    st.rerun()

    # Footer encouragement
    st.markdown(
        f'<div class="footer-encourage">🐰 {tr("home_encourage")}</div>',
        unsafe_allow_html=True,
    )


def render_learning_path(profile=None) -> None:
    """Render the learning path component with weak-point highlighting."""
    nodes = build_learning_path_nodes(profile)

    with st.expander("🗺️ 学习路径图", expanded=False):
        if not nodes:
            st.caption("当前课程路径正在生成，先使用通用复习路径。")
            return

        cols = st.columns(len(nodes))
        for i, node in enumerate(nodes):
            with cols[i]:
                bg = "#fff3e0" if node["is_weak"] else "#f5f7f0"
                border = "#e6a23c" if node["is_weak"] else "#c8d6b0"
                weak_html = '<div style="color:#d32f2f;font-size:11px;margin-top:4px;">⚠️ 优先复习</div>' if node["is_weak"] else ""
                st.markdown(
                    f'<div style="background:{bg};border:2px solid {border};'
                    f'border-radius:10px;padding:12px;text-align:center;min-height:110px;">'
                    f'<div style="font-size:13px;font-weight:600;">{node["name"]}</div>'
                    f'{weak_html}'
                    f'<div style="font-size:10px;color:#999;margin-top:4px;">'
                    f'{", ".join(node["recommended_pdfs"][:2])}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            if i < len(nodes) - 1:
                with cols[i]:
                    st.markdown(
                        '<div style="text-align:center;color:#aaa;font-size:18px;margin-top:-8px;">↓</div>',
                        unsafe_allow_html=True,
                    )


# ── GOAL ───────────────────────────────────────────────────────────────────

def page_goal() -> None:
    st.title(tr("goal_title"))
    st.caption(tr("goal_subtitle"))

    parsed = st.session_state.get("parsed_goal", {})

    # Show parsed results
    if parsed and parsed.get("raw_input"):
        with st.container(border=True):
            st.markdown(f"💬 *\"{parsed['raw_input']}\"*")
            st.caption(f"⏱ {tr('goal_remaining_time')}：{parsed.get('remaining_time') or '未识别'}")
            st.caption(f"🎯 {tr('goal_target_score')}：{parsed.get('target_score') or '未识别'}")
            st.caption(f"📚 {tr('goal_course')}：{parsed.get('course') or '未识别'}")
            st.caption(f"📖 {tr('goal_chapter')}：{parsed.get('chapter') or '未识别'}")
            if parsed.get("weak_points"):
                st.caption(f"💪 {tr('goal_weak_points')}：{'、'.join(parsed['weak_points'])}")
            if parsed.get("mode"):
                mode_labels = {
                    "systematic_study": "📖 系统学习",
                    "exam_sprint": "⚡ 考前冲刺",
                    "mock_exam": "📝 模拟考试",
                    "past_paper": "🎯 高频题精讲",
                }
                st.caption(f"🎯 {tr('goal_recommended_mode')}：{mode_labels.get(parsed['mode'], parsed['mode'])}")
    else:
        st.info("你也可以直接选择下方的目标设置。")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        goal_display = [
            tr("goal_pass"), tr("goal_80"), tr("goal_85_plus"), tr("goal_90"), tr("goal_custom"),
        ]
        goal_values = ["及格", "75+", "85+", "90+", "自定义"]
        current_idx = 1
        for i, g in enumerate(goal_values):
            if g == st.session_state.get("goal", "80+"):
                current_idx = i
                break
        selected_goal = st.selectbox(
            tr("goal_select_score"), goal_values, index=min(current_idx, len(goal_values) - 1),
            key="goal",
        )
    with col2:
        level_display = [tr("level_zero"), tr("level_normal"), tr("level_good")]
        level_values = ["零基础", "一般", "较好"]
        current_level = st.session_state.get("level", "一般")
        current_level_idx = level_values.index(current_level) if current_level in level_values else 1
        st.selectbox(
            tr("goal_select_level"), level_values, index=current_level_idx,
            key="level",
        )

    # Weak points manual entry — safe init before widget
    init_session_value("weak_points_raw", "、".join(st.session_state.get("weak_points", [])))
    weak_str = st.text_input(
        "💪 " + tr("goal_weak_points") + "（可选，用逗号分隔）",
        key="weak_points_raw",
        label_visibility="visible",
    )

    # 🐰
    st.markdown(
        render_bunny_bubble(get_bunny_message("goal"), st.session_state.get("bunny_mood", "neutral")),
        unsafe_allow_html=True,
    )

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button(tr("wizard_back")):
            navigate_to("home")
            st.rerun()
    with col_next:
        if st.button(tr("goal_confirm"), type="primary"):
            # Parse weak_points from the text input on confirm (not on every rerun)
            raw = st.session_state.get("weak_points_raw", "")
            st.session_state.weak_points = [w.strip() for w in raw.replace("，", ",").split(",") if w.strip()]
            # If parsed_goal has mode, set selected_task_type
            if parsed.get("mode") and not st.session_state.get("selected_task_type"):
                st.session_state.selected_task_type = parsed["mode"]
            if not st.session_state.get("selected_task_type"):
                st.session_state.selected_task_type = "systematic_study"

            # ── Persist to UserProfile ──
            try:
                profile = load_profile()
                profile.target_score = st.session_state.get("goal", "85+")
                profile.weak_points = st.session_state.weak_points
                if parsed.get("course"):
                    profile.course_name = parsed["course"]
                    st.session_state.active_course = parsed["course"]
                if parsed.get("chapter"):
                    profile.chapter_name = parsed["chapter"]
                    st.session_state.active_chapter = parsed["chapter"]
                if st.session_state.get("prefs_output_style"):
                    profile.preferred_pdf_style = st.session_state.prefs_output_style
                save_profile(profile)
            except Exception:
                pass

            # Sync active_course → course_id
            _sync_active_course_to_course_id()

            navigate_to("upload")
            st.rerun()


# ── UPLOAD ─────────────────────────────────────────────────────────────────

def page_upload_wizard() -> None:
    st.title(tr("step_upload"))
    st.caption("上传你的学习资料，让 AI 更准确地帮你复习。")

    course = current_course()
    if not course:
        st.info(tr("select_course_first"))
        # Quick create
        with st.expander("📚 创建课程", expanded=True):
            uni = st.text_input(tr("university"), value=tr("default_university"))
            cname = st.text_input(tr("course_name"))
            if st.button(tr("create_course")) and cname.strip():
                course = create_course(uni, cname)
                st.session_state["course_id"] = course["course_id"]
                st.success(tr("course_created"))
                st.rerun()
        col_back, _ = st.columns([1, 3])
        with col_back:
            if st.button(tr("wizard_back")):
                navigate_to("goal")
                st.rerun()
        return

    course_id = course["course_id"]
    tabs = st.tabs([
        f"📗 {tr('upload_zone_textbook')}",
        f"📊 {tr('upload_zone_ppt')}",
        f"📝 {tr('upload_zone_exam')}",
        f"📒 {tr('upload_zone_notes')}",
    ])

    zone_configs = [
        {"key": "textbook", "desc": tr("upload_zone_textbook_desc"), "types": ["pdf"]},
        {"key": "ppt", "desc": tr("upload_zone_ppt_desc"), "types": ["pdf", "pptx"]},
        {"key": "exam", "desc": tr("upload_zone_exam_desc"), "types": ["pdf", "png", "jpg", "jpeg"]},
        {"key": "notes", "desc": tr("upload_zone_notes_desc"), "types": ["pdf"]},
    ]

    uploaded_any = False
    for tab, zc in zip(tabs, zone_configs):
        with tab:
            st.caption(zc["desc"])
            uploaded_files = st.file_uploader(
                f"选择文件", type=zc["types"],
                accept_multiple_files=True,
                key=f"upload_{zc['key']}",
                label_visibility="collapsed",
            )
            if uploaded_files:
                uploaded_any = True
                for uf in uploaded_files:
                    # Simple card
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"📄 {uf.name}")
                        c1.caption(f"{uf.size / 1024:.0f} KB")
                        c2.caption(tr("upload_status_pending"))

    if uploaded_any:
        # ── Collect all uploaded filenames for recognition reset ──
        all_uploaded_names: list[str] = []
        for zc in zone_configs:
            uf_list = st.session_state.get(f"upload_{zc['key']}", [])
            for uf in uf_list:
                all_uploaded_names.append(uf.name)

        if st.button("📤 解析并上传全部资料", type="primary"):
            # ── Compute file hashes & reset recognition cache on new files ──
            new_hashes: list[str] = []
            for zc in zone_configs:
                uf_list = st.session_state.get(f"upload_{zc['key']}", [])
                for uf in uf_list:
                    file_hash = hashlib.md5(uf.getbuffer()).hexdigest()
                    new_hashes.append(file_hash)

            prev_hashes = set(st.session_state.get("uploaded_file_hashes", []))
            if set(new_hashes) != prev_hashes:
                # New files detected — clear all recognition cache
                st.session_state.active_course = None
                st.session_state.active_chapter = None
                st.session_state.active_subject = None
                st.session_state.active_subject_label = None
                st.session_state.recognition_source = {}
                st.session_state.uploaded_file_hashes = new_hashes
                st.session_state.uploaded_file_names = all_uploaded_names
                # Also reset legacy recog keys
                for legacy_key in ("recog_course", "recog_chapter", "recog_subject"):
                    if legacy_key in st.session_state:
                        del st.session_state[legacy_key]

            with st.status(tr("upload_processing"), expanded=True) as status:
                course_dir = Path("data") / "uploads" / course_id
                course_dir.mkdir(parents=True, exist_ok=True)

                chunk_path = Path("data") / "vector_store" / course_id / "chunks.json"
                all_chunks = (
                    json.loads(chunk_path.read_text(encoding="utf-8"))
                    if chunk_path.exists()
                    else []
                )
                success_count = 0
                for zc in zone_configs:
                    uf_list = st.session_state.get(f"upload_{zc['key']}", [])
                    for uf in uf_list:
                        st.write(f"📄 {uf.name}...")
                        file_path = course_dir / uf.name
                        try:
                            with file_path.open("wb") as f:
                                f.write(uf.getbuffer())
                            analysis = analyze_pdf(file_path, uf.name)
                            if analysis["quality_status"] != "failed":
                                try:
                                    extract_textbook_assets(str(file_path), course_id)
                                except Exception:
                                    pass
                            if analysis["quality_status"] == "failed":
                                st.warning(f"⚠️ {uf.name}：{analysis.get('quality_message', '')}")
                                continue
                            pages = load_pdf_pages(file_path)
                            chunks = split_text_pages(pages)
                            if len(chunks) == 0:
                                st.warning(f"⚠️ {uf.name}：可能是扫描版 PDF，暂无文字")
                                continue
                            add_resource_metadata(
                                course, "", "", "教材", "", "", uf.name, str(file_path),
                                analysis=analysis, status="completed",
                            )
                            all_chunks.extend(chunks)
                            success_count += 1
                        except Exception as exc:
                            st.error(f"❌ {uf.name}：{exc}")
                if all_chunks:
                    try:
                        backend = rebuild_course_store(course_id, all_chunks)
                        st.write(f"✅ 索引完成（{backend.upper()}）")
                    except Exception as exc:
                        st.error(f"❌ 索引失败：{exc}")
                status.update(label=f"✅ 完成 — {success_count} 个文件已处理", state="complete")
            st.success("上传完成！")
            time.sleep(1)
            st.rerun()

    # 🐰
    st.markdown(
        render_bunny_bubble(get_bunny_message("upload"), st.session_state.get("bunny_mood", "neutral")),
        unsafe_allow_html=True,
    )

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button(tr("wizard_back"), key="upload_back"):
            navigate_to("goal")
            st.rerun()
    with col_next:
        if st.button(tr("wizard_continue"), type="primary", key="upload_next"):
            navigate_to("ai_recognition")
            st.rerun()


# ── AI RECOGNITION ─────────────────────────────────────────────────────────

def page_ai_recognition() -> None:
    st.title(tr("recognition_title"))
    st.caption(tr("recognition_subtitle"))

    course = current_course() or {}
    parsed = st.session_state.get("parsed_goal", {})

    # ── Classify from uploaded files ──
    classifier = CourseClassifier()
    uploaded_names = st.session_state.get("uploaded_file_names", [])
    rec_result = classifier.classify_full(uploaded_names) if uploaded_names else {}

    # ── Determine course: classifier → active_course → parsed → course → fallback ──
    detected_course = (
        rec_result.get("course")
        or st.session_state.get("active_course")
        or parsed.get("course")
        or course.get("course_name")
        or None
    )
    course_confidence = rec_result.get("course_confidence", 0.0)
    course_source = rec_result.get("course_source", "")
    course_keywords = rec_result.get("course_matched_keywords", [])

    # ── Determine chapter: classifier ONLY, no history fallback ──
    chapter_result = classifier.detect_chapter(uploaded_names, course_name=detected_course) if uploaded_names else {}
    detected_chapter = chapter_result.get("chapter_name")
    chapter_confidence = chapter_result.get("confidence", 0.0)
    chapter_source = chapter_result.get("source", "")

    # ── Determine subject: classifier ONLY ──
    detected_subject_type = rec_result.get("subject_type")
    detected_subject_label = rec_result.get("subject_label")
    subject_confidence = rec_result.get("subject_confidence", 0.0)
    subject_source = rec_result.get("subject_source", "")

    # ── Persist to unified state ──
    if detected_course:
        st.session_state.active_course = detected_course
    if detected_chapter and chapter_confidence >= 0.7:
        st.session_state.active_chapter = detected_chapter
    else:
        st.session_state.active_chapter = None
    if detected_subject_type:
        st.session_state.active_subject = detected_subject_type
        st.session_state.active_subject_label = detected_subject_label
    st.session_state.recognition_source = {
        "course_source": course_source,
        "course_confidence": course_confidence,
        "chapter_source": chapter_source,
        "chapter_confidence": chapter_confidence,
        "subject_source": subject_source,
        "subject_confidence": subject_confidence,
    }

    task_key = st.session_state.get("selected_task_type", "systematic_study")
    task_labels_map = {
        "systematic_study": "Review / 章节复习",
        "exam_sprint": "Sprint / 考前冲刺",
        "mock_exam": "MockExam / 模拟试卷",
        "past_paper": "PastPaper / 真题精讲",
    }

    # ── Chapter display logic ──
    if chapter_confidence >= 0.7 and detected_chapter:
        chapter_display = detected_chapter
        chapter_display_source = f"（来源：{chapter_source} {chapter_confidence:.2f}）"
    else:
        chapter_display = "未识别"
        chapter_display_source = "（无高置信匹配）"

    # ── Course display logic ──
    if detected_course and course_confidence > 0:
        course_display = detected_course
        course_display_source = f"（来源：{course_source} {course_confidence:.2f}）"
    elif detected_course:
        course_display = detected_course
        course_display_source = "（手动设置）"
    else:
        course_display = "未识别"
        course_display_source = "（无匹配）"

    # ── Subject display logic ──
    if detected_subject_label and subject_confidence > 0:
        subject_display = detected_subject_label
        subject_display_source = f"（来源：{subject_source} {subject_confidence:.2f}）"
    elif detected_subject_label:
        subject_display = detected_subject_label
        subject_display_source = "（默认）"
    else:
        subject_display = "未识别"
        subject_display_source = "（无匹配）"

    # ── Build subject options including detected value ──
    subject_options = ["工程类", "理科类", "数学类", "文科类", "医学类"]
    if detected_subject_label and detected_subject_label not in subject_options:
        subject_options.insert(0, detected_subject_label)
    subject_default = detected_subject_label if detected_subject_label in subject_options else "工程类"

    # Safe init widgets
    init_session_value("recog_course", course_display)
    init_session_value("recog_chapter", chapter_display)
    init_session_value("recog_subject", subject_default)

    with st.container(border=True):
        st.markdown(f"**📚 {tr('recognition_course')}**")
        st.caption(course_display_source)
        st.text_input(
            tr("recognition_course"), label_visibility="collapsed", key="recog_course",
        )

        st.markdown(f"**📖 {tr('recognition_chapter')}**")
        st.caption(chapter_display_source)
        st.text_input(
            tr("recognition_chapter"), label_visibility="collapsed", key="recog_chapter",
        )

        st.markdown(f"**🔬 {tr('recognition_subject')}**")
        st.caption(subject_display_source)
        st.selectbox(
            tr("recognition_subject"),
            subject_options,
            label_visibility="collapsed", key="recog_subject",
        )

        st.markdown(f"**📤 {tr('recognition_recommended')}**")
        st.info(task_labels_map.get(task_key, "Review"))

        # ── Match quality warning ──
        if not detected_course or course_confidence < 0.5:
            st.markdown(f"**⚠️ {tr('recognition_risk')}**")
            st.warning("课程识别置信度较低，建议手动确认课程名称。")
        elif chapter_confidence < 0.7:
            st.markdown(f"**⚠️ {tr('recognition_risk')}**")
            st.warning("章节未能高置信度识别，已显示「未识别」，可手动填写。")
        else:
            st.markdown(f"**✅ 识别状态**")
            st.success(
                f"课程匹配关键词：{'、'.join(course_keywords[:5]) if course_keywords else '—'} ｜ "
                f"置信度：{course_confidence:.2f}"
            )

    # 🐰
    st.markdown(
        render_bunny_bubble(get_bunny_message("ai_recognition"), st.session_state.get("bunny_mood", "neutral")),
        unsafe_allow_html=True,
    )

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button(tr("wizard_back"), key="recog_back"):
            navigate_to("upload")
            st.rerun()
    with col_next:
        if st.button(tr("wizard_continue"), type="primary", key="recog_next"):
            # Sync widget values back to unified state
            st.session_state.active_course = st.session_state.get("recog_course")
            st.session_state.active_chapter = st.session_state.get("recog_chapter")
            st.session_state.active_subject_label = st.session_state.get("recog_subject")
            # Sync active_subject type from label (prevent desync)
            label = st.session_state.get("recog_subject", "")
            label_to_type = {
                "数学类": "math", "理科类": "math",
                "理工工程类": "engineering", "工程类": "engineering",
                "文科类": "humanities", "人文社科类": "humanities",
                "医学类": "language", "语言类": "language",
            }
            st.session_state.active_subject = label_to_type.get(label, "engineering")
            # Sync active_course → profile.course_name (prevent stale profile)
            try:
                profile = load_profile()
                if st.session_state.active_course:
                    profile.course_name = st.session_state.active_course
                if st.session_state.active_chapter:
                    profile.chapter_name = st.session_state.active_chapter
                save_profile(profile)
            except Exception:
                pass
            # Sync active_course → course_id (prevent sidebar mismatch)
            _sync_active_course_to_course_id()
            navigate_to("preferences")
            st.rerun()


# ── PREFERENCES ────────────────────────────────────────────────────────────

def page_preferences() -> None:
    st.title(tr("prefs_title"))
    st.caption(tr("prefs_subtitle"))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**📝 {tr('prefs_detail_level')}**")
        detail_options = [tr(d) for d in DETAIL_LEVELS]
        detail_values = ["精简", "标准", "详细"]
        detail_idx = detail_values.index("标准") if "标准" in detail_values else 1
        st.selectbox(
            tr("prefs_detail_level"), detail_values, index=detail_idx,
            key="prefs_detail_level", label_visibility="collapsed",
        )

        st.markdown(f"**🎨 {tr('prefs_illustration')}**")
        ill_options = [tr(i) for i in ILLUSTRATION_OPTIONS]
        ill_values = ["尽量多插图", "只在必要题目插图", "暂不插图"]
        ill_idx = 1
        st.selectbox(
            tr("prefs_illustration"), ill_values, index=ill_idx,
            key="prefs_illustration", label_visibility="collapsed",
        )

    with col2:
        st.markdown(f"**📤 {tr('prefs_output_style')}**")
        style_idx = OUTPUT_STYLES.index(st.session_state.get("prefs_output_style", "GoodNotes 友好")) if st.session_state.get("prefs_output_style") in OUTPUT_STYLES else 0
        st.selectbox(
            tr("prefs_output_style"), OUTPUT_STYLES, index=style_idx,
            key="prefs_output_style", label_visibility="collapsed",
        )

        st.markdown(f"**🎯 {tr('prefs_exam_mode')}**")
        st.toggle(
            tr("prefs_exam_mode"),
            value=st.session_state.get("prefs_exam_mode", False),
            key="prefs_exam_mode",
            help="开启后优先匹配历年高频考点",
        )

    st.markdown(f"**💬 {tr('prefs_request_label')}**")
    st.text_area(
        tr('prefs_request_label'),
        value=st.session_state.get("prefs_request", ""),
        key="prefs_request",
        placeholder="例如：请重点讲解高斯定理的对称性分析...",
        label_visibility="collapsed",
    )

    # 🐰
    st.markdown(
        render_bunny_bubble(get_bunny_message("preferences"), st.session_state.get("bunny_mood", "neutral")),
        unsafe_allow_html=True,
    )

    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button(tr("wizard_back"), key="prefs_back"):
            navigate_to("ai_recognition")
            st.rerun()
    with col_next:
        if st.button(tr("wizard_generate"), type="primary", key="prefs_generate"):
            # ── Persist preferences to UserProfile ──
            try:
                profile = load_profile()
                profile.preferred_pdf_style = st.session_state.get("prefs_output_style", "GoodNotes 友好")
                profile.prefers_more_examples = st.session_state.get("prefs_detail_level") in ("prefs_detail_comprehensive",)
                ill_val = st.session_state.get("prefs_illustration", "prefs_illustration_balanced")
                profile.prefers_more_diagrams = ill_val in ("prefs_illustration_rich",)
                profile.prefers_exam_driven = st.session_state.get("prefs_exam_mode", False)
                save_profile(profile)
            except Exception:
                pass

            navigate_to("progress")
            st.rerun()


# ── PROGRESS ───────────────────────────────────────────────────────────────

def page_progress() -> None:
    st.title(tr("progress_title"))

    course = current_course()
    task_key = st.session_state.get("selected_task_type", "systematic_study")
    task_type = CARD_TO_TASK_TYPE.get(task_key, "single_chapter")

    # 🐰
    bunny_tips_cycle = [
        "正在帮你找老师最爱考的点…",
        "正在整理公式，不让 AI 乱写符号…",
        "正在检查有没有空公式和科学垃圾…",
        "正在生成适合打印的讲义…",
        "快了快了，我在努力让你的复习更有底气！",
        "每份资料都是为你定制的，值得等待～",
    ]
    import random
    bunny_tip = random.choice(bunny_tips_cycle)
    st.markdown(
        render_bunny_bubble(bunny_tip, "working"),
        unsafe_allow_html=True,
    )

    # Check if we have a running task
    watching_id = st.session_state.get("watching_task_id")
    task = get_task(watching_id) if watching_id else None

    if not task or task.get("status") == "pending":
        # Start new task
        if course and not watching_id:
            user_request = st.session_state.get("prefs_request", "") or st.session_state.get("agent_input", "")
            run_id = create_run(
                course_id=course.get("course_id", ""),
                task_type=task_type,
                user_request=user_request,
                course_name=st.session_state.get("active_course", course.get("course_name", "")),
                chapter_name=st.session_state.get("active_chapter", ""),
            )
            st.session_state.current_run_id = run_id

            # Build generation prefs
            prefs = {
                "goal": st.session_state.get("goal", "80+"),
                "level": st.session_state.get("level", "一般"),
                "detail": st.session_state.get("prefs_detail_level", "标准"),
                "illustration": st.session_state.get("prefs_illustration", "只在必要题目插图"),
                "output_style": st.session_state.get("prefs_output_style", "GoodNotes 友好"),
                "exam_mode": st.session_state.get("prefs_exam_mode", False),
                "weak_points": st.session_state.get("weak_points", []),
            }

            new_task = create_task(
                course_id=course.get("course_id", ""),
                task_type=task_type,
                user_request=user_request,
                run_id=run_id,
                prefs=prefs,
            )
            run_task_in_background(
                task_id=new_task["task_id"],
                course=course,
                task_type=task_type,
                user_request=user_request,
                top_k=5,
                pdf_style="textbook",
                run_id=run_id,
                prefs=prefs,
            )
            st.session_state.watching_task_id = new_task["task_id"]
            task = new_task

    # Display progress
    if task:
        progress = task.get("progress", 0)
        task_status = task.get("status", "pending")

        # Phase visualization
        for phase_key, phase_pct in PROGRESS_PHASES:
            col_icon, col_label = st.columns([0.5, 9.5])
            if progress >= phase_pct:
                col_icon.markdown("✅")
                status_text = "已完成"
            elif progress >= phase_pct - 15:
                col_icon.markdown("🔄")
                status_text = "进行中"
            else:
                col_icon.markdown("⏳")
                status_text = "等待中"
            col_label.caption(f"{tr(phase_key)} · {status_text}")

        st.progress(progress / 100.0, text=task.get("message", ""))

        # Auto-poll or complete
        if task_status in ("completed", "warning"):
            st.success(f"✅ {task.get('message', '')}")
            st.session_state.bunny_mood = "excited"
            time.sleep(1)
            navigate_to("results")
            st.rerun()
        elif task_status == "failed":
            st.error(f"❌ {task.get('error_message', '生成失败')}")
            if st.button(tr("wizard_back"), key="progress_fail_back"):
                st.session_state.watching_task_id = None
                navigate_to("preferences")
                st.rerun()
        elif task_status == "running":
            time.sleep(1.5)
            st.rerun()

    # Cancel button
    if st.button(tr("progress_cancel"), key="progress_cancel_btn"):
        st.session_state.watching_task_id = None
        navigate_to("preferences")
        st.rerun()


# ── RESULTS ────────────────────────────────────────────────────────────────

def page_results_wizard() -> None:
    st.title(tr("results_title"))

    task_id = st.session_state.get("watching_task_id")
    task = get_task(task_id) if task_id else None

    if not task:
        st.info("没有找到生成结果。")
        if st.button(tr("wizard_home")):
            navigate_to("home")
            st.rerun()
        return

    run_id = task.get("run_id") or st.session_state.get("current_run_id")
    run = get_run(run_id) if run_id else None

    qc = task.get("quality_checks", {})
    score = qc.get("total_score", 0)
    grade = qc.get("grade", "")
    is_teaching = qc.get("is_teaching_grade", False)
    is_complete = qc.get("is_complete", False)

    # Quality badge
    if is_teaching:
        badge_html = f'<span class="quality-badge quality-recommended">{tr("quality_recommended")}</span>'
    elif is_complete:
        badge_html = f'<span class="quality-badge quality-review">{tr("quality_review")}</span>'
    else:
        badge_html = f'<span class="quality-badge quality-draft">{tr("quality_draft")}</span>'

    # PDF card
    pdf_path_str = task.get("result_pdf_path", "")
    md_path_str = task.get("result_markdown_path", "")

    with st.container(border=True):
        st.markdown(f"### 📄 {task.get('task_type', '?')}")
        st.markdown(badge_html, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        # Try to get PDF size
        pdf_size = 0
        if pdf_path_str and Path(pdf_path_str).exists():
            pdf_size = Path(pdf_path_str).stat().st_size
        if run and run.get("files"):
            for f in run["files"]:
                if f["format"] == "pdf":
                    pdf_size = f.get("size_bytes", pdf_size)

        col1.metric(tr("results_pages"), qc.get("total_pages", "?"))
        col2.metric(tr("results_size"), f"{pdf_size / 1024:.0f} KB" if pdf_size else "—")
        col3.metric("Score", f"{score}/100" if score else "—")

        st.caption(f"📊 {tr('results_quality_label')}：{grade}")
        st.caption(f"🕐 {tr('results_generated_at')}：{task.get('finished_at') or _now()}")

        # Scene description
        task_type = task.get("task_type", "")
        scene_map = {
            "single_chapter": "适合系统复习章节内容",
            "exam_sprint": "适合考前 30 分钟快速回顾",
            "mock_exam": "适合自测查漏、模拟考试",
            "past_paper": "适合研究高频考点和出题规律",
        }
        st.caption(f"🎯 {tr('results_scene')}：{scene_map.get(task_type, '学习资料')}")

        # ── Study Advice (personalized) ──
        with st.expander("📋 学习建议 & 覆盖率", expanded=True):
            try:
                profile = load_profile()
                engine = PersonalizationEngine(profile)
                gen_types = []
                if task_type == "exam_sprint":
                    gen_types = ["Sprint"]
                elif task_type == "past_paper":
                    gen_types = ["PastPaper"]
                elif task_type == "mock_exam":
                    gen_types = ["MockExam"]
                else:
                    gen_types = ["Review"]
                advice = engine.build_result_advice(gen_types)

                # Study order
                st.markdown("**建议学习顺序：**")
                for step in advice["study_order"][:3]:
                    st.caption(step)

                # Coverage
                if advice.get("coverage"):
                    st.markdown("**本次资料覆盖：**")
                    st.caption("  ".join(advice["coverage"][:5]))

                # Usage tags
                if advice.get("usage_tags"):
                    st.markdown("**使用场景：**")
                    tag_cols = st.columns(len(advice["usage_tags"]))
                    for i, tag in enumerate(advice["usage_tags"]):
                        with tag_cols[i]:
                            st.caption(f"{tag['icon']} {tag['label']}")

                # Bunny card
                st.markdown(
                    render_bunny_card(advice["bunny_message"], "happy"),
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

        # Buttons
        c1, c2, c3, c4, c5 = st.columns(5)
        if pdf_path_str and Path(pdf_path_str).exists():
            with c1:
                with open(pdf_path_str, "rb") as f:
                    st.download_button(tr("results_download_pdf"), f.read(), file_name=Path(pdf_path_str).name, key="dl_pdf_final")
        if md_path_str and Path(md_path_str).exists():
            with c2:
                st.download_button(tr("results_download_md"), Path(md_path_str).read_bytes(), file_name=Path(md_path_str).name, key="dl_md_final")
        with c3:
            if st.button(tr("results_regenerate"), key="regen_btn"):
                st.session_state.watching_task_id = None
                navigate_to("preferences")
                st.rerun()
        with c4:
            if run_id:
                is_final = run.get("is_final", False) if run else False
                if st.button("⭐" if not is_final else "🌟", help=tr("results_mark_final"), key="mark_final_btn"):
                    mark_final(run_id)
                    st.rerun()
        with c5:
            if st.button(tr("results_delete"), key="delete_result_btn"):
                if run_id:
                    delete_run(run_id)
                delete_task(task_id)
                st.session_state.watching_task_id = None
                navigate_to("home")
                st.rerun()

    # Quality breakdown
    if qc:
        with st.expander("📊 质量详情", expanded=False):
            st.json({k: v for k, v in qc.items() if not isinstance(v, (list, dict)) or len(str(v)) < 200})

    # Figures
    figures = task.get("figures", [])
    if figures:
        st.subheader(tr("results_figures"))
        fig_cols = st.columns(min(len(figures), 4))
        for i, fig in enumerate(figures):
            fig_path = fig.get("path", "")
            if fig_path and Path(fig_path).exists():
                with fig_cols[i % len(fig_cols)]:
                    st.image(str(fig_path), caption=fig.get("title", ""), use_container_width=True)

    # 🐰
    bunny_context = {"task_type": task_type, "quality_score": score}
    st.markdown(
        render_bunny_bubble(get_bunny_message("results", bunny_context), st.session_state.get("bunny_mood", "excited")),
        unsafe_allow_html=True,
    )

    # Next steps
    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button(tr("wizard_start_new"), key="results_start_new"):
            st.session_state.watching_task_id = None
            st.session_state.current_run_id = None
            navigate_to("home")
            st.rerun()
    with col_next:
        if st.button(tr("results_next_steps") + " →", type="primary", key="results_next"):
            navigate_to("next_steps")
            st.rerun()


# ── NEXT STEPS ─────────────────────────────────────────────────────────────

def page_next_steps() -> None:
    st.title(tr("next_title"))

    task_key = st.session_state.get("selected_task_type", "systematic_study")
    task_id = st.session_state.get("watching_task_id")
    task = get_task(task_id) if task_id else None
    score = (task.get("quality_checks", {}) or {}).get("total_score", 0) if task else 0

    # Context-aware suggestions
    suggestions = []
    if task_key == "exam_sprint":
        suggestions.append(("📝", "MockExam", tr("next_suggestion_sprint"), "mock_exam"))
        suggestions.append(("🎯", "PastPaper", tr("next_suggestion_mock"), "past_paper"))
    elif task_key == "mock_exam":
        suggestions.append(("🎯", "PastPaper", tr("next_suggestion_mock"), "past_paper"))
        suggestions.append(("⚡", "Sprint", tr("next_suggestion_review"), "exam_sprint"))
    elif task_key == "past_paper":
        suggestions.append(("📝", "MockExam", tr("next_suggestion_past_paper"), "mock_exam"))
        suggestions.append(("⚡", "Sprint", tr("next_suggestion_review"), "exam_sprint"))
    else:
        suggestions.append(("⚡", "Sprint", tr("next_suggestion_review"), "exam_sprint"))
        suggestions.append(("📝", "MockExam", tr("next_suggestion_mock"), "mock_exam"))

    for icon, label, desc, card_key in suggestions:
        with st.container(border=True):
            c1, c2 = st.columns([0.5, 9.5])
            c1.markdown(f"### {icon}")
            c2.markdown(f"**{label}**")
            c2.caption(desc)
            if c2.button(f"生成 {label}", key=f"next_{card_key}"):
                st.session_state.selected_task_type = card_key
                st.session_state.watching_task_id = None
                navigate_to("preferences")
                st.rerun()

    # 🐰
    st.markdown(
        render_bunny_bubble(get_bunny_message("next_steps"), st.session_state.get("bunny_mood", "encourage")),
        unsafe_allow_html=True,
    )

    if st.button(tr("wizard_home"), key="next_home"):
        st.session_state.watching_task_id = None
        st.session_state.current_run_id = None
        navigate_to("home")
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Legacy Pages (debug mode)
# ═══════════════════════════════════════════════════════════════════════════

def _render_legacy_pages() -> None:
    """Only accessible when debug_mode is ON."""
    if not st.session_state.get("debug_mode"):
        return

    st.sidebar.markdown("---")
    st.sidebar.caption("🔧 旧版页面（调试模式）")
    legacy_page = st.sidebar.radio(
        "Legacy Nav", PAGE_KEYS,
        format_func=lambda v: tr(NAV_LABEL_KEYS.get(v, v)),
        key="legacy_page",
    )

    course = current_course() if legacy_page not in {"dashboard", "courses"} else None

    if legacy_page == "dashboard":
        _page_dashboard_legacy()
    elif legacy_page == "courses":
        _page_courses_legacy()
    elif legacy_page == "profile":
        _page_profile_legacy(course)
    elif legacy_page == "upload":
        _page_upload_legacy(course)
    elif legacy_page == "library":
        _page_library_legacy(course)
    elif legacy_page == "ai":
        _page_ai_legacy(course)
    elif legacy_page == "outputs":
        _page_results_legacy()


def _page_dashboard_legacy() -> None:
    courses = load_courses()
    outputs = list_outputs()
    tasks = get_all_tasks()
    st.title("🏠 首页（旧版）")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(tr("course_count"), len(courses))
    c2.metric(tr("resource_count"), sum(len(resources_for_course(c["course_id"])) for c in courses))
    c3.metric(tr("output_count"), len(outputs))
    c4.metric(tr("task_count"), len(tasks))


def _page_courses_legacy() -> None:
    st.header(tr("courses_title"))
    with st.form("create_course_legacy"):
        university = st.text_input(tr("university"), value=tr("default_university"))
        course_name = st.text_input(tr("course_name"))
        exam_date = st.date_input(tr("exam_date"), value=None)
        if st.form_submit_button(tr("create_course")):
            if course_name.strip():
                course = create_course(university, course_name, exam_date.isoformat() if exam_date else "")
                st.session_state["course_id"] = course["course_id"]
                st.success(tr("course_created"))
    for course in load_courses():
        with st.container(border=True):
            st.write(f"**{course['course_name']}** · {course.get('university', '')}")
            if st.button(tr("set_current"), key=f"select_{course['course_id']}"):
                st.session_state["course_id"] = course["course_id"]
                st.rerun()


def _page_profile_legacy(course: dict | None) -> None:
    st.header(tr("profile_title"))
    if not course:
        st.info(tr("select_course_first"))
        return
    profile = get_profile(course["course_id"])
    with st.form("profile_legacy"):
        goal = st.selectbox(tr("goal"), GOAL_KEYS, format_func=tr)
        level = st.selectbox(tr("level"), LEVEL_KEYS, format_func=tr)
        if st.form_submit_button(tr("save_profile")):
            save_profile(course["course_id"], {"goal": canonical(goal), "level": canonical(level)})
            st.success(tr("profile_saved"))


def _page_upload_legacy(course: dict | None) -> None:
    st.header(tr("upload_title"))
    if not course:
        st.info(tr("select_course_first"))
        return
    uploaded = st.file_uploader(tr("upload_pdf"), type=["pdf"], accept_multiple_files=True)
    if st.button(tr("save_and_index")) and uploaded:
        course_dir = Path("data") / "uploads" / course["course_id"]
        course_dir.mkdir(parents=True, exist_ok=True)
        for uf in uploaded:
            path = course_dir / uf.name
            path.write_bytes(uf.getbuffer())
            try:
                pages = load_pdf_pages(path)
                chunks = split_text_pages(pages)
                if chunks:
                    rebuild_course_store(course["course_id"], chunks)
                    st.success(f"✅ {uf.name}")
            except Exception as exc:
                st.error(f"❌ {uf.name}: {exc}")


def _page_library_legacy(course: dict | None) -> None:
    st.header(tr("library_title"))
    if not course:
        st.info(tr("select_course_first"))
        return
    items = resources_for_course(course["course_id"])
    for item in items:
        with st.container(border=True):
            st.write(f"📄 {item.get('filename', '?')}")
            st.caption(f"{item.get('resource_type', '?')} · {item.get('upload_time', '?')}")


def _page_ai_legacy(course: dict | None) -> None:
    st.header("🤖 AI 学习中心（旧版）")
    if not course:
        st.info(tr("select_course_first"))
        return
    task_type = st.selectbox(tr("task_type"), list(TASK_OPTIONS.keys()), format_func=lambda v: tr(TASK_OPTIONS[v]))
    request = st.text_area(tr("request_label"), value=tr("default_request"), height=120)
    if st.button(tr("generate"), type="primary"):
        task = create_task(course["course_id"], task_type, request)
        run_task_in_background(task["task_id"], course, task_type, request, top_k=5)
        st.session_state.watching_task_id = task["task_id"]
        st.success(tr("task_created"))
        st.rerun()


def _page_results_legacy() -> None:
    st.header(tr("outputs_title"))
    tasks = get_all_tasks()
    if tasks:
        for task in tasks:
            st.write(f"{task.get('task_type', '?')} · {task.get('status', '?')} · {task.get('created_at', '')}")
    outputs = list_outputs()
    if outputs:
        for path in outputs[:10]:
            st.write(path.name)


# ═══════════════════════════════════════════════════════════════════════════
# Main Router
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    init_session()
    render_sidebar()

    # Debug mode: also show legacy nav
    _render_legacy_pages()

    step = st.session_state.get("current_step", "home")

    if step == "home":
        page_home()
    elif step == "goal":
        page_goal()
    elif step == "upload":
        page_upload_wizard()
    elif step == "ai_recognition":
        page_ai_recognition()
    elif step == "preferences":
        page_preferences()
    elif step == "progress":
        page_progress()
    elif step == "results":
        page_results_wizard()
    elif step == "next_steps":
        page_next_steps()
    else:
        page_home()


if __name__ == "__main__":
    main()
