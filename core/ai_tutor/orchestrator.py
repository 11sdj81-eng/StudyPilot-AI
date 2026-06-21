"""AITutorOrchestrator — single entry point for ALL user interactions.

LLM First: always try DeepSeek first.
RAG is enhancement, not a gate.
Cross-course questions get answered, not rejected.
PDF only via explicit trigger.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.ai_tutor.intent_router import Intent, IntentResult, get_router
from core.ai_tutor.context_builder import ContextBuilder, detect_course_mismatch


class AITutorOrchestrator:
    """The ONE entry point for all user input. Nothing bypasses this.

    Flow:
        User Input → IntentRouter → LLM First → Context Enhance → Response
    """

    def __init__(self):
        self.router = get_router()
        self.context_builder = ContextBuilder()
        self._llm = None
        self._mastery_tracker = None
        self._wrong_memory = None

    @property
    def mastery(self):
        if self._mastery_tracker is None:
            try:
                from core.mastery_tracker import get_mastery_tracker
                self._mastery_tracker = get_mastery_tracker()
            except Exception:
                self._mastery_tracker = None
        return self._mastery_tracker

    @property
    def wrong_memory(self):
        if self._wrong_memory is None:
            try:
                from core.wrong_question_memory import get_wrong_memory
                self._wrong_memory = get_wrong_memory()
            except Exception:
                self._wrong_memory = None
        return self._wrong_memory

    @property
    def llm(self):
        if self._llm is None:
            try:
                from core.llm.glm_client import get_llm
                self._llm = get_llm()
            except Exception:
                self._llm = None
        return self._llm

    @property
    def llm_available(self) -> bool:
        return self.llm is not None and self.llm.status.available

    # ═══════════════════════════════════════════════════════════════════
    # Main entry point
    # ═══════════════════════════════════════════════════════════════════

    def handle(self, user_input: str, course_id: str = "",
               course_name: str = "") -> dict:
        """Handle ANY user input. Returns a response dict with citations and source level."""
        # 1. Route intent
        intent = self.router.route(user_input)

        # 2. PDF is the ONLY intent that triggers background tasks
        if intent.intent == Intent.PDF_EXPORT:
            return self._handle_pdf(course_id, course_name)

        # 3. Build context (enhancement, not a gate)
        ctx = self.context_builder.build(course_id, user_input) if course_id else {}
        ctx["weak_points"] = self._load_weak_points(course_id) if course_id else []
        citations = self.context_builder.get_citations()
        rejected_citations = self.context_builder.get_rejected_citations()
        has_rag = len(citations) > 0

        # 4. Check cross-course mismatch
        mismatch = detect_course_mismatch(course_id, user_input) if course_id else None

        # 5. Determine source level
        if has_rag:
            source_level = "RAG_ENHANCED"
        elif self.llm_available:
            source_level = "LLM_GENERAL"
        else:
            source_level = "RULE_BASED_FALLBACK"

        # 6. LLM FIRST
        if self.llm_available:
            llm_response = self._try_llm(user_input, intent, ctx, mismatch)
            if llm_response:
                llm_response["source"] = source_level
                llm_response["citations"] = citations
                llm_response["rejected_citations"] = rejected_citations
                return llm_response

        # 7. Fallback
        fb = self._fallback(user_input, intent, ctx, mismatch)
        fb["source"] = source_level
        fb["citations"] = citations
        fb["rejected_citations"] = rejected_citations
        return fb

    # ═══════════════════════════════════════════════════════════════════
    # LLM First
    # ═══════════════════════════════════════════════════════════════════

    def _try_llm(self, user_input: str, intent: IntentResult,
                 ctx: dict, mismatch: dict | None) -> dict | None:
        """Try LLM for any non-PDF intent. Returns None if LLM fails."""
        try:
            course_id = ctx.get("course_id", "")
            course_name = ctx.get("course_name", "")
            seed = ctx.get("seed_context", "")
            rag = ctx.get("rag_context", "")
            has_materials = ctx.get("has_materials", False)
            weak_points = ctx.get("weak_points", [])
            priority_concepts = self._get_priority_concepts(course_id, weak_points)
            weak_note = self._weak_points_instruction(weak_points)
            recurring_note = self._recurring_mistakes_note(course_id)

            # ── Exam Pattern Engine for "怎么考" queries ──
            exam_context = ""
            exam_has_data = False
            is_exam_query = self._is_exam_query(user_input)
            if is_exam_query and course_id:
                try:
                    from core.exam_pattern_engine import get_exam_engine
                    engine = get_exam_engine()
                    # Extract the concept being asked about
                    concept = self._extract_exam_concept(user_input)
                    if concept:
                        formatted = engine.format_for_llm(course_id, concept)
                        exam_context = formatted["exam_context"]
                        exam_has_data = formatted["has_real_data"]
                except Exception:
                    pass

            # Build system prompt with exam context
            system = self._build_system_prompt(
                course_name, has_materials, mismatch,
                exam_context=exam_context,
                exam_has_data=exam_has_data,
            )

            # Build user prompt based on intent
            if intent.intent == Intent.QUIZ:
                priority_str = "、".join(priority_concepts[:5]) if priority_concepts else "本章核心考点"
                user_prompt = f"""为{course_name}生成5道练习题。

