"""Build evidence-first content cards from structured StudyPilot data.

PDF 5.0: Course-aware builder. All course routing is via course_id lookup.
No hardcoded EM fallback. Unknown courses go through GenericCoursePlugin.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from core.exam_engine.exam_pattern_database import load_patterns
from core.pdf_content_v2.cache import cache_key, load_cache, save_cache
from core.pdf_content_v2.models import (
    ConceptCard,
    ExamPatternCard,
    ExampleCard,
    FormulaCard,
    MarginNote,
    SourceRef,
)


PRIORITY_BY_FREQUENCY = {
    0: "低：先确认定义",
    1: "中：会出基础题",
    2: "中高：至少做 1 道例题",
    3: "高：考前必须复盘",
}

# ── Course data configuration ─────────────────────────────────────────────
# Each course maps to its golden chapter directory and metadata.
# This is the ONLY place where course-specific data paths are configured.
# No course-specific logic should appear elsewhere.

COURSE_DATA_CONFIG: dict[str, dict] = {
    "field_wave_ch1": {
        "chapter_dir": Path("data/golden_chapters/engineering/electromagnetic_static_chapter1"),
        "pattern_file": Path("data/exam_patterns/engineering/electromagnetic_static_chapter1/patterns.json"),
        "textbook_name": "电磁场与电磁波.pdf",
        "course_name": "电磁场与电磁波",
        "chapter_name": "第一章 静电场",
        "source_hints": {
            "electric_field": ("第 1 章 电场强度小节", "Lecture 1 slide 6-10"),
            "gauss_law": ("第 1 章 高斯定理，约 87-93 页", "Lecture 3 slide 12-18"),
            "potential_gradient": ("第 1 章 电位与梯度小节", "Lecture 4 slide 5-9"),
            "boundary_conditions": ("第 1 章 静电边界条件小节", "Lecture 5 slide 10-14"),
            "image_method": ("第 1 章 镜像法例题小节", "Lecture 6 slide 3-8"),
            "electrostatic_energy": ("第 1 章 静电能量小节", "Lecture 7 slide 4-7"),
        },
        "past_exam_refs": {
            "electric_field": [("2023", "选择题 1"), ("2020-2021", "填空题 1")],
            "gauss_law": [("2017-2018", "计算题"), ("2020-2021", "填空题"), ("2023", "选择题")],
            "potential_gradient": [("2023", "选择题"), ("2017-2018", "填空题")],
            "boundary_conditions": [("2023", "选择题 5"), ("2020-2021", "选择题")],
            "image_method": [("2017-2018", "综合题"), ("2023", "大题")],
            "electrostatic_energy": [("2020-2021", "填空题")],
        },
        "standard_answers": {
            "choice_gauss_symmetry": "必须同时满足电荷分布对称、场强在高斯面上大小相同、方向与面元关系固定。",
            "choice_potential_component": "先写 E=-∇φ，再分别求偏导并代入给定点。",
            "choice_boundary_surface_charge": "切向 E 连续；法向 D 的跳变量等于自由面电荷密度。",
            "choice_image_model": "接地平面另一侧放置异号、对称的镜像电荷，结果只适用于真实求解区域。",
            "choice_energy_density": "线性介质中能量密度与 E² 成正比，场强翻倍时能量密度变为 4 倍。",
            "fill_sphere_enclosed_charge": "r<a 时包围电荷为 Qr³/a³。",
        },
        "confidence": 0.85,
        "is_demo": False,
    },
    "probability_ch2": {
        "chapter_dir": Path("data/golden_chapters/math/probability_random_var_ch2"),
        "pattern_file": None,  # No legacy pattern file for probability
        "textbook_name": "概率论与随机过程.pdf",
        "course_name": "概率论与随机过程",
        "chapter_name": "第二章 随机变量及其分布",
        "source_hints": {
            "random_variable": ("第 2 章 §2.1 随机变量", "Lecture 1 slide 4-8"),
            "distribution_function": ("第 2 章 §2.2 分布函数", "Lecture 2 slide 5-12"),
            "discrete_random_variable": ("第 2 章 §2.3 离散型随机变量", "Lecture 3 slide 3-10"),
            "continuous_random_variable": ("第 2 章 §2.4 连续型随机变量", "Lecture 4 slide 4-11"),
            "common_discrete_distributions": ("第 2 章 §2.5 常见离散分布", "Lecture 5 slide 3-14"),
            "common_continuous_distributions": ("第 2 章 §2.6 常见连续分布", "Lecture 6 slide 2-12"),
            "rv_function_distribution": ("第 2 章 §2.7 随机变量函数的分布", "Lecture 7 slide 3-10"),
        },
        "past_exam_refs": {
            "random_variable": [("2020-2021", "填空题 1")],
            "distribution_function": [("2020-2021", "选择题 2"), ("2019-2020", "填空题 1")],
            "discrete_random_variable": [("2020-2021", "计算题 1"), ("2018-2019", "填空题 2")],
            "continuous_random_variable": [("2018-2019", "计算题 2"), ("2020-2021", "选择题 3")],
            "common_discrete_distributions": [("2019-2020", "计算题 3"), ("2018-2019", "综合题 1"), ("2020-2021", "选择题 4")],
            "common_continuous_distributions": [("2020-2021", "计算题 2"), ("2019-2020", "选择题 3"), ("2018-2019", "填空题 3")],
            "rv_function_distribution": [("2019-2020", "综合题 2"), ("2018-2019", "选择题 5")],
        },
        "standard_answers": {
            "pat_cdf_property": "必须同时满足单调不减、右连续、F(-∞)=0, F(+∞)=1 三条性质。",
            "pat_cdf_to_prob": "P{a<X≤b}=F(b)-F(a)，注意区间左开右闭。",
            "pat_discrete_law": "先列出所有可能取值，计算对应概率，验证 ∑pk=1。",
            "pat_pdf_constant": "由归一化条件 ∫f(x)dx=1 求系数，再由积分求区间概率。",
            "pat_binomial_calc": "代入 B(n,p) 公式 P{X=k}=C(n,k)p^k(1-p)^{n-k}。至少问用补事件。",
            "pat_poisson_approx": "λ=np=3，P{X=2}=λ²e^{-λ}/2!，并说明近似条件 n大p小λ适中。",
            "pat_normal_standardize": "Z=(X-μ)/σ~N(0,1)，查表后注意 Φ(-z)=1-Φ(z)。",
            "pat_transform": "单调函数用公式 f_Y(y)=f_X(h(y))|h'(y)|，非单调用分布函数法分区讨论。",
        },
        "confidence": 0.88,
        "is_demo": False,
    },
    "digital_logic_ch3": {
        "chapter_dir": Path("data/golden_chapters/engineering/digital_logic_ch3_demo"),
        "pattern_file": None,
        "textbook_name": "数字电路逻辑设计.pdf (未上传)",
        "course_name": "数字电路逻辑设计",
        "chapter_name": "第三章 组合逻辑电路",
        "source_hints": {
            "boolean_algebra": ("第 3 章 逻辑代数基础", "AI_DERIVED"),
            "karnaugh_map": ("第 3 章 卡诺图化简", "AI_DERIVED"),
            "combinational_logic": ("第 3 章 组合逻辑电路分析", "AI_DERIVED"),
            "encoder_decoder": ("第 3 章 编码器与译码器", "AI_DERIVED"),
            "multiplexer": ("第 3 章 数据选择器", "AI_DERIVED"),
            "adder_comparator": ("第 3 章 加法器与比较器", "AI_DERIVED"),
            "flip_flop": ("第 3 章 触发器基础", "AI_DERIVED"),
        },
        "past_exam_refs": {},  # No exam data — demo only
        "standard_answers": {},
        "confidence": 0.40,
        "is_demo": True,
    },
}


def get_course_config(course_id: str) -> dict | None:
    """Get the data configuration for a course. Returns None for unknown courses."""
    return COURSE_DATA_CONFIG.get(course_id)


def build_evidence_deck(course_id: str = "field_wave_ch1",
                        chapter_dir: str | Path | None = None) -> dict[str, Any]:
    """Build and cache ConceptCards, ExampleCards and ExamPatternCards.

    PDF 5.0: Course-aware. Routes data loading based on course_id.
    Falls back to GenericCoursePlugin for unknown courses.

    Args:
        course_id: Course identifier (e.g. 'probability_ch2', 'field_wave_ch1')
        chapter_dir: Optional override for the data directory

    Returns:
        Evidence deck dict with concepts, examples, exam_patterns, stats
    """
    config = get_course_config(course_id)

    if config is None:
        # Unknown course — use GenericCoursePlugin for concept extraction
        return _build_generic_deck(course_id)

    base = Path(chapter_dir) if chapter_dir else config["chapter_dir"]
    if not base.exists():
        # Data directory doesn't exist — use generic fallback for this course
        return _build_generic_deck(course_id)

    pattern_file = config.get("pattern_file")
    inputs = [
        base / "concepts.json",
        base / "formulas.json",
        base / "examples.json",
        base / "exam_patterns.json",
        base / "teaching_strategies.json",
    ]
    if pattern_file and pattern_file.exists():
        inputs.append(pattern_file)

    key = cache_key(inputs)
    cached = load_cache(key)
    if cached:
        cached["cache_hit"] = True
        return cached

    raw = {
        "concepts": _load(base / "concepts.json"),
        "formulas": _load(base / "formulas.json"),
        "examples": _load(base / "examples.json"),
        "patterns": _load(base / "exam_patterns.json"),
        "strategies": _load(base / "teaching_strategies.json"),
    }

    # Load legacy pattern objects if available
    pattern_objects = []
    if pattern_file and pattern_file.exists():
        try:
            pattern_objects = load_patterns()
        except Exception:
            pattern_objects = []

    # Build cards using course-specific helpers
    source_hints = config.get("source_hints", {})
    exam_refs = config.get("past_exam_refs", {})
    textbook_name = config.get("textbook_name", "教材")
    ppt_name = config.get("ppt_name", "课堂 PPT")
    standard_answers = config.get("standard_answers", {})

    formulas = _build_formulas(raw["formulas"], source_hints, textbook_name, ppt_name)
    formulas_by_concept: dict[str, list[FormulaCard]] = defaultdict(list)
    for formula in formulas.values():
        formulas_by_concept[formula.concept_id].append(formula)

    exam_patterns = _build_exam_patterns(raw["patterns"], pattern_objects,
                                         exam_refs, standard_answers)
    examples = _build_examples(raw["examples"], pattern_objects,
                               source_hints, textbook_name, ppt_name,
                               exam_refs, standard_answers)
    examples_by_concept: dict[str, list[ExampleCard]] = defaultdict(list)
    for example in examples.values():
        examples_by_concept[example.concept_id].append(example)

    concepts = _build_concepts(raw["concepts"], formulas_by_concept, exam_patterns,
                               source_hints, textbook_name, ppt_name, exam_refs)

    deck = {
        "cache_hit": False,
        "cache_key": key,
        "course_id": course_id,
        "is_demo": config.get("is_demo", False),
        "concepts": {k: v.to_dict() for k, v in concepts.items()},
        "examples": {k: v.to_dict() for k, v in examples.items()},
        "exam_patterns": {k: v.to_dict() for k, v in exam_patterns.items()},
        "stats": {
            "concept_count": len(concepts),
            "example_count": len(examples),
            "exam_pattern_count": len(exam_patterns),
        },
    }
    save_cache(key, deck)
    return deck


def _build_generic_deck(course_id: str) -> dict[str, Any]:
    """Build a minimal evidence deck for unknown courses using GenericCoursePlugin."""
    from core.course_plugins.plugin_registry import get_plugin

    plugin = get_plugin(course_id, allow_generic=True)
    concepts_list = plugin.extract_concepts()
    concept_ids = [f"concept_{i}" for i in range(len(concepts_list))]

    concepts = {}
    for cid, cname in zip(concept_ids, concepts_list):
        concepts[cid] = ConceptCard(
            concept_id=cid,
            title=cname,
            textbook_evidence=[],
            ppt_evidence=[],
            exam_evidence=[],
            explanation=f"AI_DERIVED: {cname}",
            formulas=[],
            difficulty=2,
            exam_frequency=0,
            mastery_level="待自测",
            source_refs=[SourceRef("ai_generated", "",
                                   note="GenericCoursePlugin — 未找到高置信来源",
                                   confidence=0.0)],
            why_important="",
            exam_usage=[],
            common_mistakes=[],
            recommended_priority=PRIORITY_BY_FREQUENCY[0],
            margin_notes=[MarginNote("warning", "Demo only — No user textbook uploaded")],
        ).to_dict()

    return {
        "cache_hit": False,
        "course_id": course_id,
        "is_demo": True,
        "concepts": concepts,
        "examples": {},
        "exam_patterns": {},
        "stats": {"concept_count": len(concepts), "example_count": 0, "exam_pattern_count": 0},
    }


def _load(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _source_ref(raw: dict[str, Any], textbook_name: str,
                fallback_type: str = "textbook") -> SourceRef:
    source_id = str(raw.get("source_id", "")).lower()
    source_type = "textbook"
    if "ppt" in source_id or "lecture" in source_id:
        source_type = "ppt"
    elif "past" in source_id or "exam" in source_id or "题" in raw.get("file_name", ""):
        source_type = "past_exam"
    elif fallback_type in {"textbook", "ppt", "past_exam", "generated_variant"}:
        source_type = fallback_type
    return SourceRef(
        source_type=source_type,  # type: ignore[arg-type]
        file_name=raw.get("file_name") or (textbook_name if source_type == "textbook" else "往年题"),
        page=str(raw.get("page", "")),
        note=str(raw.get("note", "")),
    )


def _textbook_ref(concept_id: str, source_hints: dict, textbook_name: str,
                  confidence: float = 0.85) -> SourceRef:
    page, _ = source_hints.get(concept_id, ("教材相关章节", ""))
    return SourceRef("textbook", textbook_name, page=page, confidence=confidence)


def _ppt_ref(concept_id: str, source_hints: dict, ppt_name: str = "课堂 PPT",
             confidence: float = 0.78) -> SourceRef:
    _, slide = source_hints.get(concept_id, ("", "Lecture slides"))
    return SourceRef("ppt", ppt_name, page=slide, confidence=confidence)


def _past_refs(concept_id: str, exam_refs: dict, textbook_name: str,
               confidence: float = 0.82) -> list[SourceRef]:
    refs = []
    course_short = textbook_name.replace(".pdf", "")
    for year, qno in exam_refs.get(concept_id, []):
        refs.append(SourceRef("past_exam", f"{year} {course_short}期末试卷",
                              year=year, question_no=qno, confidence=confidence))
    return refs


def _build_formulas(raw_formulas: list[dict[str, Any]], source_hints: dict,
                    textbook_name: str, ppt_name: str = "课堂 PPT") -> dict[str, FormulaCard]:
    result = {}
    for item in raw_formulas:
        refs = [_source_ref(ref, textbook_name, "textbook") for ref in item.get("source_refs", [])] \
               or [_textbook_ref(item["concept_id"], source_hints, textbook_name)]
        result[item["id"]] = FormulaCard(
            formula_id=item["id"],
            concept_id=item["concept_id"],
            title=item.get("display_name", item["id"]),
            latex=item.get("latex", ""),
            display_text=item.get("display_text", ""),
            conditions=item.get("conditions", ""),
            symbol_explanation=item.get("symbol_explanation", {}),
            source_refs=refs,
        )
    return result


def _build_exam_patterns(raw_patterns: list[dict[str, Any]], pattern_objects: list[Any],
                         exam_refs: dict, standard_answers: dict) -> dict[str, ExamPatternCard]:
    type_counter: dict[str, Counter[str]] = defaultdict(Counter)
    context_map: dict[str, list[str]] = defaultdict(list)
    score_map: dict[str, list[int]] = defaultdict(list)
    traps: dict[str, list[str]] = defaultdict(list)
    for pattern in raw_patterns:
        for cid in pattern.get("concept_ids", []):
            type_counter[cid][pattern.get("type", "题型")] += 1
            context_map[cid].append(pattern.get("how_tested", ""))
            score_map[cid].append(_score_value(pattern.get("score_weight", "中")))
            if pattern.get("trap"):
                traps[cid].append(pattern["trap"])
    for pattern in pattern_objects:
        for cid in pattern.concept_ids:
            type_counter[cid][pattern.question_type] += 1
            context_map[cid].append(pattern.sample_problem)
            score_map[cid].append(int(pattern.score))
            traps[cid].extend(pattern.common_traps)

    result = {}
    concept_ids = sorted(set(type_counter) | set(exam_refs))
    for cid in concept_ids:
        frequency = len(exam_refs.get(cid, [])) or sum(type_counter[cid].values())
        avg_score = sum(score_map[cid]) / len(score_map[cid]) if score_map[cid] else 0
        result[cid] = ExamPatternCard(
            concept_id=cid,
            frequency=frequency,
            avg_score=round(avg_score, 1),
            question_types=list(type_counter[cid].keys()) or ["未找到高置信题型"],
            common_contexts=_dedupe(context_map[cid])[:4],
            past_exam_refs=[],
            recommended_priority=_priority(frequency),
            how_tested=_dedupe(context_map[cid])[0] if context_map[cid] else "未找到高置信真题考法",
            common_traps=_dedupe(traps[cid])[:4],
        )
    return result


def _build_examples(raw_examples: list[dict[str, Any]], pattern_objects: list[Any],
                    source_hints: dict, textbook_name: str, ppt_name: str,
                    exam_refs: dict, standard_answers: dict) -> dict[str, ExampleCard]:
    result: dict[str, ExampleCard] = {}
    for item in raw_examples:
        cids = item.get("concept_ids", [])
        cid = cids[0] if cids else "unknown"
        refs = [_source_ref(ref, textbook_name, "textbook") for ref in item.get("source_refs", [])] \
               or [_textbook_ref(cid, source_hints, textbook_name)]
        result[item["id"]] = ExampleCard(
            example_id=item["id"],
            concept_id=cid,
            source_type="textbook",
            problem=item.get("question", ""),
            solution_steps=item.get("solution_steps", []),
            standard_answer=item.get("answer", ""),
            annotations=[item.get("exam_focus", ""), *item.get("variants", [])],
            common_mistakes=item.get("common_mistakes", []),
            source_refs=refs,
            difficulty=_difficulty(item.get("difficulty", "典型")),
            grading_points=item.get("rubric", []),
            question_type="教材例题/同类考法",
        )
    for idx, pattern in enumerate(pattern_objects, start=1):
        cid = pattern.concept_ids[0] if pattern.concept_ids else "unknown"
        eid = f"pattern_variant_{pattern.pattern_id}"
        result[eid] = ExampleCard(
            example_id=eid,
            concept_id=cid,
            source_type="generated_variant",
            problem=_variant_problem(pattern.sample_problem, pattern.variation_methods),
            solution_steps=pattern.required_steps,
            standard_answer=_standard_answer(pattern.pattern_id, standard_answers),
            annotations=[
                f"同考法改编：{pattern.source_label}",
                f"命题意图：{pattern.teacher_intent}",
            ],
            common_mistakes=pattern.common_traps,
            source_refs=_past_refs(cid, exam_refs, textbook_name)
                        or [SourceRef("unknown", "", note="未找到高置信来源", confidence=0.0)],
            difficulty=pattern.difficulty,
            grading_points=pattern.grading_points,
            question_type=pattern.question_type,
        )
    return result


def _build_concepts(
    raw_concepts: list[dict[str, Any]],
    formulas_by_concept: dict[str, list[FormulaCard]],
    exam_patterns: dict[str, ExamPatternCard],
    source_hints: dict, textbook_name: str, ppt_name: str, exam_refs: dict,
) -> dict[str, ConceptCard]:
    result = {}
    for item in raw_concepts:
        cid = item["id"]
        textbook = [_source_ref(ref, textbook_name, "textbook")
                    for ref in item.get("source_refs", [])] \
                   or [_textbook_ref(cid, source_hints, textbook_name)]
        ppt = [_ppt_ref(cid, source_hints, ppt_name)]
        exam = _past_refs(cid, exam_refs, textbook_name)
        pattern = exam_patterns.get(cid)
        frequency = pattern.frequency if pattern else len(exam)
        difficulty = _concept_difficulty(frequency, item.get("common_mistakes", []))
        notes = [
            MarginNote("source", f"教材：{textbook[0].label()}", textbook[0]),
            MarginNote("source", f"PPT：{ppt[0].label()}", ppt[0]),
            MarginNote("exam", f"真题：{'; '.join(ref.label() for ref in exam) if exam else '未找到高置信来源'}", exam[0] if exam else None),
            MarginNote("warning", "易错：" + (item.get("common_mistakes") or ["暂无"])[0]),
            MarginNote("tip", f"优先级：{_priority(frequency)}"),
        ]
        refs = [*textbook, *ppt, *exam]
        result[cid] = ConceptCard(
            concept_id=cid,
            title=item.get("display_name") or item.get("name") or cid,
            textbook_evidence=textbook,
            ppt_evidence=ppt,
            exam_evidence=exam,
            explanation=item.get("plain_explanation") or item.get("definition", ""),
            formulas=formulas_by_concept.get(cid, []),
            difficulty=difficulty,
            exam_frequency=frequency,
            mastery_level="待自测",
            source_refs=refs,
            why_important=item.get("why_important", ""),
            exam_usage=item.get("exam_usage", []),
            common_mistakes=item.get("common_mistakes", []),
            recommended_priority=_priority(frequency),
            margin_notes=notes,
        )
    return result


def _score_value(label: str) -> int:
    if "高" in label:
        return 12
    if "中" in label:
        return 8
    return 4


def _difficulty(label: str) -> int:
    if "基础" in str(label):
        return 2
    if "综合" in str(label) or "高" in str(label):
        return 4
    return 3


def _concept_difficulty(frequency: int, mistakes: list[str]) -> int:
    return min(5, max(2, 2 + (1 if frequency >= 2 else 0) + (1 if len(mistakes) >= 3 else 0)))


def _priority(frequency: int) -> str:
    if frequency >= 3:
        return PRIORITY_BY_FREQUENCY[3]
    return PRIORITY_BY_FREQUENCY.get(frequency, PRIORITY_BY_FREQUENCY[1])


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        value = re.sub(r"\s+", " ", value).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _variant_problem(problem: str, variants: list[str]) -> str:
    if not variants:
        return problem
    return f"{problem}（变式：{variants[0]}，保持同一考法与难度。）"


def _standard_answer(pattern_id: str, standard_answers: dict) -> str:
    return standard_answers.get(pattern_id, "按题型识别、公式选择、逐步推导、标准答案四步作答。")


# ═══════════════════════════════════════════════════════════════════════════
# Backward-compatible wrappers (deprecated — use build_evidence_deck(course_id))
# ═══════════════════════════════════════════════════════════════════════════

def build_probability_ch2_deck() -> dict[str, Any]:
    """[DEPRECATED] Use build_evidence_deck('probability_ch2') instead."""
    return build_evidence_deck("probability_ch2")


def build_field_wave_ch1_deck() -> dict[str, Any]:
    """[DEPRECATED] Use build_evidence_deck('field_wave_ch1') instead."""
    return build_evidence_deck("field_wave_ch1")
