"""Render StudyObjects to Markdown/PDF using the existing v6 engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import OUTPUT_DIR, ROOT_DIR
from core.formula_service import render_formula, render_formula_list, validate_formula_db
from core.pdf_engine_v6 import render_pdf_v6
from core.study_objects import ConceptCard, ExampleCard, ExamPaper, FormulaCard, PastPaperCase, QuestionCard, SprintCard, StudyDocument
from core.symbol_normalizer_v2 import build_symbol_profile_v2, normalize_markdown_v2


def study_document_to_markdown(document: StudyDocument) -> str:
    validate_formula_db(document.formulas)
    parts: list[str] = []
    for section in document.sections:
        parts.append(f"# {section.title}")
        if section.markdown:
            parts.append(section.markdown)
        for block in section.blocks:
            parts.append(_block_to_markdown(block, document))
    return "\n\n".join(p for p in parts if p.strip())


def render_study_document_pdf(document: StudyDocument, output_path: str | Path) -> Path:
    markdown = normalize_markdown_v2(study_document_to_markdown(document), build_symbol_profile_v2(document.course, []))
    md_path = Path(output_path).with_suffix(".md")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    return render_pdf_v6(
        content=markdown,
        output_path=output_path,
        title=document.title,
        course={**document.course, "task_type": document.task_type},
        task_type=document.task_type,
        sources=_sources_for_document(document),
        figures=_figures_for_document(document),
    )


def _block_to_markdown(block: Any, document: StudyDocument) -> str:
    if isinstance(block, SprintCard):
        return _sprint_card(block, document)
    if isinstance(block, PastPaperCase):
        return _past_case(block, document)
    if isinstance(block, ExamPaper):
        return _exam_paper(block, document)
    if isinstance(block, ConceptCard):
        return _concept_card(block, document)
    if isinstance(block, FormulaCard):
        return _formula_row(block)
    if isinstance(block, ExampleCard):
        return _example_card(block, document)
    return str(block)


def _sprint_card(card: SprintCard, document: StudyDocument) -> str:
    concept = document.concepts[card.concept_id]
    formula_text = render_formula_list(card.formula_ids, document)
    symbols = "；".join(f"{k}：{v}" for k, v in card.symbol_notes.items())
    return (
        f"## 救命卡：{concept.name}\n\n"
        f"**教材定义：** {card.definition}\n\n"
        f"**必背公式：** {formula_text}\n\n"
        f"**教材符号解释：** {symbols}\n\n"
        f"**怎么考：** {'；'.join(card.exam_usage)}\n\n"
        f"**经典小题：** {document.examples[card.quick_question_id].question}\n\n"
        f"**小题标准答案：** {card.quick_answer}\n\n"
        f"**关键步骤：** {'；'.join(card.quick_steps)}\n\n"
        f"**易错点：** {'；'.join(card.common_mistakes)}\n\n"
        f"**忘了回看哪里：** {card.review_location}\n\n"
        f"**最后 10 秒提醒：** {card.ten_second_reminder}"
    )


def _past_case(case: PastPaperCase, document: StudyDocument) -> str:
    q = case.question
    formulas = _formula_hint(q.formula_ids, document)
    return (
        f"## 题 {q.id.replace('Q', '')}：{_concept_names(q.concept_ids, document)}\n\n"
        f"**完整题目：** {q.question}\n\n"
        f"**来源可靠性：** {_source_label(case.source_reliability)}；{_user_source(q.source_basis)}\n\n"
        f"**教材定位：** {case.textbook_location}\n\n"
        f"**所用公式：** {formulas}\n\n"
        f"**解题思路：** {'；'.join(q.solution.steps)}\n\n"
        f"**标准答案：** {q.solution.answer}\n\n"
        f"**阅卷扣分点：** {'；'.join(q.solution.rubric or q.solution.common_mistakes)}\n\n"
        f"**易错点：** {'；'.join(q.solution.common_mistakes)}\n\n"
        f"**变式题：** {case.variant_question}\n\n"
        f"**本题学会什么：** {case.takeaway}"
    )


def _exam_paper(exam: ExamPaper, document: StudyDocument) -> str:
    if len(exam.questions) != 14 or sum(q.score for q in exam.questions) != 100:
        raise ValueError("MockExam 必须为 14 题且总分 100")
    choice = [q for q in exam.questions if q.question_type == "choice"]
    blanks = [q for q in exam.questions if q.question_type == "blank"]
    short_answers = [q for q in exam.questions if q.question_type == "short_answer"]
    calculations = [q for q in exam.questions if q.question_type == "calculation"]
    if not (len(choice) == 5 and len(blanks) == 5 and len(short_answers) == 2 and len(calculations) == 2):
        raise ValueError("MockExam 结构必须为 5 选 + 5 填 + 2 简答 + 2 计算")
    parts = [
        "## 试卷说明",
        "；".join(exam.instructions),
        "## 一、选择题",
    ]
    for i, q in enumerate(choice, start=1):
        options = "\n\n".join(f"{chr(64+j)}. {option}" for j, option in enumerate(q.options, start=1))
        parts.append(f"### 题 {i}\n\n{q.question}\n\n{options}\n\n**来源依据：** {_user_source(q.source_basis)}")
    parts.append("## 二、填空题")
    for offset, q in enumerate(blanks, start=6):
        parts.append(f"### 题 {offset}\n\n{q.question}\n\n答：____________________________\n\n**来源依据：** {_user_source(q.source_basis)}")
    parts.append("## 三、简答题")
    for offset, q in enumerate(short_answers, start=11):
        parts.append(f"### 题 {offset}\n\n{q.question}\n\n答题区：\n\n________________________________\n\n________________________________\n\n**来源依据：** {_user_source(q.source_basis)}")
    parts.append("## 四、计算/综合题")
    for offset, q in enumerate(calculations, start=13):
        parts.append(f"### 题 {offset}\n\n{q.question}\n\n**答题区：**\n\n（1）建模依据：__________________\n\n（2）公式选择：__________________\n\n（3）计算过程：__________________\n\n（4）最终结论：__________________\n\n**来源依据：** {_user_source(q.source_basis)}")
    parts.append("## 答案与解析")
    for i, q in enumerate(exam.questions, start=1):
        parts.append(f"**题 {i}：** {q.solution.answer} 关键步骤：{'；'.join(q.solution.steps)}")
    parts.append("## 评分标准")
    parts.append(
        "选择题每题 4 分；填空题每题 4 分；计算题按建模、公式、推导、结论和适用条件给分。\n\n"
        "| 项目 | 分值 | 给分说明 |\n"
        "|------|------|----------|\n"
        "| 建模依据 | 4 | 写清对称性、边界或镜像替代理由 |\n"
        "| 公式选择 | 5 | 公式必须来自本章，符号与适用条件正确 |\n"
        "| 推导过程 | 6 | 分段、代入、边界验证完整 |\n"
        "| 结论说明 | 3 | 写出区域、方向、单位或物理含义 |"
    )
    parts.append("## 题目来源依据")
    rows = [
        "| 题号 | 考查知识点 | 使用公式 | 来源依据 | 难度 |",
        "|------|------------|------------|--------------|------------|",
    ]
    for index, q in enumerate(exam.questions, start=1):
        rows.append(
            f"| 题 {index} | {_concept_names(q.concept_ids, document)} | {_formula_names(q.formula_ids, document)} | {_user_source(q.source_basis)} | {_difficulty_label(q.difficulty)} |"
        )
    parts.append(exam.source_basis + "\n\n" + "\n".join(rows))
    parts.append("## 正式答题卡")
    parts.append(
        "选择题答案：1____ 2____ 3____ 4____ 5____\n\n"
        "填空题答案：6________________ 7________________ 8________________ 9________________ 10________________\n\n"
        "计算题草稿区：\n\n"
        "（1）建模图示：______________________________\n\n"
        "（2）公式与条件：____________________________\n\n"
        "（3）分步推导：______________________________\n\n"
        "（4）最终结论：______________________________"
    )
    return "\n\n".join(parts)


def _concept_card(concept: ConceptCard, document: StudyDocument) -> str:
    examples = [e for e in document.examples.values() if concept.id in e.concept_ids]
    formula_text = render_formula_list(concept.related_formulas, document) if concept.related_formulas else "本节以概念理解为主"
    return (
        f"## 知识点：{concept.name}\n\n"
        f"### 教材原意\n{concept.definition}\n\n"
        f"### 通俗理解\n{concept.plain_explanation}\n\n"
        f"### 为什么重要\n{concept.why_important}\n\n"
        f"### 公式来源\n{formula_text}\n\n"
        f"### 教材例题/同类题\n{examples[0].question if examples else '本节以概念理解为主'}\n\n"
        f"### 常见考法\n{'；'.join(concept.exam_usage)}\n\n"
        f"### 易错点\n{'；'.join(concept.common_mistakes)}"
    )


def _formula_row(formula: FormulaCard) -> str:
    symbols = "；".join(f"{k}：{v}" for k, v in formula.symbol_explanation.items())
    title = formula.display_title or _formula_display_name(formula)
    if not formula.display_text:
        raise ValueError(f"公式为空：{formula.id}")
    return f"| {title} | {formula.display_text} | {formula.conditions} | {symbols} |"


def _example_card(example: ExampleCard, document: StudyDocument) -> str:
    formulas = _formula_hint(example.required_formulas or _formula_ids_for_example(example, document), document)
    title = example.display_title or _example_display_title(example, document)
    return (
        f"## 例题：{title}\n\n"
        f"**题目：** {example.question}\n\n"
        f"**来源：** {_source_label(example.source_type)} · {example.source_ref}\n\n"
        f"**所用公式：** {formulas}\n\n"
        f"**解题思路：** {'；'.join(example.solution.steps)}\n\n"
        f"**标准答案：** {example.solution.answer}\n\n"
        f"**易错点：** {'；'.join(example.solution.common_mistakes)}\n\n"
        f"**变式：** {'；'.join(example.variants)}"
    )


def _formula_hint(formula_ids: list[str], document: StudyDocument) -> str:
    return render_formula_list(formula_ids, document)


def _formula_ids_for_example(example: ExampleCard, document: StudyDocument) -> list[str]:
    ids: list[str] = []
    for concept_id in example.concept_ids:
        if concept_id in document.concepts:
            ids.extend(document.concepts[concept_id].related_formulas)
    return ids


def _concept_names(concept_ids: list[str], document: StudyDocument) -> str:
    return "、".join(document.concepts[cid].name for cid in concept_ids if cid in document.concepts)


def _formula_names(formula_ids: list[str], document: StudyDocument) -> str:
    return "；".join(_formula_display_name(document.formulas[fid]) for fid in formula_ids if fid in document.formulas)


def _formula_display_name(formula: FormulaCard) -> str:
    names = {
        "point_charge_field": "点电荷电场公式",
        "point_charge_potential": "点电荷电位公式",
        "gauss_law_integral": "高斯定理",
        "uniform_sphere_inside": "均匀带电球体内部场强",
        "uniform_sphere_outside": "均匀带电球体外部场强",
        "potential_gradient_formula": "电位负梯度公式",
        "boundary_tangential_e": "切向电场边界条件",
        "boundary_normal_d": "法向电位移边界条件",
        "image_plane_potential": "接地平面镜像法电位",
        "image_sphere_position": "导体球镜像位置",
        "electrostatic_energy_density": "静电能量密度公式",
    }
    return names.get(formula.id, "课程公式")


def _example_display_title(example: ExampleCard, document: StudyDocument) -> str:
    names = _concept_names(example.concept_ids, document)
    return f"{names}典型题" if names else "典型题"


def _source_label(source_type: str) -> str:
    labels = {
        "textbook_example": "教材例题改编",
        "local_similar": "同类题改编",
        "past_paper": "往年题可确认考点",
        "教材例题/真题考法同范围改编": "教材例题与真题考法改编",
    }
    return labels.get(str(source_type or ""), str(source_type or "课程资料来源"))


def _user_source(source_basis: str) -> str:
    text = str(source_basis or "课程资料与本地同类题池")
    text = text.replace("local_question_bank", "本地题库")
    text = text.replace("example_db", "例题库")
    text = text.replace("formula_db", "公式库")
    text = text.replace("exam_pattern_db", "考试题型库")
    text = text.replace("source_basis", "来源依据")
    return text


def _difficulty_label(value: float) -> str:
    if value >= 0.78:
        return "提高"
    if value >= 0.58:
        return "中等"
    return "基础"


def _figures_for_document(document: StudyDocument) -> list[dict]:
    figures: list[dict] = []
    for section in document.sections:
        for block in section.blocks:
            candidates: list[Any] = []
            if isinstance(block, PastPaperCase):
                candidates.append(block.question)
            elif isinstance(block, ExamPaper):
                candidates.extend(block.questions)
            elif isinstance(block, ExampleCard):
                candidates.append(block)
            for item in candidates:
                diagram_id = getattr(item, "diagram_id", "")
                diagram_type = getattr(item, "diagram_type", "")
                diagram = document.diagrams.get(diagram_id) if diagram_id else None
                if not diagram and diagram_type:
                    diagram = next((d for d in document.diagrams.values() if d.diagram_type == diagram_type), None)
                if diagram:
                    if isinstance(item, ExampleCard):
                        visible_id = _example_display_title(item, document)
                    else:
                        visible_id = getattr(item, "display_title", "") or getattr(item, "id", "题目").replace("Q", "题 ")
                    figures.append({
                        "path": str((ROOT_DIR / diagram.path).resolve()),
                        "title": f"{visible_id} {diagram.description}",
                        "caption": diagram.description,
                        "target_section": getattr(item, "id", ""),
                        "source": "diagram_db · programmatic_png",
                        "linked_question_id": visible_id,
                        "linked_knowledge_point": "、".join(getattr(item, "concept_ids", [])),
                        "why_needed": "该图由 QuestionCard/ExampleCard 的 diagram_id 绑定，用于辅助解题。",
                        "diagram_type": diagram.diagram_type,
                        "contains_required_labels": diagram.required_labels,
                        "generated": True,
                    })
    # Deduplicate by linked question and diagram type.
    dedup: dict[tuple[str, str], dict] = {}
    for fig in figures:
        dedup[(fig["linked_question_id"], fig["diagram_type"])] = fig
    return list(dedup.values())[:6]


def _sources_for_document(document: StudyDocument) -> list[dict]:
    return [
        {"filename": "电磁场第一章结构化学习题库", "resource_type": "结构化题库", "page": "概念、公式、例题、考试题型"},
        {"filename": "电磁场与电磁波.pdf", "resource_type": "教材", "page": "第一章 静电场相关片段"},
        {"filename": "2023 电磁场与电磁波 期末试卷.pdf", "resource_type": "往年题", "page": "OCR 可确认考点"},
    ]