可用资料：{seed[:500] if seed else '无'}
RAG检索：{rag[:500] if rag else '无'}
学生薄弱点：{'、'.join(weak_points) if weak_points else '无'}
掌握度最低概念（优先出题）：{priority_str}
{recurring_note}
要求：
- 必须完整生成且只生成5道题，编号为题目1到题目5
- {weak_note}
- 前2道题优先覆盖掌握度最低的概念：{priority_str}
- 每道题必须有：题干、答案、评分点
- 标注 AI_GENERATED，不要模板题
- 最后一行输出 END_OF_QUIZ"""

            elif intent.intent == Intent.SUMMARY:
                user_prompt = f"""用老师口吻总结{course_name}的核心内容。

可用资料：{seed[:800] if seed else rag[:800] if rag else '无'}
要求：3-5个要点，每个要点2-3句话。像老师在考前串讲。"""

            elif intent.intent == Intent.MOCK_EXAM:
                priority_str = "、".join(priority_concepts[:5]) if priority_concepts else "本章核心考点"
                user_prompt = f"""为{course_name}生成一套模拟卷。
题型：5道选择题(4分)+4道填空题(5分)+3道计算题(12分)+1道综合题(24分)，总分100分。
可用概念：{', '.join(ctx.get('course_topics', [])[:5])}
学生薄弱点：{'、'.join(weak_points) if weak_points else '无'}
掌握度最低概念（必须在综合题中覆盖）：{priority_str}
{recurring_note}
要求：
- {weak_note}
- 综合题必须覆盖掌握度最低的概念：{priority_str}
- 必须完整包含：一、选择题；二、填空题；三、计算题；四、综合题；五、参考答案
- 选择题必须给选项和答案；填空题必须给答案；计算题和综合题必须给解答步骤
- 不允许在任何题目中途停止，不允许只写题干不写答案
- 具体题目，不是模板。标注 AI_GENERATED
- 最后一行输出 END_OF_EXAM"""

            else:  # CHAT
                cross_note = ""
                if mismatch:
                    cross_note = f"\n注意：用户当前在{course_name}课程，但问题涉及{mismatch['matched_course_name']}的内容（{','.join(mismatch['matched_topics'])}）。请先说明这一点，然后仍然回答用户的问题。"

                material_note = ""
                if not has_materials:
                    material_note = "\n当前课程未上传教材，以下为通用知识讲解。回答末尾请注明：[当前未上传教材，以下为通用 AI 讲解]"

                # Include richer RAG context
                rag_text = rag[:800] if rag else '无'

                user_prompt = f"""用户问题：{user_input}

当前课程：{course_name}
可用资料：{seed[:500] if seed else '无教材资料'}
RAG检索结果：{rag_text}{cross_note}{material_note}

