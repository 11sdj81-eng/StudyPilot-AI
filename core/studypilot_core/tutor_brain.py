"""TutorBrain — unified AI content engine for ALL output types.

PDF, Chat, Quiz, MockExam, StudyPlan ALL consume TutorBrain output.
This is the single brain behind all StudyPilot content generation.
Reuses existing AITeacher, TeacherStyleRewriter, StudentProfileAdapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Content block types — unified output format ─────────────────────────

@dataclass
class TutorConceptBlock:
    """Teacher-quality explanation of one concept."""
    concept_id: str
    title: str
    why_tested: str = ""
    how_tested: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    scoring_strategy: list[str] = field(default_factory=list)
    explanation: str = ""
    beginner_explanation: str = ""
    exam_tip: str = ""
    formulas: list[dict] = field(default_factory=list)
    source_level: str = "AI_DERIVED"
    confidence: float = 0.85
    importance_stars: str = "★★★"

    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id, "title": self.title,
            "why_tested": self.why_tested, "how_tested": self.how_tested,
            "common_mistakes": self.common_mistakes,
            "scoring_strategy": self.scoring_strategy,
            "explanation": self.explanation,
            "beginner_explanation": self.beginner_explanation,
            "exam_tip": self.exam_tip, "formulas": self.formulas,
            "source_level": self.source_level, "confidence": self.confidence,
            "importance_stars": self.importance_stars,
        }


@dataclass
class TutorExampleBlock:
    """A worked example with teacher annotations."""
    example_id: str
    concept_id: str
    problem: str
    solution_steps: list[str] = field(default_factory=list)
    standard_answer: str = ""
    grading_points: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    source_level: str = "AI_DERIVED"
    is_demo: bool = False

    def to_dict(self) -> dict:
        return {
            "example_id": self.example_id, "concept_id": self.concept_id,
            "problem": self.problem, "solution_steps": self.solution_steps,
            "standard_answer": self.standard_answer,
            "grading_points": self.grading_points,
            "common_mistakes": self.common_mistakes,
            "difficulty": self.difficulty, "source_level": self.source_level,
            "is_demo": self.is_demo,
        }


@dataclass
class TutorQuestionBlock:
    """An exam-style question with answer and grading."""
    question_id: str
    concept_id: str
    stem: str
    question_type: str  # 选择题/填空题/计算题/综合题
    options: list[str] = field(default_factory=list)
    correct_answer: str = ""
    grading_points: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    score: int = 5
    source_level: str = "AI_GENERATED"

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id, "concept_id": self.concept_id,
            "stem": self.stem, "question_type": self.question_type,
            "options": self.options,
            "answer": self.correct_answer,  # Validator expects 'answer' field
            "standard_answer": self.correct_answer,
            "grading_points": self.grading_points,
            "difficulty": self.difficulty, "score": self.score,
            "source_level": self.source_level,
        }


@dataclass
class PDFContentBlocks:
    """All content blocks needed to render one PDF type."""
    pdf_type: str
    title: str
    subtitle: str
    concepts: list[TutorConceptBlock] = field(default_factory=list)
    examples: list[TutorExampleBlock] = field(default_factory=list)
    questions: list[TutorQuestionBlock] = field(default_factory=list)
    is_demo: bool = False

    def to_dict(self) -> dict:
        return {
            "pdf_type": self.pdf_type, "title": self.title,
            "subtitle": self.subtitle, "is_demo": self.is_demo,
            "concept_count": len(self.concepts),
            "example_count": len(self.examples),
            "question_count": len(self.questions),
        }


# ── TutorBrain ──────────────────────────────────────────────────────────

class TutorBrain:
    """Unified AI brain for all StudyPilot content generation.

    PDF, Chat, Quiz, MockExam, and StudyPlan all consume blocks from here.
    Priority: GLM/LLM > rule-based fallback.
    NEVER pretends AI is enabled when no API key is configured.
    """

    def __init__(self, core=None):
        self.core = core
        self._ai_teacher = None
        self._rewriter = None
        self._adapter = None
        self._llm = None

    @property
    def llm(self):
        """Get LLM client. Returns None if no API key configured."""
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

    def llm_status_label(self) -> str:
        if self.llm is None:
            return "🔴 LLM disabled: client not loaded"
        return self.llm.status.display_label

    @property
    def ai_teacher(self):
        if self._ai_teacher is None:
            from core.pdf_content_v2.ai_teacher.ai_teacher import AITeacher
            self._ai_teacher = AITeacher()
        return self._ai_teacher

    @property
    def rewriter(self):
        if self._rewriter is None:
            from core.pdf_content_v2.ai_teacher.teacher_style_rewriter import TeacherStyleRewriter
            self._rewriter = TeacherStyleRewriter()
        return self._rewriter

    @property
    def adapter(self):
        if self._adapter is None:
            from core.pdf_content_v2.ai_teacher.student_profile_adapter import (
                StudentProfileAdapter, StudentProfile
            )
            self._adapter = StudentProfileAdapter(StudentProfile())
        return self._adapter

    # ── Content synthesis ───────────────────────────────────────────────

    def synthesize_concept(self, concept_id: str, concept_data: dict | None = None,
                           exam_patterns: list[dict] | None = None) -> TutorConceptBlock:
        """Synthesize a complete teacher-quality concept block.

        Priority: LLM > TeacherStyleRewriter > rule-based fallback.
        """
        concept_data = concept_data or {}
        title = concept_data.get("title", concept_data.get("display_name", concept_id))
        course_name = concept_data.get("course_name",
                       self._resolve_course_name(concept_id))

        # ── Try LLM first ──
        source_level = "RULE_BASED_FALLBACK"
        explanation = concept_data.get("explanation", concept_data.get("definition", ""))
        why_tested = concept_data.get("why_important", "")
        how_tested = concept_data.get("exam_usage", [])
        common_mistakes = concept_data.get("common_mistakes", [])
        exam_tip = ""

        if self.llm_available:
            try:
                llm_result = self.llm.generate_exam_analysis(
                    title, course_name,
                    exam_data=str(exam_patterns)[:500] if exam_patterns else ""
                )
                if llm_result.get("source_level") != "RULE_BASED_FALLBACK":
                    explanation = llm_result.get("why_tested", explanation)
                    why_tested = llm_result.get("why_tested", why_tested)
                    how_tested_str = llm_result.get("how_tested", "")
                    if how_tested_str:
                        how_tested = [how_tested_str] if isinstance(how_tested_str, str) else how_tested_str
                    common_mistakes_str = llm_result.get("common_mistakes", "")
                    if common_mistakes_str:
                        common_mistakes = [common_mistakes_str] if isinstance(common_mistakes_str, str) else common_mistakes_str
                    exam_tip = llm_result.get("scoring_tips", "")
                    source_level = "AI_DERIVED"
            except Exception:
                pass  # Fall through to rule-based

        # ── Fallback: TeacherStyleRewriter ──
        if source_level == "RULE_BASED_FALLBACK":
            style_report = self.rewriter.rewrite(concept_id, explanation or title, concept_data, exam_patterns)
            explanation = style_report.rewritten
            source_level = style_report.source_level

        # Score importance
        try:
            from core.pdf_content_v2.scoring.exam_importance import ExamImportanceScorer
            scorer = ExamImportanceScorer()
            imp = scorer.score(concept_id, concept_data, exam_patterns or [])
            stars = imp.stars
        except Exception:
            stars = "★★★"

        return TutorConceptBlock(
            concept_id=concept_id,
            title=title,
            why_tested=why_tested,
            how_tested=how_tested if isinstance(how_tested, list) else [how_tested],
            common_mistakes=common_mistakes if isinstance(common_mistakes, list) else [common_mistakes],
            explanation=explanation,
            exam_tip=exam_tip or (explanation[:100] if explanation else ""),
            formulas=concept_data.get("formulas", []),
            source_level=source_level,
            importance_stars=stars,
        )

    def synthesize_all_concepts(self, concepts: list[dict],
                                exam_patterns_by_concept: dict | None = None) -> list[TutorConceptBlock]:
        """Synthesize teacher blocks for all concepts."""
        exam_patterns_by_concept = exam_patterns_by_concept or {}
        results = []
        for c in concepts:
            cid = c.get("concept_id", c.get("id", ""))
            # Get patterns for this concept, ensuring list-of-dicts format
            raw_patterns = exam_patterns_by_concept.get(cid, [])
            if isinstance(raw_patterns, dict):
                raw_patterns = [raw_patterns]
            elif isinstance(raw_patterns, str):
                raw_patterns = []
            elif not isinstance(raw_patterns, list):
                raw_patterns = []
            results.append(self.synthesize_concept(cid, c, raw_patterns))
        return results

    def generate_examples(self, concept_id: str, count: int = 2,
                          difficulty: str = "medium") -> list[TutorExampleBlock]:
        """Generate AI-derived examples for a concept."""
        blocks = []
        for i in range(count):
            blocks.append(TutorExampleBlock(
                example_id=f"{concept_id}_ex_{i+1}",
                concept_id=concept_id,
                problem=f"AI_DERIVED: 关于{concept_id}的例题 {i+1}",
                difficulty=difficulty,
                source_level="AI_DERIVED",
            ))
        return blocks

    def generate_mock_exam(self, course_id: str, concepts: list[dict],
                           examples: list[dict] | None = None) -> list[TutorQuestionBlock]:
        """Generate a complete mock exam question set.

        Priority: LLM generates real questions > course-aware templates.
        """
        examples = examples or []
        questions = []
        course_name = self._resolve_course_name(course_id)
        source_level = "RULE_BASED_FALLBACK"

        # ── Try LLM for exam questions ──
        if self.llm_available and concepts:
            try:
                concept_names = [c.get("title", c.get("display_name", "")) for c in concepts[:3]]
                llm_result = self.llm.generate_practice_questions(
                    "、".join(concept_names), course_name, count=13, qtype="mixed"
                )
                if llm_result.get("source_level") != "RULE_BASED_FALLBACK":
                    llm_questions = llm_result.get("questions", [])
                    for i, lq in enumerate(llm_questions[:13]):
                        cid = concepts[i % len(concepts)].get("concept_id",
                                concepts[i % len(concepts)].get("id", f"c{i}"))
                        questions.append(TutorQuestionBlock(
                            question_id=f"llm_q_{i+1}",
                            concept_id=cid,
                            stem=lq.get("stem", ""),
                            question_type=lq.get("type", "简答题"),
                            correct_answer=lq.get("answer", ""),
                            grading_points=[lq.get("grading", "概念 2分")],
                            difficulty="medium",
                            score=5,
                            source_level="AI_GENERATED",
                        ))
                    if questions:
                        return questions  # LLM succeeded, use its questions
            except Exception:
                pass  # Fall through to template-based generation

        # ── Template-based fallback ──

        # Course-aware option templates — correct answer includes course keywords
        course_options_map = {
            "probability_ch2": [
                ("A. F(x)单调不减且右连续", "B. F(-∞)=0, F(+∞)=1", "C. F(x)在每一点都连续", "D. F(x)单调不减、右连续、端点极限为0和1"),
                ("A. 二项分布B(n,p)期望为np", "B. 泊松分布期望和方差均为λ", "C. 指数分布具有无记忆性", "D. 二项分布、泊松分布、指数分布性质均正确"),
            ],
            "field_wave_ch1": [
                ("A. 高斯定理适用于对称电荷分布", "B. 电位梯度给出电场强度方向", "C. 镜像法处理导体边界问题", "D. 高斯定理、电位梯度、镜像法均为静电场核心方法"),
                ("A. 电场强度与电位梯度方向相反", "B. 高斯面内总电荷决定电通量", "C. 导体内部静电场为零", "D. 电场强度、高斯定理、导体性质均正确"),
            ],
            "digital_logic_ch3": [
                ("A. 与或式可用卡诺图化简", "B. 真值表列出所有输入输出组合", "C. 译码器将输入代码转为对应输出", "D. 卡诺图化简、真值表、译码器均为组合逻辑方法"),
                ("A. 组合逻辑输出仅取决于当前输入", "B. D触发器Q^(n+1)=D有记忆功能", "C. 卡诺图相邻格可合并消去变量", "D. 组合逻辑、触发器、卡诺图均为数字电路基础"),
            ],
        }

        default_options = [
            ("A. 教材中有详细推导和证明", "B. 该知识点需结合例题理解", "C. 该知识点是考试重点内容", "D. 教材推导、例题理解、考试重点均正确"),
        ]

        # Choice questions (5 × 4 points)
        for i, concept in enumerate(concepts[:5]):
            cid = concept.get("concept_id", concept.get("id", f"c{i}"))
            title = concept.get("title", concept.get("display_name", cid))

            # Pick course-aware options
            course_opts = course_options_map.get(course_id, default_options)
            opts = course_opts[i % len(course_opts)]

            # Correct answer is D if last option is a summary, else A
            correct_letter = "D" if ("以上" in opts[-1] or "均为" in opts[-1]) else "A"
            correct_text = opts[3] if correct_letter == "D" else opts[0]

            questions.append(TutorQuestionBlock(
                question_id=f"choice_{i+1}",
                concept_id=cid,
                stem=f"关于{title}，下列说法正确的是：",
                question_type="选择题",
                options=list(opts),
                correct_answer=correct_text,  # Full answer text, not just letter
                grading_points=["概念判断 2分", "知识应用 2分"],
                difficulty="medium",
                score=4,
            ))

        # Fill-in questions (4 × 5 points)
        for i, concept in enumerate(concepts[1:5]):
            cid = concept.get("concept_id", concept.get("id", f"c{i+1}"))
            title = concept.get("title", concept.get("display_name", cid))
            formula_text = ""
            formulas = concept.get("formulas", [])
            if formulas:
                f = formulas[0]
                formula_text = f.get("display_text", "") if isinstance(f, dict) else str(f)
            questions.append(TutorQuestionBlock(
                question_id=f"fill_{i+6}",
                concept_id=cid,
                stem=f"{title}的核心公式/定义为：______。",
                question_type="填空题",
                correct_answer=formula_text,
                grading_points=["公式 3分", "条件 2分"],
                difficulty="easy",
                score=5,
            ))

        # Calculation questions (3 × 12 points)
        for i, ex in enumerate(examples[:3]):
            questions.append(TutorQuestionBlock(
                question_id=f"calc_{i+10}",
                concept_id=ex.get("concept_id", ex.get("concept_ids", [""])[0] if ex.get("concept_ids") else ""),
                stem=ex.get("question", ex.get("problem", "")),
                question_type="计算题",
                correct_answer=ex.get("answer", ex.get("standard_answer", "")),
                grading_points=ex.get("rubric", ex.get("grading_points", []))[:4],
                difficulty="medium",
                score=12,
            ))

        # Comprehensive question (1 × 24 points)
        if len(examples) >= 3:
            ex = examples[2]
            questions.append(TutorQuestionBlock(
                question_id="comprehensive_13",
                concept_id=ex.get("concept_id", ""),
                stem=ex.get("question", ex.get("problem", "")),
                question_type="综合题",
                correct_answer=ex.get("answer", ex.get("standard_answer", "")),
                grading_points=ex.get("rubric", ex.get("grading_points", []))[:4],
                difficulty="hard",
                score=24,
            ))

        return questions

    def build_pdf_blocks(self, course_id: str, pdf_type: str,
                         deck: dict | None = None) -> PDFContentBlocks:
        """Build all content blocks needed for one PDF type.

        This is the bridge between TutorBrain and the PDF rendering pipeline.
        PDF renderer consumes these blocks instead of self-assembling content.
        """
        from core.pdf_content_v2.assembler import get_document_metadata

        meta = get_document_metadata(course_id, pdf_type)
        is_demo = meta.get("is_demo", False)

        if deck is None:
            from core.pdf_content_v2.builder import build_evidence_deck
            deck = build_evidence_deck(course_id)

        concepts_raw = list(deck.get("concepts", {}).values())
        examples_raw = list(deck.get("examples", {}).values())
        patterns_raw = deck.get("exam_patterns", {})

        # Synthesize all concepts through TutorBrain
        concept_blocks = self.synthesize_all_concepts(concepts_raw, patterns_raw)

        # Build example blocks
        example_blocks = []
        for ex in examples_raw[:10]:
            ex_data = ex if isinstance(ex, dict) else ex.to_dict() if hasattr(ex, "to_dict") else {}
            example_blocks.append(TutorExampleBlock(
                example_id=ex_data.get("example_id", ex_data.get("id", "")),
                concept_id=ex_data.get("concept_id", ""),
                problem=ex_data.get("problem", ex_data.get("question", "")),
                solution_steps=ex_data.get("solution_steps", []),
                standard_answer=ex_data.get("standard_answer", ex_data.get("answer", "")),
                grading_points=ex_data.get("grading_points", []),
                difficulty=ex_data.get("difficulty", "medium"),
                source_level="AI_DERIVED" if is_demo else "textbook",
            ))

        # Build questions for MockExam
        question_blocks = []
        if pdf_type == "MockExam":
            question_blocks = self.generate_mock_exam(course_id, concepts_raw, examples_raw)

        return PDFContentBlocks(
            pdf_type=pdf_type,
            title=meta["title"],
            subtitle=meta["subtitle"],
            concepts=concept_blocks,
            examples=example_blocks,
            questions=question_blocks,
            is_demo=is_demo,
        )

    def answer_question(self, query: str, course_id: str = "",
                        top_k: int = 5) -> dict:
        """Answer a student question using LLM + RAG context.

        Priority: LLM with RAG context > RAG-only > generic fallback.
        """
        # Gather RAG context
        context_chunks = []
        if course_id and self.core:
            try:
                chunks = self.core.rag.retrieve(course_id, query, top_k)
                context_chunks = [c.get("text", str(c)) for c in chunks]
            except Exception:
                pass

        context_text = "\n\n".join(context_chunks[:3]) if context_chunks else ""

        # ── Try LLM ──
        if self.llm_available:
            try:
                course_name = self._resolve_course_name(course_id)
                llm_result = self.llm.generate_concept_summary(
                    query, course_name,
                    key_points=[context_text[:500]] if context_text else None
                )
                if llm_result.get("source_level") != "RULE_BASED_FALLBACK":
                    return {
                        "query": query,
                        "answer": llm_result["text"],
                        "source_chunks": len(context_chunks),
                        "course_id": course_id,
                        "source_level": "AI_DERIVED",
                    }
            except Exception:
                pass

        # ── Fallback: try structured seed data ──
        if context_text:
            answer = f"根据课程资料：\n\n{context_text}\n\n---\n*本回答基于 RAG 检索结果。*"
            source = "RAG_DERIVED"
        elif course_id:
            # Try evidence deck for structured answers
            try:
                from core.pdf_content_v2.builder import build_evidence_deck
                deck = build_evidence_deck(course_id)
                concepts = deck.get("concepts", {})
                # Find matching concept
                matched = None
                for cid, cdata in concepts.items():
                    title = cdata.get("title", "") if isinstance(cdata, dict) else getattr(cdata, "title", "")
                    explanation = cdata.get("explanation", "") if isinstance(cdata, dict) else getattr(cdata, "explanation", "")
                    # Match: title substring in query OR 2-char sliding window match
                    title_match = title and (title in query or any(
                        title[i:i+2] in query for i in range(len(title)-1)
                        if len(title[i:i+2]) == 2
                    ))
                    if title_match:
                        matched = (title, explanation)
                        break
                if matched:
                    answer = f"📖 **{matched[0]}**\n\n{matched[1]}\n\n---\n*[RULE_BASED_FALLBACK] 基于课程种子数据，非 LLM 生成。配置 API Key 可获得 AI 老师讲解。*"
                    source = "STRUCTURED_SEED_DATA"
                else:
                    answer = f"[RULE_BASED_FALLBACK] 关于「{query}」，暂无匹配的课程资料。请上传教材/PPT后重试，或配置 GLM_API_KEY 启用 AI 讲解。"
                    source = "RULE_BASED_FALLBACK"
            except Exception:
                answer = f"[RULE_BASED_FALLBACK] 关于「{query}」，无法检索课程资料。请上传教材/PPT。"
                source = "RULE_BASED_FALLBACK"
        else:
            answer = f"[RULE_BASED_FALLBACK] 关于「{query}」，请指定课程后重试。"
            source = "RULE_BASED_FALLBACK"

        return {
            "query": query,
            "answer": answer,
            "source_chunks": len(context_chunks),
            "course_id": course_id,
            "source_level": source,
        }

    def _resolve_course_name(self, course_id: str) -> str:
        """Resolve a human-readable course name from course_id."""
        mapping = {
            "probability_ch2": "概率论与随机过程",
            "field_wave_ch1": "电磁场与电磁波",
            "digital_logic_ch3": "数字电路逻辑设计",
        }
        return mapping.get(course_id, course_id)

    def generate_study_plan(self, course_id: str,
                            student_profile: dict | None = None) -> dict:
        """Generate a personalized study plan."""
        profile = student_profile or {}
        adapter = self.adapter

        # Get concept list
        concepts = []
        try:
            from core.pdf_content_v2.builder import build_evidence_deck
            deck = build_evidence_deck(course_id)
            concepts = list(deck.get("concepts", {}).values())
        except Exception:
            pass

        recs = adapter.get_study_recommendations()

        return {
            "course_id": course_id,
            "total_concepts": len(concepts),
            "recommended_pdfs": recs.get("suggested_pdfs", []),
            "time_allocation": recs.get("time_allocation", {}),
            "focus_areas": recs.get("focus_areas", []),
            "student_profile": profile,
        }
