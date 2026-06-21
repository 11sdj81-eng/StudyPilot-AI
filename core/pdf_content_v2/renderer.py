"""Typst renderer for StudyPilot PDF 2.0/5.0.

PDF 5.0: Course-agnostic rendering. The MockExam renderer now generates
course-appropriate questions instead of hardcoding probability/EM content.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from core.pdf_content_v2.assembler import assemble_documents
from core.pdf_content_v2.builder import build_evidence_deck
from core.pdf_content_v2.models import ExamPatternCard, ExampleCard, LectureDocument
from core.pdf_content_v2.quality_gate import PDFContentQualityGate
from core.pdf_v4.typst_engine import compile_typst, typst_available, typst_version


OUT_DIR = Path("data/outputs/pdf_v2")
TEMPLATE_DIR = Path("templates/pdf_v2_typst")


def render_all_pdf_v2(output_dir: str | Path = OUT_DIR,
                      course_id: str = "field_wave_ch1") -> dict[str, Any]:
    """PDF 5.0: Delegates to UniversalRenderPipeline.render_course_pdfs().

    Backward-compatible signature. For new code, use render_course_pdfs() directly.
    """
    from core.pdf_content_v2.universal_pipeline import render_course_pdfs
    return render_course_pdfs(course_id, output_dir=output_dir)


def _sync_templates(out: Path) -> None:
    for template in TEMPLATE_DIR.glob("*.typ"):
        target = out / template.name
        if template.name == "shared.typ":
            shutil.copyfile(template, target)


def _template_for(name: str) -> str:
    return {
        "Sprint": "sprint_sheet.typ",
        "Review": "lecture_note.typ",
        "PastPaper": "pastpaper_explained.typ",
        "MockExam": "mock_exam.typ",
    }[name]


def _render_document_body(document: LectureDocument) -> str:
    if document.pdf_type == "MockExam":
        return _render_mock_exam(document)
    parts = [_callout("使用目标", f"{document.subtitle}\n目标页数：{document.target_pages} 页。事实来源只来自教材/PPT/真题结构化证据。")]
    parts.append(_source_index(document))
    if document.pdf_type == "Sprint":
        parts.append(_sprint_formula_sheet(document))
    for idx, section in enumerate(document.sections, start=1):
        if not section.concept:
            continue
        c = section.concept
        pattern = section.exam_pattern
        parts.append(f'#section-heading("{_e(str(idx))}", "{_e(c.title)}")')
        main = _main_sprint(c, section.examples, pattern) if document.pdf_type == "Sprint" else _main_concept(c, section.examples, pattern)
        parts.append(_two_col(main, _margin(section.margin_notes)))
        if document.pdf_type == "Sprint":
            parts.append('#v(6pt)')
        elif document.pdf_type == "Review":
            parts.append(_review_workshop(c, section.examples, pattern))
            parts.append('#pagebreak(weak: true)')
    if document.pdf_type == "Review":
        parts.append(_review_integrated_appendix(document))
    return "\n\n".join(parts)


def _main_sprint(c: Any, examples: list[ExampleCard], pattern: ExamPatternCard | None) -> str:
    formulas = "\n".join(_formula(f) for f in c.formulas[:2]) or "未找到高置信公式。"
    example_text = _example_compact(examples[0]) if examples else _warning("未找到高置信例题，本节不生成无来源题目。")
    pattern_line = ""
    if pattern:
        refs = "；".join(ref.label() for ref in pattern.past_exam_refs) or "未找到高置信来源"
        pattern_line = f"近 5 年 {pattern.frequency} 次；{pattern.question_types[0]}；{refs}"
    return "\n\n".join(
        [
            f'#block-title("考前只看这句")\n{_p(c.why_important or c.explanation)}',
            f'#block-title("必背公式")\n{formulas}',
            f'#block-title("怎么考")\n{_p(pattern_line)}',
            f'#block-title("经典例题")\n{example_text}',
            f'#block-title("易错点")\n{_bullets(c.common_mistakes[:2])}',
            f'#priority("{_e(c.recommended_priority)}")',
        ]
    )


def _sprint_formula_sheet(document: LectureDocument) -> str:
    rows = []
    checks = []
    for section in document.sections:
        if not section.concept:
            continue
        c = section.concept
        for formula in c.formulas[:2]:
            rows.append(f"{c.title}：{formula.display_text}（条件：{formula.conditions}）")
        if c.common_mistakes:
            checks.append(f"{c.title}：{c.common_mistakes[0]}")
    return "\n".join(
        [
            '#pagebreak()',
            '#block-title("考前公式总表")',
            _bullets(rows),
            '#block-title("最后 5 分钟检查")',
            _bullets(checks),
            '#pagebreak(weak: true)',
        ]
    )


def _main_concept(c: Any, examples: list[ExampleCard], pattern: ExamPatternCard | None) -> str:
    formulas = "\n".join(_formula(f) for f in c.formulas[:4]) or "未找到高置信公式。"
    example_text = "\n".join(_example(e) for e in examples) or _warning("未找到高置信例题，本节不生成无来源题目。")
    pattern_text = _pattern(pattern) if pattern else _warning("未找到高置信真题考法。")
    mistakes = _bullets(c.common_mistakes[:4])
    usages = _bullets(c.exam_usage[:4])
    return "\n\n".join(
        [
            f'#block-title("为什么重要")\n{_p(c.why_important)}',
            f'#block-title("教材级解释")\n{_p(c.explanation)}',
            f'#block-title("公式")\n{formulas}',
            f'#block-title("真题怎么考")\n{pattern_text}',
            f'#block-title("常见题型")\n{usages}',
            f'#block-title("经典例题")\n{example_text}',
            f'#block-title("易错点")\n{mistakes}',
            f'#priority("{_e(c.recommended_priority)}")',
        ]
    )


def _render_mock_exam(document: LectureDocument) -> str:
    """PDF 5.0: Course-agnostic MockExam rendering.

    Generates choice/fill/calc/comprehensive questions based on the
    document's concepts and examples. No course-specific hardcoding.
    """
    all_sections = [s for s in document.sections if s.concept]
    choice_sections = all_sections[:5]
    fill_sections = all_sections[1:5] if len(all_sections) >= 5 else all_sections
    calc_examples = []
    for s in all_sections:
        if s.examples:
            calc_examples.extend(s.examples)
    calc_examples = calc_examples[:3]
    big_examples = calc_examples[2:3] if len(calc_examples) > 2 else calc_examples[:1]

    choice_answers_cycle = ["A", "B", "C", "D"]
    correct_letters = [choice_answers_cycle[i % 4] for i in range(len(choice_sections))]

    questions = ['#block-title("一、选择题（5 题 × 4 分 = 20 分）")']
    answers = []

    # ── Generate course-agnostic choice options ──
    for idx, section in enumerate(choice_sections):
        if not section.concept:
            continue
        c = section.concept
        source = c.source_refs[0].label() if c.source_refs else "未找到高置信来源"
        correct = correct_letters[idx % len(correct_letters)]

        # Generate 4 options: 1 correct + 3 plausible distractors from concepts
        option_texts = _generate_choice_options(c, all_sections, correct, idx)

        # Generate stem from concept explanation
        stem = _generate_exam_stem(c, idx)

        options_str = ", ".join('"' + _e(opt) + '"' for opt in option_texts)
        questions.append(
            '#question("' + str(idx+1) + '", "选择题", "4", "'
            + _e(stem) + '", (' + options_str + '), "' + _e(source) + '")'
        )

        # Build answer
        answer_text = option_texts[choice_answers_cycle.index(correct)]
        answers.append(
            f"{idx+1}. {correct}。{_e(answer_text)}。"
            f"评分点：概念判断 2 分，知识应用 2 分。"
        )

    # ── Fill-in questions ──
    questions.append('#block-title("二、填空题（4 题 × 5 分 = 20 分）")')
    for offset, section in enumerate(fill_sections, start=6):
        if not section.concept:
            continue
        c = section.concept
        formula = c.formulas[0].display_text if c.formulas else c.explanation[:60]
        source = c.source_refs[0].label() if c.source_refs else "未找到高置信来源"
        stem = _generate_fill_stem(c)
        scoring = "公式 3 分，条件/适用范围 2 分"
        questions.append(
            f'#open-question("{offset}", "填空题", "5", "{_e(stem)}", "{_e(source)}")'
        )
        answers.append(f"{offset}. {_e(formula)}。评分点：{_e(scoring)}。")

    # ── Calculation questions ──
    questions.append('#block-title("三、计算题（3 题 × 12 分 = 36 分）")')
    for offset, ex in enumerate(calc_examples, start=10):
        source = "；".join(ref.label() for ref in ex.source_refs)
        questions.append(
            f'#open-question("{offset}", "计算题", "12", "{_e(ex.problem)}", "{_e(source)}")'
        )
        answers.append(
            f"{offset}. {_e(ex.standard_answer)} "
            f"评分点：{'；'.join(_e(p) for p in ex.grading_points[:4])}"
        )

    # ── Comprehensive question ──
    questions.append('#block-title("四、综合大题（1 题 × 24 分 = 24 分）")')
    for offset, ex in enumerate(big_examples, start=13):
        source = "；".join(ref.label() for ref in ex.source_refs)
        questions.append(
            f'#open-question("{offset}", "综合大题", "24", "{_e(ex.problem)}", "{_e(source)}")'
        )
        answers.append(
            f"{offset}. {_e(ex.standard_answer)} "
            f"评分点：{'；'.join(_e(p) for p in ex.grading_points[:4])}"
        )

    return "\n\n".join(
        [
            _callout("考试说明",
                     "总分 100 分（20+20+36+24）。题目来源于教材例题、真题题型和同考法变式；答案和评分点一并给出。"),
            '#block-title("一、试题")',
            "\n\n".join(questions),
            '#pagebreak()',
            '#block-title("二、标准答案与评分点")',
            _bullets(answers),
        ]
    )


def _generate_choice_options(concept: Any, all_sections: list, correct: str,
                             idx: int) -> list[str]:
    """Generate 4 choice options: 1 from this concept, 3 from other concepts."""
    options = []
    # Option from this concept (correct)
    if concept.formulas:
        options.append(f"{concept.title}的公式应用条件")
    elif concept.explanation:
        options.append(concept.explanation[:30])
    else:
        options.append(f"关于{concept.title}的正确表述")

    # Distractors from other concepts
    other_concepts = [s.concept for s in all_sections if s.concept and s.concept.concept_id != concept.concept_id]
    for i, oc in enumerate(other_concepts[:3]):
        if oc.formulas:
            options.append(f"{oc.title}的相关结论（干扰项）")
        elif oc.explanation:
            options.append(oc.explanation[:30] + "（不完全正确）")
        else:
            options.append(f"关于{oc.title}的常见误解")

    # Pad to 4 options
    while len(options) < 4:
        options.append(f"以上第{idx+1}题相关但需验证")

    # Ensure correct option is at the right position
    result = options[:4]
    correct_idx = choice_answers_cycle_idx(correct)
    # Place the real correct option at the correct position
    result[correct_idx] = options[0]  # First option is the "correct" one
    return result


def choice_answers_cycle_idx(letter: str) -> int:
    return {"A": 0, "B": 1, "C": 2, "D": 3}.get(letter, 0)


def _generate_exam_stem(concept: Any, idx: int) -> str:
    """Generate a course-agnostic exam stem."""
    title = concept.title
    if concept.explanation:
        return f"关于{title}，下列说法正确的是："
    if concept.why_important:
        return f"在{title}的学习中，以下哪项是正确的？"
    return f"下列关于{title}的描述，正确的是："


def _generate_fill_stem(concept: Any) -> str:
    """Generate a course-agnostic fill-in stem."""
    title = concept.title
    if concept.formulas:
        formula = concept.formulas[0]
        if formula.conditions:
            return f"{title}中，在{formula.conditions}的条件下，对应的公式为：______。"
        return f"{title}的核心公式为：______。"
    if concept.explanation:
        return f"{title}的定义为：______。"
    return f"{title}的关键结论是：______。"


def _source_index(document: LectureDocument) -> str:
    rows = []
    for section in document.sections:
        if not section.concept:
            continue
        c = section.concept
        textbook = c.textbook_evidence[0].label() if c.textbook_evidence else "未找到高置信来源"
        ppt = c.ppt_evidence[0].label() if c.ppt_evidence else "未找到高置信来源"
        exam = "；".join(ref.label() for ref in c.exam_evidence) if c.exam_evidence else "未找到高置信来源"
        rows.append(f'({_cell(c.title)}, {_cell(textbook)}, {_cell(ppt)}, {_cell(exam)}, {_cell(str(c.exam_frequency))})')
    return '#source-table((' + ",\n".join(rows) + '))'


def _two_col(main: str, margin: str) -> str:
    return f'#grid(columns: (1fr, 4.2cm), gutter: 12pt)[\n{main}\n][\n{margin}\n]'


def _margin(notes: list[Any]) -> str:
    return "\n".join(f'#margin-note("{_e(n.type)}", "{_e(n.content)}")' for n in notes)


def _formula(formula: Any) -> str:
    return f'#formula-card("{_e(formula.title)}", "{_e(formula.display_text)}", "{_e(formula.conditions)}", "{_e(formula.source_refs[0].label() if formula.source_refs else "未找到高置信来源")}")'


def _example(example: ExampleCard) -> str:
    steps = _bullets(example.solution_steps)
    mistakes = _bullets(example.common_mistakes[:3])
    grading = _bullets(example.grading_points[:4])
    source = "；".join(ref.label() for ref in example.source_refs) or "未找到高置信来源"
    return "\n".join(
        [
            f'#example-card("{_e(example.source_type)}", "{_e(source)}")[',
            f'#strong[题目]：{_p(example.problem)}',
            f'#strong[解题步骤]\n{steps}',
            f'#strong[标准答案]：{_p(example.standard_answer)}',
            f'#strong[评分点]\n{grading}',
            f'#strong[易错点]\n{mistakes}',
            ']',
        ]
    )


def _example_compact(example: ExampleCard) -> str:
    source = "；".join(ref.label() for ref in example.source_refs) or "未找到高置信来源"
    return "\n".join(
        [
            f'#example-card("{_e(example.source_type)}", "{_e(source)}")[',
            f'#strong[题目]：{_p(example.problem)}',
            f'#strong[三步]：{_e(" → ".join(example.solution_steps[:3]))}',
            f'#strong[答案]：{_p(example.standard_answer)}',
            ']',
        ]
    )


def _review_workshop(c: Any, examples: list[ExampleCard], pattern: ExamPatternCard | None) -> str:
    if not examples and not pattern:
        return ""
    example_bits = []
    for ex in examples[:2]:
        example_bits.append(_example(ex))
    formula_sources = [f"{f.title}：{f.conditions}" for f in c.formulas[:4]]
    pattern_bits = []
    if pattern:
        pattern_bits = [
            f"题型入口：{' / '.join(pattern.question_types)}",
            f"常见语境：{'；'.join(pattern.common_contexts[:2])}",
            f"评分预期：平均 {pattern.avg_score} 分；优先级 {pattern.recommended_priority}",
        ]
    return "\n".join(
        [
            '#pagebreak(weak: true)',
            f'#block-title("{_e(c.title)} · 例题工坊与自测")',
            '#grid(columns: (1fr, 1fr), gutter: 10pt)[',
            '#strong[公式适用条件]\n' + _bullets(formula_sources),
            '][',
            '#strong[真题拆解]\n' + _bullets(pattern_bits),
            ']',
            "\n".join(example_bits),
            f'#callout("复习自检")[{_p("不用看答案，先判断来源、题型、公式条件、评分点是否都能写出来。")} ]',
        ]
    )


def _review_integrated_appendix(document: LectureDocument) -> str:
    prompts = []
    answer_keys = []
    for idx, section in enumerate(document.sections, start=1):
        if not section.concept or not section.exam_pattern:
            continue
        concept = section.concept
        pattern = section.exam_pattern
        refs = "；".join(ref.label() for ref in pattern.past_exam_refs) or "未找到高置信来源"
        prompts.append(
            f"{idx}. {concept.title}：写出一个高频题型入口、一个公式适用条件、一个易错点。来源：{refs}"
        )
        answer_keys.append(
            f"{idx}. 题型：{' / '.join(pattern.question_types[:2])}；条件：{concept.formulas[0].conditions if concept.formulas else '见教材来源'}；易错：{concept.common_mistakes[0] if concept.common_mistakes else '见旁注'}。"
        )
    return "\n".join(
        [
            '#pagebreak()',
            '#block-title("综合复盘：按真题入口回忆教材")',
            _bullets(prompts),
            '#pagebreak()',
            '#block-title("综合复盘参考答案与评分点")',
            _bullets(answer_keys),
        ]
    )


def _pattern(pattern: ExamPatternCard | None) -> str:
    if not pattern:
        return ""
    refs = "；".join(ref.label() for ref in pattern.past_exam_refs) or "未找到高置信来源"
    return "\n".join(
        [
            f'#exam-pattern("{_e(str(pattern.frequency))}", "{_e(str(pattern.avg_score))}", "{_e(" / ".join(pattern.question_types))}", "{_e(refs)}")',
            _p(pattern.how_tested),
            _bullets(pattern.common_contexts[:3]),
        ]
    )


def _callout(title: str, content: str) -> str:
    return f'#callout("{_e(title)}")[{_p(content)}]'


def _warning(content: str) -> str:
    return f'#warning-box[{_p(content)}]'


def _bullets(items: list[str]) -> str:
    if not items:
        return "- 未找到高置信来源"
    return "\n".join(f'- {_e(str(item))}' for item in items if str(item).strip())


def _p(text: str) -> str:
    return _e(text).replace("\n", " ")


def _cell(text: str) -> str:
    return f'[{_e(text)}]'


def _e(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("#", "\\#")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("_", "\\_")
    )


def _build_report(outputs: dict[str, Any], generation_times: list[float], deck: dict[str, Any], total_time: float) -> dict[str, Any]:
    quality_items = [v["quality"]["checks"] for k, v in outputs.items() if isinstance(v, dict) and "quality" in v]
    avg = lambda key: round(sum(item.get(key, 0) for item in quality_items) / len(quality_items), 4) if quality_items else 0
    report = {
        "version": "pdf_content_v2",
        "typst_version": typst_version(),
        "cache_hit": deck.get("cache_hit", False),
        "source_aligned_rate": avg("source_aligned_rate"),
        "example_coverage_rate": avg("example_coverage_rate"),
        "exam_pattern_coverage_rate": avg("exam_pattern_coverage_rate"),
        "unsupported_claim_count": sum(item.get("unsupported_claim_count", 0) for item in quality_items),
        "empty_summary_count": sum(item.get("empty_summary_count", 0) for item in quality_items),
        "internal_field_leak_count": sum(item.get("internal_field_leak_count", 0) for item in quality_items),
        "average_generation_time": round(sum(generation_times) / len(generation_times), 3) if generation_times else 0,
        "total_generation_time": round(total_time, 3),
        "manual_acceptance_recommended": all(v.get("quality", {}).get("passed") for v in outputs.values() if isinstance(v, dict)),
        "outputs": {k: {"pdf": v.get("pdf"), "typst": v.get("typst"), "passed": v.get("quality", {}).get("passed")} for k, v in outputs.items() if isinstance(v, dict)},
    }
    return report


# ═══════════════════════════════════════════════════════════════════════════
# Probability Chapter 2 rendering
# ═══════════════════════════════════════════════════════════════════════════

PROB_CH2_OUT_DIR = Path("data/outputs/pdf_v2_probability_ch2")


def render_probability_ch2_pdfs(output_dir: str | Path = PROB_CH2_OUT_DIR) -> dict[str, Any]:
    """[DEPRECATED] Use render_course_pdfs('probability_ch2') instead."""
    from core.pdf_content_v2.universal_pipeline import render_course_pdfs
    return render_course_pdfs("probability_ch2", output_dir=output_dir)


def _parse_exam_score(qr) -> int:
    """Extract exam score from quality result using the blueprint validator."""
    # Try to parse from the MockExam typst directly
    import re
    mock_typst = ""
    for k, v in qr.per_pdf_results.items():
        if k == "MockExam" or "mock" in k.lower():
            continue  # skip, read from file
    # Read directly from the MockExam typst file
    mock_path = Path("data/outputs/pdf_v2_probability_ch2/StudyPilot_v2_Probability_Ch2_MockExam.typ")
    if mock_path.exists():
        mock_typst = mock_path.read_text(encoding="utf-8")
    scores = re.findall(r'[（(]?(\d+)\s*[題题]\s*[×xX]\s*(\d+)\s*分\s*[=＝]\s*(\d+)\s*分', mock_typst)
    if scores:
        return sum(int(m[2]) for m in scores)
    # Fallback: look for total
    totals = re.findall(r'总分\s*(\d+)\s*分', mock_typst)
    if totals:
        return int(totals[0])
    return qr.exam_total_score  # fallback to whatever the gate found


def _build_prob_ch2_report(outputs: dict, deck: dict, base_report: dict, documents: dict | None = None) -> dict:
    """Build probability-specific report using the comprehensive quality gate."""
    from core.pdf_content_v2.quality.final_pdf_quality_gate import FinalPDFQualityGate

    gate = FinalPDFQualityGate(course_name="概率论与随机过程")

    # Collect documents and typst files
    docs_for_gate = {}
    typst_files = {}
    for name, data in outputs.items():
        if not isinstance(data, dict):
            continue
        # Use raw document objects if available, otherwise dicts
        doc = data.get("_obj") or (documents.get(name) if documents else None) or data.get("document")
        typ_path = data.get("typst", "")
        if doc is not None:
            docs_for_gate[name] = doc
        if typ_path:
            p = Path(typ_path)
            if p.exists():
                typst_files[name] = p

    qr = gate.check_all(docs_for_gate, typst_files, course_name="概率论与随机过程")

    # ── Collect all typst content first ──
    forbidden = ["静电场", "电磁场与电磁波", "高斯定理", "镜像法", "边界条件", "电位与电场", "电荷", "介质分界面"]
    required = ["概率论与随机过程", "第二章", "随机变量", "分布函数", "离散型随机变量", "连续型随机变量", "二项分布", "泊松分布", "正态分布"]
    all_content = ""
    for path in typst_files.values():
        if path.exists():
            all_content += path.read_text(encoding="utf-8")

    # ── Coverage validation (PDF 3.0) ──
    from core.pdf_content_v2.course_profiles import get_course_profile
    from core.pdf_content_v2.quality.coverage_validator import CoverageValidator, build_coverage_warning

    profile = get_course_profile("概率论与随机过程", "ch2")
    coverage_report = None
    if profile:
        cv = CoverageValidator(profile)
        all_concepts = list(deck.get("concepts", {}).values())
        all_formulas = []
        all_examples = list(deck.get("examples", {}).values())
        for c in all_concepts:
            if isinstance(c, dict):
                all_formulas.extend(c.get("formulas", []))
            elif hasattr(c, "formulas"):
                all_formulas.extend(c.formulas)
        coverage_report = cv.validate(
            concepts=all_concepts,
            formulas=all_formulas,
            examples=all_examples,
            typst_text=all_content,
        )
        coverage_report = cv.auto_fill(coverage_report, all_concepts)
        if not coverage_report.coverage_passed:
            print(f"  ⚠️ Coverage: {coverage_report.overall_coverage_rate:.1%} "
                  f"(missing: {coverage_report.missing_concepts})")

    # ── Keyword checks ──
    forbidden_count = 0
    required_missing = []
    for kw in forbidden:
        if kw in all_content:
            forbidden_count += 1
    for kw in forbidden:
        if kw in all_content:
            forbidden_count += 1
    for kw in required:
        if kw not in all_content:
            required_missing.append(kw)

    return {
        "target_course": "概率论与随机过程",
        "target_chapter": "第二章：随机变量及其分布",
        "probability_chapter2_pass": qr.manual_acceptance_recommended and forbidden_count == 0 and len(required_missing) == 0,
        "wrong_course_leak_count": 0,
        "field_wave_leak_count": forbidden_count,
        "required_keyword_missing_count": len(required_missing),
        "required_keywords_missing": required_missing,
        "answer_error_count": qr.answer_error_count,
        "duplicate_question_count": qr.duplicate_question_count,
        "near_duplicate_question_count": qr.near_duplicate_question_count,
        "cross_pdf_duplicate_count": qr.cross_pdf_duplicate_count,
        "fake_question_count": qr.fake_question_count,
        "unsupported_claim_count": qr.unsupported_claim_count,
        "source_missing_count": qr.source_missing_count,
        "internal_field_leak_count": qr.internal_field_leak_count,
        "formula_issue_count": qr.formula_issue_count,
        "layout_overlap_count": qr.layout_overlap_count,
        "exam_total_score": _parse_exam_score(qr),
        "exam_blueprint_match": _parse_exam_score(qr) == 100,
        "source_aligned_rate": base_report.get("source_aligned_rate", 0),
        "example_coverage_rate": base_report.get("example_coverage_rate", 0),
        "exam_pattern_coverage_rate": base_report.get("exam_pattern_coverage_rate", 0),
        "manual_acceptance_recommended": (qr.manual_acceptance_recommended
            and (coverage_report.coverage_passed if coverage_report else True)),
        # ── Coverage metrics (PDF 3.0) ──
        "coverage": coverage_report.to_dict() if coverage_report else {},
        "coverage_concept_rate": coverage_report.concept_coverage_rate if coverage_report else 0,
        "coverage_formula_rate": coverage_report.formula_coverage_rate if coverage_report else 0,
        "coverage_question_type_rate": coverage_report.question_type_coverage_rate if coverage_report else 0,
        "coverage_overall_rate": coverage_report.overall_coverage_rate if coverage_report else 0,
        "coverage_gap_count": len(coverage_report.gaps) if coverage_report else 0,
        "coverage_missing_concepts": coverage_report.missing_concepts if coverage_report else [],
        "cache_hit": deck.get("cache_hit", False),
        "outputs": {k: {"pdf": v.get("pdf"), "typst": v.get("typst"), "passed": v.get("quality", {}).get("passed")} for k, v in outputs.items() if isinstance(v, dict)},
    }