要求：
- 用老师口吻直接回答，遵循教学链格式
- 第③步如果RAG检索有结果，必须引用具体资料（标注来源文件名）
- 第③步如果RAG检索无结果，标注「通用AI讲解」
- 如果涉及其他课程内容，先说明再回答
- 不要编造教材页码、真题年份
- 如果当前课程无资料，明确说明但不拒答"""

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ]
            max_tokens = self._max_tokens_for_intent(intent.intent)
            result = self.llm._call(messages, temperature=0.5, max_tokens=max_tokens)
            if result.get("text") and not result.get("error"):
                content = result["text"].strip()
                content = self._ensure_complete_output(content, messages, intent.intent, weak_points)
                resp = {
                    "type": intent.intent.value,
                    "content": self._strip_end_markers(content),
                    "source": "LLM_FIRST",
                    "should_trigger_pdf": False,
                }
                # ── Attach tested concepts for quiz/mock_exam ──
                if intent.intent in (Intent.QUIZ, Intent.MOCK_EXAM):
                    resp["tested_concepts"] = self._extract_tested_concepts(
                        content, course_id
                    )
                return resp
        except Exception:
            pass
        return None

    def _load_weak_points(self, course_id: str) -> list[str]:
        try:
            path = Path("data/student_profile.json")
            if not path.exists():
                return []
            profile = json.loads(path.read_text(encoding="utf-8"))
            weak_points = profile.get(course_id, {}).get("weak_points", [])
            return [str(w).strip() for w in weak_points if str(w).strip()][:10]
        except Exception:
            return []

    def _weak_points_instruction(self, weak_points: list[str]) -> str:
        if not weak_points:
            return "如果没有学生薄弱点，按本章核心考点均衡覆盖"
        focus = "、".join(weak_points[:2])
        return f"前2道题必须围绕学生薄弱点：{focus}；题目1和题目2的题干必须直接出现这些薄弱点关键词"

    def _get_priority_concepts(self, course_id: str, weak_points: list[str]) -> list[str]:
        """Merge mastery weakest concepts with student_profile weak_points.

        Returns deduplicated list of up to 5 priority concepts.
        """
        priority = []
        # 1. Lowest mastery from tracker
        try:
            if self.mastery:
                weakest = self.mastery.get_weakest_concepts(course_id, n=3)
                for c, _ in weakest:
                    if c not in priority:
                        priority.append(c)
        except Exception:
            pass
        # 2. Weak points from student profile (dedup)
        for w in weak_points:
            if w not in priority:
                priority.append(w)
        return priority[:5]

    def _recurring_mistakes_note(self, course_id: str) -> str:
        """Build a note about recurring mistakes for the LLM prompt."""
        try:
            if self.wrong_memory:
                recurring = self.wrong_memory.get_recurring_mistakes(
                    course_id, min_occurrences=2
                )
                if recurring:
                    parts = []
                    for r in recurring[:3]:
                        parts.append(f"{r['concept']}({r['count']}次)")
                    return (
                        f"学生反复出错的概念（必须重点出题）：{'、'.join(parts)}。"
                        f"这些概念是学生的顽固薄弱点，请确保至少2道题直接涉及它们。"
                    )
        except Exception:
            pass
        return ""

    def _extract_tested_concepts(self, content: str, course_id: str) -> list[str]:
        """Extract which golden chapter concepts appear in generated quiz/exam content.

        Matches concept names from golden chapters against the content text.
        """
        concepts_found = []
        try:
            # Load concepts from golden chapters
            golden_concepts = self._load_golden_concepts(course_id)
            for concept_name in golden_concepts:
                if concept_name in content:
                    concepts_found.append(concept_name)
        except Exception:
            pass
        return concepts_found

    @staticmethod
    def _load_golden_concepts(course_id: str) -> list[str]:
        """Load concept display names from golden chapters for a course."""
        mapping = {
            "probability_ch2": "data/golden_chapters/math/probability_random_var_ch2/concepts.json",
            "field_wave_ch1": "data/golden_chapters/engineering/electromagnetic_static_chapter1/concepts.json",
            "digital_logic_ch3": "data/golden_chapters/engineering/digital_logic_ch3_demo/concepts.json",
        }
        path = mapping.get(course_id)
        if not path:
            return []
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [c.get("name", "") for c in data if c.get("name")]
            if isinstance(data, dict) and "concepts" in data:
                return [c.get("name", "") for c in data["concepts"] if c.get("name")]
        except Exception:
            pass
        return []

    def _max_tokens_for_intent(self, intent: Intent) -> int:
        if intent == Intent.MOCK_EXAM:
            return 8192
        if intent == Intent.QUIZ:
            return 4096
        return 1024

    def _strip_end_markers(self, content: str) -> str:
        return re.sub(r"\n?\s*END_OF_(QUIZ|EXAM)\s*", "\n", content.strip()).strip()

    def _ensure_complete_output(
        self,
        content: str,
        messages: list[dict],
        intent: Intent,
        weak_points: list[str],
    ) -> str:
        if intent not in (Intent.QUIZ, Intent.MOCK_EXAM):
            return content

        full = content
        for _ in range(2):
            if not self._needs_continuation(full, intent):
                break
            continue_prompt = self._build_continue_prompt(full, intent, weak_points)
            result = self.llm._call(
                messages + [
                    {"role": "assistant", "content": full},
                    {"role": "user", "content": continue_prompt},
                ],
                temperature=0.3,
                max_tokens=3072,
            )
            extra = result.get("text", "").strip()
            if not extra or result.get("error"):
                break
            full = f"{full.rstrip()}\n\n{extra}"
        return full

    def _needs_continuation(self, content: str, intent: Intent) -> bool:
        text = content.strip()
        if intent == Intent.QUIZ:
            if "END_OF_QUIZ" not in text:
                return True
            question_count = len(re.findall(r"题目\s*[1-5]|(?:^|\n)\s*[1-5][.、]", text))
            answer_count = len(re.findall(r"答案", text))
            return question_count < 5 or answer_count < 5

        if "END_OF_EXAM" not in text:
            return True
        required = ["选择题", "填空题", "计算题", "综合题", "参考答案"]
        if any(section not in text for section in required):
            return True
        tail = text[-80:]
        return bool(re.search(r"(若|如果|设|其中|答案|解[:：]?)\s*$", tail))

    def _build_continue_prompt(self, content: str, intent: Intent, weak_points: list[str]) -> str:
        weak = "、".join(weak_points[:2]) if weak_points else "本章核心考点"
        if intent == Intent.QUIZ:
            return (
                f"上一次练习题输出不完整。请只补全缺失部分，保证最终共有5道题，"
                f"每道都有题干、答案、评分点，前2题围绕{weak}。最后输出 END_OF_QUIZ。"
            )
        return (
            f"上一次模拟卷输出不完整。请只从中断处继续补全，必须补齐选择/填空/计算/综合和参考答案，"
            f"前2题围绕{weak}，最后输出 END_OF_EXAM。"
        )

    def _is_exam_query(self, user_input: str) -> bool:
        """Detect if the user is asking 'how is this tested'."""
        exam_patterns = [
            "怎么考", "如何考", "考试怎么", "考什么", "怎么出题",
            "真题", "题型", "分值", "考法", "考试重点",
        ]
        return any(p in user_input for p in exam_patterns)

    def _extract_exam_concept(self, user_input: str) -> str:
        """Extract the concept being asked about in a '怎么考' query."""
        # Remove query markers
        concept = user_input
        for marker in ["怎么考", "如何考", "考试怎么考", "考什么", "怎么出题",
                        "考试重点", "？", "?", "吗"]:
            concept = concept.replace(marker, "")
        return concept.strip() or user_input

    def _build_system_prompt(self, course_name: str, has_materials: bool,
                             mismatch: dict | None,
                             exam_context: str = "",
                             exam_has_data: bool = False) -> str:
        base = f"""你是 StudyPilot AI 家教，一名亲切的大学讲师。当前课程：{course_name}。

