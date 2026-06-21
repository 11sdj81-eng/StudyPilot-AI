"""StudyPilot — AI 学习家教 (ChatGPT-like UI).

产品原则：用户打开只做三件事：选课、问AI、导出PDF。
后台系统（Task/Quality/RAG）折叠在高级区，不暴露给用户。
"""

import os
from pathlib import Path

# ── Load env vars BEFORE any other imports ──
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# ── Page config ──
st.set_page_config(
    page_title="StudyPilot AI",
    page_icon="🐰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init session ──
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "active_course_id" not in st.session_state:
    st.session_state.active_course_id = ""
if "active_course_name" not in st.session_state:
    st.session_state.active_course_name = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# ── Learning memory ──
import json as _json

def _load_profile() -> dict:
    p = Path("data/student_profile.json")
    return _json.loads(p.read_text()) if p.exists() else {}

def _save_profile(profile: dict) -> None:
    Path("data/student_profile.json").write_text(_json.dumps(profile, ensure_ascii=False, indent=2))

def record_weak_point(course_id: str, user_input: str) -> list[str]:
    """Detect '我不会/不懂/不理解' patterns and record weak points.

    Also updates MasteryTracker and WrongQuestionMemory for learning analytics.
    """
    import re
    weak_patterns = [r"我不会(.+?)(?:[，。？！\s]|$)", r"不懂(.+?)(?:[，。？！\s]|$)",
                     r"不理解(.+?)(?:[，。？！\s]|$)", r"怎么理解(.+?)(?:[，。？！\s]|$)",
                     r"讲一下(.+?)(?:[，。？！\s]|$)"]
    for pat in weak_patterns:
        m = re.search(pat, user_input)
        if m:
            concept = m.group(1).strip()[:20]
            if concept and len(concept) >= 2:
                profile = _load_profile()
                course_data = profile.get(course_id, {"weak_points": [], "last_questions": []})
                if concept not in course_data["weak_points"]:
                    course_data["weak_points"].insert(0, concept)
                course_data["weak_points"] = course_data["weak_points"][:10]
                course_data["last_questions"].insert(0, user_input[:100])
                course_data["last_questions"] = course_data["last_questions"][:20]
                profile[course_id] = course_data
                _save_profile(profile)

                # ── Mastery: auto-decrease for weak point ──
                try:
                    from core.mastery_tracker import get_mastery_tracker
                    get_mastery_tracker().record_answer(course_id, concept, is_correct=False)
                except Exception:
                    pass

                # ── Wrong Question Memory: record the question ──
                try:
                    from core.wrong_question_memory import get_wrong_memory
                    get_wrong_memory().record_wrong(
                        course_id=course_id,
                        question=user_input[:200],
                        error_concept=concept,
                    )
                except Exception:
                    pass

                return course_data["weak_points"]
    return get_weak_points(course_id)

def get_weak_points(course_id: str) -> list[str]:
    return _load_profile().get(course_id, {}).get("weak_points", [])[:10]

COURSES = {
    "probability_ch2": {
        "name": "概率论与随机过程", "chapter": "第二章 随机变量及其分布", "icon": "🎲", "demo": False,
        "welcome_examples": ["我不会分布函数", "随机变量怎么理解", "给我出5道第二章题"],
    },
    "field_wave_ch1": {
        "name": "电磁场与电磁波", "chapter": "第一章 静电场", "icon": "⚡", "demo": False,
        "welcome_examples": ["我不会镜像法", "高斯定理怎么考", "电位怎么理解"],
    },
    "digital_logic_ch3": {
        "name": "数字电路逻辑设计", "chapter": "第三章 组合逻辑电路", "icon": "🔌", "demo": True,
        "welcome_examples": ["我不会卡诺图", "触发器怎么考", "组合逻辑怎么化简"],
    },
}

DEFAULT_WELCOME = ["我不会本章重点", "帮我总结本章", "给我出5道题"]


# ═══════════════════════════════════════════════════════════════════════════
# AI Tutor Core — single entry point for ALL user input
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_tutor():
    from core.ai_tutor.orchestrator import get_tutor as _gt
    return _gt()


def get_llm_label() -> str:
    try:
        from core.llm.glm_client import get_llm_status
        s = get_llm_status()
        if s.available:
            return f"🟢 {s.provider.upper()} connected ({s.model})"
        return "🔴 LLM disabled — 配置 DEEPSEEK_API_KEY 或 GLM_API_KEY"
    except Exception:
        return "🔴 LLM: not loaded"


def get_pdf_count(course_id: str) -> int:
    d = Path(f"data/outputs/pdf_v2/{course_id}")
    return len(list(d.glob("*.pdf"))) if d.exists() else 0


def run_tutor(user_input: str, course_id: str, course_name: str) -> dict | None:
    """ALL user input → AITutorOrchestrator. ALWAYS returns dict for session_state, never relies on inline render."""
    import time
    t0 = time.perf_counter()
    orchestrator = get_tutor()

    with st.spinner("思考中…"):
        response = orchestrator.handle(user_input, course_id, course_name)
    latency = round((time.perf_counter() - t0) * 1000)

    # ── Record debug log ──
    debug_entry = {
        "intent": response.get("type", "?"),
        "provider": "deepseek" if orchestrator.llm_available else "none",
        "llm_called": response.get("source") == "LLM_FIRST",
        "fallback_used": response.get("source") != "LLM_FIRST",
        "latency_ms": latency,
        "course_id": course_id,
        "pdf_triggered": response.get("should_trigger_pdf", False),
        "rejected_citations": response.get("rejected_citations", []),
    }
    if "debug_log" not in st.session_state:
        st.session_state.debug_log = []
    st.session_state.debug_log.append(debug_entry)

    content = response.get("content", "")
    resp_type = response.get("type", "chat")
    source = response.get("source", "unknown")

    # ── PDF: save message to history, trigger background task ──
    if response.get("should_trigger_pdf"):
        msg = "📄 正在后台生成 PDF，请稍候…"
        try:
            from core.task_manager import create_task, run_task_in_background
            tid = create_task(course_id, "exam_sprint", user_input)
            tid_str = tid if isinstance(tid, str) else tid.get("task_id", "")
            run_task_in_background(tid_str,
                {"course_id": course_id, "course_name": course_name},
                "exam_sprint", user_input, 5)
            msg = "✅ PDF 生成任务已启动。生成完成后在下方「📂 输出文件」查看。"
        except Exception as e:
            msg = f"❌ PDF 生成失败：{e}"
        return {"answer": msg, "source_level": source, "debug": debug_entry}

    # ── All other intents: return dict for session_state persistence ──
    prefix = {"mock_exam": "✅ 已生成模拟卷：\n\n", "quiz": "✅ 已生成练习题：\n\n",
              "summary": "✅ 本章总结：\n\n"}.get(resp_type, "")
    return {
        "answer": prefix + content,
        "source_level": source,
        "citations": response.get("citations", []),
        "debug": debug_entry,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.title("🐰 StudyPilot")

        # AI Status
        st.caption(get_llm_label())

        # Course selector
        st.divider()
        st.caption("📖 当前课程")
        names = [f"{v['icon']} {v['name']}" for v in COURSES.values()]
        ids = list(COURSES.keys())
        current_idx = ids.index(st.session_state.active_course_id) if st.session_state.active_course_id in ids else 0

        selected_name = st.selectbox("选择课程", names, index=current_idx, label_visibility="collapsed")
        selected_idx = names.index(selected_name)
        selected_id = ids[selected_idx]

        if selected_id != st.session_state.active_course_id:
            st.session_state.active_course_id = selected_id
            st.session_state.active_course_name = COURSES[selected_id]["name"]
            st.session_state.chat_history = []
            st.rerun()

        info = COURSES[selected_id]
        st.caption(f"{info['chapter']}")
        if info["demo"]:
            st.caption("🟡 Demo（无教材）")

        # Materials status
        up_dir = Path(f"data/uploads/{selected_id}")
        has_files = up_dir.exists() and any(up_dir.iterdir())
        st.caption(f"📚 资料：{'已上传' if has_files else '无'}")

        # PDF count
        n_pdf = get_pdf_count(selected_id)
        st.caption(f"📄 已生成 PDF：{n_pdf} 份")

        # Navigation
        st.divider()
        if st.button("🏠 首页", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()

        # Upload
        with st.expander("📤 上传资料"):
            uploaded = st.file_uploader("上传 PDF / PPT / ZIP", type=["pdf", "pptx", "ppt", "zip"],
                                       key="sidebar_upload")
            if uploaded:
                up_dir.mkdir(parents=True, exist_ok=True)
                safe_name = uploaded.name.replace(" ", "_")
                dest = up_dir / safe_name
                dest.write_bytes(uploaded.read())
                st.success(f"✅ 已上传 {uploaded.name}")
                st.rerun()

        # Advanced / Debug (collapsed)
        with st.expander("⚙️ 高级 / 调试"):
            st.caption("以下为技术状态，不影响正常使用。")
            try:
                from core.studypilot_core import get_core
                core = get_core()
                st.caption(f"Workspaces: {len(core.workspace.list_all())}")
                st.caption(f"Tasks: {core.tasks.get_stats()}")
                st.caption(f"RAG courses: {len(core.rag.list_courses())}")
            except Exception:
                pass
            st.caption(f"Typst: {'✅' if Path('/usr/local/bin/typst').exists() or os.system('which typst >/dev/null 2>&1') == 0 else '❌'}")

            # Task list
            try:
                tasks = get_all_tasks()[:5]
                if tasks:
                    st.caption("最近任务：")
                    for t in tasks:
                        emoji = {"success": "✅", "failed": "❌", "running": "🔄"}.get(t.get("status", ""), "⏳")
                        st.caption(f"{emoji} {t.get('task_type','')} — {t.get('message','')[:40]}")
            except Exception:
                pass

            if st.button("🧹 清空聊天"):
                st.session_state.chat_history = []
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Page: Home
# ═══════════════════════════════════════════════════════════════════════════

def page_home():
    st.markdown("# 🐰 StudyPilot AI 学习家教")
    st.markdown("上传教材、PPT、真题，直接问问题、出题、生成讲义。")

    # ── Course cards ──
    st.markdown("### 📚 课程")
    cols = st.columns(len(COURSES))
    for i, (cid, info) in enumerate(COURSES.items()):
        with cols[i]:
            badge = "🟡 Demo" if info["demo"] else "🟢"
            n_pdf = get_pdf_count(cid)
            st.markdown(f"""**{info['icon']} {info['name']}**
{info['chapter']}
{badge} | 📄 {n_pdf} PDF""")
            if st.button("进入课程", key=f"enter_{cid}", use_container_width=True):
                st.session_state.active_course_id = cid
                st.session_state.active_course_name = info["name"]
                st.session_state.chat_history = []
                st.session_state.current_page = "course"
                st.rerun()

    # ── Quick upload ──
    st.divider()
    st.markdown("### 📤 快速上传")
    uploaded = st.file_uploader("拖拽或点击上传教材 PDF / PPT / ZIP", type=["pdf", "pptx", "ppt", "zip"])
    if uploaded:
        cid = st.session_state.active_course_id or "probability_ch2"
        up_dir = Path(f"data/uploads/{cid}")
        up_dir.mkdir(parents=True, exist_ok=True)
        safe_name = uploaded.name.replace(" ", "_")
        (up_dir / safe_name).write_bytes(uploaded.read())
        st.success(f"✅ 已上传 {uploaded.name} 到 {COURSES.get(cid, {}).get('name', cid)}")

    # ── Footer ──
    st.divider()
    st.caption(f"AI 状态：{get_llm_label()}")


# ═══════════════════════════════════════════════════════════════════════════
# Page: Course Chat (ChatGPT-like)
# ═══════════════════════════════════════════════════════════════════════════

def page_course():
    cid = st.session_state.active_course_id
    cinfo = COURSES.get(cid, COURSES["probability_ch2"])
    examples = cinfo.get("welcome_examples", DEFAULT_WELCOME)
    is_demo = cinfo["demo"]
    badge = " 🟡 Demo（无教材，AI 生成内容）" if is_demo else ""

    # ── Top bar: course name + AI status (one line) ──
    st.markdown(f"## {cinfo['icon']} {cinfo['name']} — {cinfo['chapter']}{badge}")
    st.caption(f"{get_llm_label()}  |  📚 资料：{'已上传' if Path(f'data/uploads/{cid}').exists() and any(Path(f'data/uploads/{cid}').iterdir()) else '无'}  |  📄 PDF：{get_pdf_count(cid)} 份")

    # ── Weak points ──
    weak_pts = get_weak_points(cid)
    if weak_pts:
        st.markdown("🎯 **当前薄弱点**：" + " · ".join(f"`{w}`" for w in weak_pts[:5]))

    # ── AI Chat area (first screen, most prominent) ──
    st.markdown("### 🤖 AI 家教")

    # Welcome message — course-aware
    if not st.session_state.chat_history:
        llm_ok = "deepseek" in get_llm_label().lower() and "connected" in get_llm_label().lower()
        if llm_ok:
            welcome = (
                f"我是你的 **{cinfo['name']} {cinfo['chapter']}** AI 家教。"
                f"我会优先用 DeepSeek 解释，再结合你的课程资料。你可以直接问：\n\n"
                f"• {examples[0]}\n• {examples[1]}\n• {examples[2]}\n• 导出 PDF"
            )
        else:
            welcome = (
                f"我是你的 **{cinfo['name']} {cinfo['chapter']}** AI 家教。"
                f"当前未启用大模型，我只能用已有结构化资料回答。你可以直接问：\n\n"
                f"• {examples[0]}\n• {examples[1]}\n• {examples[2]}"
            )
        with st.chat_message("assistant"):
            st.markdown(welcome)

    # Chat history
    for msg in st.session_state.chat_history[-20:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("source"):
                st.caption(f"来源：{msg['source']}")

    # Chat input
    placeholder = f"直接问：{examples[0]} / {examples[1]} / 给我出5道题 / 生成PDF"
    user_input = st.chat_input(placeholder)

    if user_input:
        # Record weak points
        record_weak_point(cid, user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        answer = run_tutor(user_input, cid, cinfo["name"])
        if answer and isinstance(answer, dict):
            source = answer.get("source_level", "unknown")
            # Add RAG citation block if citations exist
            citations = answer.get("citations", [])
            cite_block = ""
            if citations:
                cite_block = "\n\n---\n📚 **教材引用**\n"
                for i, c in enumerate(citations[:3]):
                    fn = (c.get("source_file") or c.get("source") or f"chunk_{c.get('chunk_id','')[:8]}")[:40]
                    pg = f" p{c['page']}" if c.get("page") else ""
                    score = c.get("score", 0)
                    preview = c.get("preview", "")[:100]
                    cite_block += f"\n{i+1}. `{fn}{pg}` (score={score:.3f})\n   _{preview}_\n"
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": answer["answer"] + cite_block,
                "source": source,
            })
        st.rerun()

    # ── Quick action buttons (below chat) ──
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📝 总结本章", use_container_width=True, key="btn_sum"):
            st.session_state.chat_history.append({"role": "user", "content": "帮我总结本章"})
            ans = run_tutor("帮我总结本章", cid, cinfo["name"])
            if ans and isinstance(ans, dict):
                st.session_state.chat_history.append({"role": "assistant", "content": ans["answer"], "source": ans.get("source_level", "")})
            st.rerun()
    with col2:
        # Build quiz prompt — prioritize weak points
        wp = get_weak_points(cid)
        quiz_prompt = f"给我出5道题。重点围绕：{'、'.join(wp[:3])}" if wp else "给我出5道题"
        if st.button("✏️ 出 5 道题", use_container_width=True, key="btn_qz"):
            st.session_state.chat_history.append({"role": "user", "content": quiz_prompt})
            ans = run_tutor(quiz_prompt, cid, cinfo["name"])
            if ans and isinstance(ans, dict):
                st.session_state.chat_history.append({"role": "assistant", "content": ans["answer"], "source": ans.get("source_level", "")})
            st.rerun()
    with col3:
        wp = get_weak_points(cid)
        mock_prompt = f"生成模拟卷。重点围绕：{'、'.join(wp[:3])}" if wp else "生成模拟卷"
        if st.button("📋 生成模拟卷", use_container_width=True, key="btn_mock"):
            st.session_state.chat_history.append({"role": "user", "content": mock_prompt})
            ans = run_tutor(mock_prompt, cid, cinfo["name"])
            if ans and isinstance(ans, dict):
                st.session_state.chat_history.append({"role": "assistant", "content": ans["answer"], "source": ans.get("source_level", "")})
            st.rerun()
    with col4:
        if st.button("📄 导出 PDF", use_container_width=True, key="btn_pdf", type="primary"):
            st.session_state.chat_history.append({"role": "user", "content": "导出 PDF"})
            ans = run_tutor("生成 PDF", cid, cinfo["name"])
            if ans and isinstance(ans, dict):
                st.session_state.chat_history.append({"role": "assistant", "content": ans["answer"], "source": ans.get("source_level", "")})
            st.rerun()

    # ── Output files (collapsed) ──
    with st.expander("📂 输出文件"):
        out_dir = Path(f"data/outputs/pdf_v2/{cid}")
        if out_dir.exists():
            for p in sorted(out_dir.glob("*.pdf"), reverse=True):
                st.text(f"📄 {p.name} ({p.stat().st_size/1024:.0f} KB)")
        else:
            st.text("暂无输出文件。点击「导出 PDF」生成。")

    # ── Debug log (collapsed) ──
    with st.expander("🔍 调试日志"):
        if "debug_log" in st.session_state and st.session_state.debug_log:
            for i, entry in enumerate(reversed(st.session_state.debug_log[-10:])):
                st.json(entry)
        else:
            st.text("暂无日志。发送一条消息后此处会显示调用记录。")
            st.text("暂无输出文件。点击「导出 PDF」生成。")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    render_sidebar()

    page = st.session_state.get("current_page", "home")
    if page == "course" and st.session_state.active_course_id:
        page_course()
    else:
        page_home()


if __name__ == "__main__":
    main()