教学规则 — 每次回答必须用以下教学链结构：

① 一句话理解：用最简单的比喻或直觉讲清楚这个概念
② 为什么重要：这个概念在课程/考试中的地位
③ 教材/资料怎么说：如果有教材资料，引用教材中的定义或公式。如果有RAG检索结果，必须引用具体来源（标注文件名和页码）。如果无资料，标注「通用AI讲解」
④ 考试怎么考：常见题型、分值、考法
⑤ 典型例题：给一道具体的题目（带数字/公式，不是模板）
⑥ 易错点：最容易犯的 2-3 个错误
⑦ 你可以继续问我什么：推荐 2-3 个相关的后续问题

格式：用数字标号 ①②③④⑤⑥⑦，每段 2-4 句话。总长度 300-500 字。

禁止：
- 只回答一小段定义就结束
- 说"该知识点很重要，建议掌握"这种空话
- 编造教材页码、真题年份、题型分布
- 没有例题的空洞解释
- 在无教材时声称引用了教材内容"""

        if not has_materials:
            base += "\n\n当前课程未上传教材资料。第③步标注「通用AI讲解」，但其他步骤仍要完整。"
        if mismatch:
            base += f"\n\n用户当前在{course_name}但问题涉及其他课程。先说明这一点，再按教学链回答。"

        # ── Exam pattern data injection ──
        if exam_context:
            if exam_has_data:
                base += f"\n\n📋 **以下为真实真题数据，第④步必须使用这些数据**：\n{exam_context}"
                base += "\n第④步要求：使用上述真题数据中的题型、分值、考法。引用来源时标注真题文件名和年份。"
            else:
                base += f"\n\n{exam_context}"
                base += "\n第④步要求：明确说明「暂无真题数据，以下为基于通用教学规律的分析（AI_GENERAL）」。不要编造具体题型分布。"

        return base

    # ═══════════════════════════════════════════════════════════════════
    # Fallback
    # ═══════════════════════════════════════════════════════════════════

    def _fallback(self, user_input: str, intent: IntentResult,
                  ctx: dict, mismatch: dict | None) -> dict:
        """Rule-based fallback when LLM unavailable."""
        seed = ctx.get("seed_context", "")
        course_name = ctx.get("course_name", "")

        # Cross-course note
        cross_note = ""
        if mismatch:
            cross_note = f"\n\n💡 注意：你当前在「{ctx.get('course_name','')}」课程，但「{'、'.join(mismatch['matched_topics'])}」属于「{mismatch['matched_course_name']}」的内容。下面先给你讲清楚：\n\n"

        # Quiz intent
        if intent.intent == Intent.QUIZ:
            try:
                weak_points = ctx.get("weak_points", [])
                from core.studypilot_core.tutor_brain import TutorBrain
                blocks = TutorBrain().build_pdf_blocks(ctx.get("course_id", ""), "MockExam")
                qs = [q for q in blocks.questions if q.question_type in ("选择题", "填空题")][:5]
                weak_qs = self._fallback_weak_point_questions(weak_points)
                base_qs = [
                    f"**{i+1 + len(weak_qs)}. [{q.question_type}]** {q.stem}\n答案：{q.correct_answer[:150]}\n评分点：核心概念、计算过程、答案单位。"
                    for i, q in enumerate(qs[: max(0, 5 - len(weak_qs))])
                ]
                text = "\n\n".join((weak_qs + base_qs)[:5])
                return {"type": "quiz", "content": text, "source": "STRUCTURED_SEED_DATA", "should_trigger_pdf": False}
            except Exception:
                pass

        # Summary intent
        if intent.intent == Intent.SUMMARY:
            try:
                from core.studypilot_core.tutor_brain import TutorBrain
                blocks = TutorBrain().build_pdf_blocks(ctx.get("course_id", ""), "Review")
                text = "\n\n".join(f"**{c.importance_stars} {c.title}**：{c.why_tested}"
                                  for c in blocks.concepts)
                return {"type": "summary", "content": text, "source": "STRUCTURED_SEED_DATA", "should_trigger_pdf": False}
            except Exception:
                pass

        # Chat fallback — use seed data
        if seed:
            content = seed
        else:
            content = f"关于「{user_input}」，当前没有教材资料可供参考。\n\n💡 建议：上传教材 PDF 以获得更精准的讲解。或者配置 GLM_API_KEY / DEEPSEEK_API_KEY 启用 AI 实时讲解。"

        if cross_note:
            content = cross_note + content

        content += f"\n\n---\n*[RULE_BASED_FALLBACK] 基于课程种子数据。配置 API Key 可获得 AI 实时讲解。*"
        return {"type": "chat", "content": content, "source": "STRUCTURED_SEED_DATA" if seed else "RULE_BASED_FALLBACK",
                "should_trigger_pdf": False}

    def _fallback_weak_point_questions(self, weak_points: list[str]) -> list[str]:
        questions = []
        for idx, weak in enumerate(weak_points[:2], start=1):
            questions.append(
                f"**{idx}. [薄弱点专项]** {weak}是什么？请写出核心思想、适用条件，并给出一个具体例子。\n"
                f"答案：围绕{weak}说明定义/建模步骤/适用边界，例题中必须明确已知量和求解目标。\n"
                "评分点：关键词解释准确；适用条件完整；例题步骤清楚。"
            )
        return questions

    # ═══════════════════════════════════════════════════════════════════
    # PDF
    # ═══════════════════════════════════════════════════════════════════

    def _handle_pdf(self, course_id: str, course_name: str) -> dict:
        """PDF is the ONLY intent that triggers background tasks."""
        return {
            "type": "pdf_task",
            "content": "正在后台生成 PDF…",
            "source": "PDF_EXPORT",
            "should_trigger_pdf": True,
            "course_id": course_id,
        }


# ── Singleton ──

_tutor: AITutorOrchestrator | None = None


def get_tutor() -> AITutorOrchestrator:
    global _tutor
    if _tutor is None:
        _tutor = AITutorOrchestrator()
    return _tutor
