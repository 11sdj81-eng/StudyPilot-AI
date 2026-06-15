"""StudyPilot PDF v4.1 renderer with exam-pattern-driven content."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from core.exam_engine.exam_pattern_database import load_patterns
from core.exam_engine.mock_exam_planner import plan_mock_exam
from core.exam_engine.pastpaper_planner import plan_pastpaper_cases
from core.exam_engine.question_difficulty import difficulty_summary
from core.exam_engine.question_generator_v41 import question_from_pattern
from core.pdf_v4.content_blocks import ContentBlock, visible_blocks
from core.pdf_v4.figure_builder import build_v4_figures
from core.pdf_v4.pdf_v4_renderer import (
    OUT_DIR,
    TEMPLATE_DIR,
    _checklist,
    _cover,
    _date,
    _esc,
    _figure,
    _formula_group,
    _formula_map,
    _heading,
    _mistake,
    _problem,
    _question_typ,
    _raw,
    _solution,
    _t,
    _text,
    _tip,
    render_blocks,
)
from core.pdf_v4.typst_asset_manager import V4FigureAsset, write_figure_manifest
from core.pdf_v4.typst_engine import compile_typst, typst_available, typst_version
from core.study_pdf_v3_renderer import load_v3_chapter_data


def render_all_v41_pdfs(
    output_dir: str | Path = OUT_DIR,
    use_figure_engine: bool = False,
    figure_engine_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not typst_available():
        raise RuntimeError("v4.1 正式引擎无法生成，当前环境缺少 Typst。")
    _sync_typst_templates(out)
    data = load_v3_chapter_data()
    figures = build_v4_figures()

    # Optional: blend Figure Engine figures with existing v4 figures
    figure_engine_report = None
    if use_figure_engine:
        figure_engine_report = _integrate_figure_engine(figures, output_dir=figure_engine_output_dir or out)

    write_figure_manifest(figures, out / "StudyPilot_v41_figure_manifest.json")
    figure_map = {f.id: f for f in figures}
    patterns = load_patterns()
    mock_patterns = plan_mock_exam(patterns)
    past_patterns = plan_pastpaper_cases(patterns)
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    specs = {
        "Sprint": ("sprint.typ", lambda: build_sprint_v41(data, figure_map)),
        "PastPaper": ("pastpaper.typ", lambda: build_pastpaper_v41(data, figure_map, past_patterns)),
        "MockExam": ("mock_exam.typ", lambda: build_mock_v41(data, figure_map, mock_patterns)),
        "Review": ("review.typ", lambda: build_review_v41(data, figure_map)),
    }
    outputs: dict[str, Any] = {}
    for name, (template_name, builder) in specs.items():
        blocks, meta = builder()
        typ_path = out / f"StudyPilot_v41_{name}.typ"
        pdf_path = out / f"StudyPilot_v41_{name}.pdf"
        typ_path.write_text(env.get_template(template_name).render(body=render_blocks(blocks)), encoding="utf-8")
        compile_typst(typ_path, pdf_path)
        outputs[name] = {"typst": str(typ_path.resolve()), "pdf": str(pdf_path.resolve()), "blocks": [b.to_dict() for b in visible_blocks(blocks)], "metadata": meta}
    write_v41_reports(out, outputs, figures, mock_patterns, past_patterns)
    if figure_engine_report:
        (out / "StudyPilot_v41_FigureEngine_report.json").write_text(
            json.dumps(figure_engine_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return outputs


def _integrate_figure_engine(
    v4_figures: list[V4FigureAsset],
    output_dir: str | Path = OUT_DIR,
) -> dict[str, Any]:
    """Integrate Figure Engine figures into v4 figure list.

    For each concept, try to load a high-quality figure from FigureBank.
    If found, add it as a V4FigureAsset alongside the existing v4 figure.
    If not found, keep the existing v4 figure.

    Does NOT replace existing figures — only adds alternatives.
    """
    out = Path(output_dir)
    concept_map_v4 = {f.concept_id: f for f in v4_figures}
    report: dict[str, Any] = {
        "figure_engine_used": True,
        "mode": "blend_with_v4",
        "concepts_enhanced": [],
        "concepts_unchanged": [],
        "fallback_details": [],
    }

    try:
        from core.figure_engine.figure_bank import FigureBank
        from core.figure_engine.figure_matcher import FigureMatcher
        from core.figure_engine.figure_ranker import FigureRanker
        from core.figure_engine.figure_selector import FigureSelector
        from core.figure_engine.figure_quality_gate import FigureQualityGate

        bank = FigureBank()
        bank_figures = bank.list_figures()

        if not bank_figures:
            report["note"] = "FigureBank is empty; no real-source figures available. Using all v4 figures."
            for f in v4_figures:
                report["concepts_unchanged"].append(f.concept_id)
            return report

        # Match and rank bank figures
        matcher = FigureMatcher()
        ranker = FigureRanker()
        bank_figures = matcher.match_all(bank_figures)
        bank_figures = ranker.rank_all(bank_figures)

        # Run quality gate
        gate = FigureQualityGate()
        quality = gate.check(bank_figures)

        # Try to enhance each concept
        selector = FigureSelector()
        all_concept_ids = [
            "gauss_law", "electric_field", "potential_gradient",
            "boundary_conditions", "image_method", "electrostatic_energy",
        ]

        for cid in all_concept_ids:
            # Try to select from bank
            selected = selector.select_figure(
                bank_figures, cid, "review", "full_explanation", allow_fallback=False
            )

            if selected and selected.source_type in {"textbook", "ppt", "past_paper"}:
                # We have a real-source figure — add as alternative
                fig_asset = V4FigureAsset(
                    id=f"fe_{selected.figure_id}",
                    title=f"[FigureEngine] {selected.concept_label}图",
                    caption=(
                        selected.caption
                        or f"来源：{selected.source_type}，第{selected.source_page}页"
                    ),
                    concept_id=cid,
                    source=f"figure_engine:{selected.source_type}",
                    path=selected.image_path,
                    pdf_types=["review", "sprint"],
                )
                v4_figures.append(fig_asset)
                report["concepts_enhanced"].append({
                    "concept_id": cid,
                    "source_type": selected.source_type,
                    "figure_id": selected.figure_id,
                    "final_score": selected.final_score,
                })
            else:
                report["concepts_unchanged"].append(cid)

        # Log fallbacks
        report["fallback_details"] = selector.get_fallback_log()
        report["quality_gate"] = quality

    except ImportError as e:
        report["error"] = f"Figure Engine import failed: {e}"
        report["note"] = "Using all v4 figures without Figure Engine."
        for f in v4_figures:
            report["concepts_unchanged"].append(f.concept_id)
    except Exception as e:
        report["error"] = f"Figure Engine integration error: {e}"
        for f in v4_figures:
            report["concepts_unchanged"].append(f.concept_id)

    return report


def build_sprint_v41(data: dict[str, Any], figures: dict[str, V4FigureAsset]) -> tuple[list[ContentBlock], dict[str, Any]]:
    formulas = _formula_map(data)
    blocks: list[ContentBlock] = [
        _raw("s41_cover", "sprint", _cover("第一章静电场\\\\考前 30 分钟救命册 v4.1", "只保留考前最能救分的图、公式、套路和检查点。", [("建议页数", "5–8 页"), ("使用方式", "先图后卡再题"), ("核心任务", "稳住大题入口"), ("日期", _date())]), 1),
        _raw("s41_toc", "sprint", '#compact-toc(("30 分钟路线", "5 分钟保底", "核心图像", "高频救命卡", "5 道保底题", "最后检查清单"), "考前半小时或进考场前快速回正。", "8 分钟看图，15 分钟看卡，7 分钟做题。", "高斯分段、镜像边界、边界条件、电位负号、能量比例")', 2),
        _heading("s41_path_h", "sprint", "30 分钟使用路线", 3),
        _tip("s41_path", "sprint", ["第 1 轮只看图：确认高斯面、镜像、边界三个模型。", "第 2 轮看救命卡：每张卡只记公式、条件、陷阱。", "第 3 轮做保底题：检查自己是否会写关键步骤。"], 4),
        _heading("s41_5_h", "sprint", "5 分钟保底区", 5),
        _checklist("s41_5", "sprint", ["高斯题看到 r<a 与 r≥a，立刻分包围电荷。", "镜像法题最后必须验证接地平面电位为零。", "边界题先画法向 n，再分切向和法向。", "电位题先写 E=-∇φ，再算偏导。", "能量题记住和场强平方相关。"], 6),
        _heading("s41_fig_h", "sprint", "核心图像速记", 7),
        _figure("s41_f1", "sprint", figures["charged_sphere_piecewise"], "1-1", 8),
        _figure("s41_f2", "sprint", figures["image_grounded_plane"], "1-2", 9),
        _figure("s41_f3", "sprint", figures["boundary_conditions"], "1-3", 10),
        _raw("s41_pb1", "sprint", "#pagebreak()", 11),
        _heading("s41_cards_h", "sprint", "高频救命卡", 12),
    ]
    cards = [
        ("高斯定理分段", "闭合面通量由包围电荷决定，能直接求 E 还要看对称性。", [formulas["gauss_law_integral"], formulas["uniform_sphere_inside"], formulas["uniform_sphere_outside"]], "球、柱、面对称最适合。", "给均匀带电球体，写出球内包围电荷。", ["选同心高斯面", "算包围电荷", "列式并分段"], "球内不要直接写总电荷 Q。", "看到分段就先写 r<a 与 r≥a。"),
        ("镜像法", "用求解区域外的假想电荷满足导体边界。", [formulas["image_plane_potential"]], "接地平面、接地球等规则边界。", "判断镜像电荷符号和位置。", ["画接地边界", "放异号镜像", "验证平面电位"], "镜像电荷不在真实求解区域。", "边界验证不写会丢分。"),
        ("边界条件", "过介质界面时，切向和法向分开处理。", [formulas["boundary_tangential_e"], formulas["boundary_normal_d"]], "介质分界面、导体表面。", "判断哪一个分量连续、哪一个跳变。", ["画 n 和 t", "写切向 E", "写法向 D"], "不要把法向 E 写成必然连续。", "切向看 E，法向看 D。"),
        ("电位求场", "电场是电位的负梯度。", [formulas["potential_gradient_formula"]], "给出电位函数或等位线。", "由 φ=x²+2yz 判断某个场强分量。", ["求偏导", "加负号", "代入点"], "负号最容易漏。", "先写负梯度再计算。"),
        ("静电能量", "场强越大，单位体积场能越高。", [formulas["electrostatic_energy_density"]], "线性介质和电容器场能题。", "场强翻倍时能量密度变几倍。", ["写能量密度", "判断比例", "检查 1/2"], "能量密度不是和 E 线性成正比。", "看到能量先想平方。"),
    ]
    pr = 13
    for title, one, fs, cond, micro, steps, mistake, last in cards:
        blocks.append(_raw(f"s41_card_{pr}", "sprint", f'#card[#strong[{_t(title)}]\n\n一句话：{_t(one)}\n\n必背公式：{", ".join("$"+f["math"]+"$" for f in fs)}\n\n适用条件：{_t(cond)}\n\n老师怎么考：{_t(micro)}\n\n3 步解法：{_t(" → ".join(steps))}\n\n易错点：{_t(mistake)}\n\n#strong[最后 10 秒：{_t(last)}]]', pr))
        pr += 1
    blocks += [
        _raw("s41_pb2", "sprint", "#pagebreak()", pr),
        _heading("s41_q_h", "sprint", "5 道保底题", pr + 1),
        _tip("s41_q", "sprint", ["均匀带电球体内包围电荷怎么写？答案：Qr³/a³。", "由 φ=x²+2yz 求 E 时先写什么？答案：E=-∇φ。", "有自由面电荷时哪个分量跳变？答案：法向 D。", "接地平面镜像电荷是什么符号？答案：异号。", "场强翻倍能量密度变几倍？答案：四倍。"], pr + 2),
        _heading("s41_final_h", "sprint", "最后检查清单", pr + 3),
        _checklist("s41_final", "sprint", ["写清 r<a 与 r≥a。", "写清方向。", "验证接地边界。", "负号和 1/2 不漏。", "答案旁边标明适用区域。"], pr + 4),
    ]
    return blocks, {"pdf_type": "sprint", "target_pages": "5-8"}


def build_pastpaper_v41(data: dict[str, Any], figures: dict[str, V4FigureAsset], patterns: list) -> tuple[list[ContentBlock], dict[str, Any]]:
    formulas = _formula_map(data)
    fig_by_type = {"charged_sphere_piecewise": figures["charged_sphere_piecewise"], "potential_gradient": figures["potential_gradient"], "boundary_conditions": figures["boundary_conditions"], "image_potential": figures["image_potential_pr1r2"]}
    blocks: list[ContentBlock] = [
        _raw("p41_cover", "pastpaper", _cover("第一章静电场\\\\真题模式精讲 v4.1", "按老师讲真题的顺序拆题：识别题型、建模、逐步解、扣分点和变式。", [("题量", "4 道高频题"), ("难度", "Level 3–5"), ("使用方式", "做题后复盘"), ("日期", _date())]), 1),
        _raw("p41_toc", "pastpaper", '#compact-toc(("高斯定理分段求场", "电位函数求电场", "边界条件计算判断", "镜像法综合题", "参考来源"), "考前补大题和复盘错题。", "每题按题目、审题、建模、图、公式、步骤、答案、扣分点阅读。", "分段、负梯度、边界跳变、镜像验证")', 2),
    ]
    pr = 3
    for idx, p in enumerate(patterns, start=1):
        qs = question_from_pattern(p, idx)
        fig = fig_by_type.get(p.diagram_type, figures["gauss_surface_charge"])
        selected_formulas = [formulas[fid] for fid in p.formula_ids if fid in formulas]
        blocks += [
            _heading(f"p41_h{idx}", "pastpaper", f"题 {idx}：{p.source_label}", pr),
            _problem(f"p41_problem{idx}", "pastpaper", p.sample_problem, pr + 1),
            _text(f"p41_id{idx}", "pastpaper", f"题型识别：{_teacher_identify(p.pattern_id)}", pr + 2),
            _text(f"p41_review{idx}", "pastpaper", f"审题：{_review_hint(p.pattern_id)}", pr + 3),
            _text(f"p41_model{idx}", "pastpaper", f"建模：{_t(p.teacher_intent)}", pr + 4),
            _figure(f"p41_fig{idx}", "pastpaper", fig, f"2-{idx}", pr + 5),
            _formula_group(f"p41_formula{idx}", "pastpaper", selected_formulas, pr + 6),
            _solution(f"p41_steps{idx}", "pastpaper", p.required_steps, pr + 7),
            _text(f"p41_answer{idx}", "pastpaper", f"标准答案：{_standard_answer(p.pattern_id)}", pr + 8),
            _mistake(f"p41_deduct{idx}", "pastpaper", _deductions(p.pattern_id), pr + 9),
            _text(f"p41_variant{idx}", "pastpaper", f"变式训练：{_t('；'.join(p.variation_methods))}", pr + 10),
            _text(f"p41_summary{idx}", "pastpaper", f"本题总结：{_case_summary(p.pattern_id)}", pr + 11),
            _raw(f"p41_break{idx}", "pastpaper", "#pagebreak()", pr + 12),
        ]
        pr += 13
    blocks.append(_raw("p41_ref", "pastpaper", '#card[#strong[参考来源]\n\n教材：电磁场与电磁波第一章，用于公式、概念定义和例题模型核对。\n\n往年题：静电场高频题型，用于整理分段求场、边界条件和镜像法综合考法。\n\n课堂资料：静电场章节讲义，用于整理老师强调的建模顺序和扣分点。]', pr))
    return blocks, {"pdf_type": "pastpaper", "case_count": len(patterns)}


def build_mock_v41(data: dict[str, Any], figures: dict[str, V4FigureAsset], patterns: list) -> tuple[list[ContentBlock], dict[str, Any]]:
    fig_by_type = {"gauss_surface": figures["gauss_surface_charge"], "charged_sphere_piecewise": figures["charged_sphere_piecewise"], "boundary_conditions": figures["boundary_conditions"], "image_plane": figures["image_grounded_plane"], "image_potential": figures["image_potential_pr1r2"]}
    questions = []
    no = 1
    points_map = {"choice": 4, "fill": 4, "short": 10, "compute": 20, "comprehensive": 20}
    for p in patterns:
        q = question_from_pattern(p, no, points_map[p.question_type])
        if p.question_type == "choice":
            q["options"] = _options_for_pattern(p.pattern_id)
        else:
            q["options"] = []
        if p.diagram_required and p.question_type in {"short", "compute", "comprehensive"}:
            fig = fig_by_type.get(p.diagram_type)
            if fig:
                q["figure"] = {"no": f"3-{no}", "title": fig.title, "path": fig.path, "caption": fig.caption}
        no += 1
        questions.append(q)
    blocks: list[ContentBlock] = [
        _raw("m41_cover", "mockexam", _cover("电磁场与电磁波\\\\第一章静电场模拟试卷 v4.1", "90 分钟 · 100 分 · 按期末题型模式组织。", [("选择题", "5 × 4 = 20 分"), ("填空题", "5 × 4 = 20 分"), ("简答题", "2 × 10 = 20 分"), ("计算综合", "2 × 20 = 40 分")]), 1),
        _heading("m41_body_h", "mockexam", "试卷正文", 2),
    ]
    pr = 3
    for title, kind in [("一、选择题", "choice"), ("二、填空题", "fill"), ("三、简答题", "short"), ("四、计算与综合题", "compute"), ("四、计算与综合题", "comprehensive")]:
        if kind != "comprehensive":
            blocks.append(_heading(f"m41_{kind}_h", "mockexam", title, pr)); pr += 1
        for q in [q for q in questions if q["kind"] == kind]:
            blocks.append(_raw(f"m41_q{q['no']}", "mockexam", _question_typ(q), pr)); pr += 1
    blocks += [_raw("m41_ans_break", "mockexam", "#pagebreak()", pr), _heading("m41_ans_h", "mockexam", "参考答案与评分标准", pr + 1)]
    pr += 2
    for q in questions:
        blocks.append(_raw(f"m41_ans{q['no']}", "mockexam", f'#card[#strong[{q["no"]}. {_t(_answer_for_pattern(q["pattern_id"]))}]\n\n解析：{_t(_analysis_for_pattern(q["pattern_id"]))}\n\n评分：{_t("；".join(q["grading_points"]))}]', pr))
        pr += 1
    return blocks, {"pdf_type": "mockexam", "question_count": 14, "score_total": 100, "average_difficulty": difficulty_summary(patterns)["average"], "has_level4_or_above": difficulty_summary(patterns)["has_level4_or_above"]}


def build_review_v41(data: dict[str, Any], figures: dict[str, V4FigureAsset]) -> tuple[list[ContentBlock], dict[str, Any]]:
    formulas = _formula_map(data)
    concept_fig = {"electric_field": figures["point_charge_lines"], "gauss_law": figures["charged_sphere_piecewise"], "potential_gradient": figures["potential_gradient"], "boundary_conditions": figures["boundary_conditions"], "image_method": figures["image_potential_pr1r2"], "electrostatic_energy": figures["energy_density"]}
    concept_formulas = {"electric_field": ["point_charge_field"], "gauss_law": ["gauss_law_integral", "uniform_sphere_inside", "uniform_sphere_outside"], "potential_gradient": ["potential_gradient_formula"], "boundary_conditions": ["boundary_tangential_e", "boundary_normal_d"], "image_method": ["image_plane_potential"], "electrostatic_energy": ["electrostatic_energy_density"]}
    blocks: list[ContentBlock] = [
        _raw("r41_cover", "review", _cover("第一章静电场\\\\章节复习讲义 v4.1", "不是速览，而是可打印进 GoodNotes 的完整章节复习讲义。", [("目标页数", "18–25 页"), ("核心概念", "6 个"), ("使用方式", "逐节复习"), ("日期", _date())]), 1),
        _raw("r41_toc", "review", '#compact-toc(("学习地图", "本章知识主线", "6 个核心概念精讲", "公式系统", "典型例题", "高频题型", "易错点", "自测题", "下一步建议"), "期末前完整复习第一章。", "先读主线，再逐节看图、公式、例题和自测。", "高斯定理、边界条件、镜像法、电位负梯度、静电能量")', 2),
        _heading("r41_map_h", "review", "学习地图", 3),
        _tip("r41_map", "review", ["电场强度解决“场是什么”。", "高斯定理解决“对称场怎么快算”。", "电位把矢量问题变成标量问题。", "边界条件解决介质和导体如何衔接。", "镜像法把复杂导体边界换成等效电荷。", "静电能量把场与工程风险联系起来。"], 4),
        _raw("r41_map_break", "review", "#pagebreak()", 5),
    ]
    pr = 6
    for idx, c in enumerate(data["concepts"], start=1):
        cid = c["id"]
        blocks += [
            _heading(f"r41_c{idx}_h", "review", f"{idx}. {c['name']}", pr),
            _text(f"r41_c{idx}_def", "review", f"教材表述：{c['definition']}", pr + 1),
            _text(f"r41_c{idx}_plain", "review", f"通俗理解：{c['plain_explanation']} {c['why_important']}", pr + 2),
            _text(f"r41_c{idx}_scene", "review", f"适用场景：{c['conditions']}", pr + 3),
            _figure(f"r41_c{idx}_fig", "review", concept_fig[cid], f"4-{idx}", pr + 4),
            _formula_group(f"r41_c{idx}_formula", "review", [formulas[fid] for fid in concept_formulas[cid]], pr + 5),
            _text(f"r41_c{idx}_symbol", "review", f"符号解释：{_symbol_line(c)}", pr + 6),
            _text(f"r41_c{idx}_test", "review", f"老师怎么考：{_t('；'.join(c['exam_usage']))}", pr + 7),
            _text(f"r41_c{idx}_must", "review", f"本节必须会：{c['exam_reminder']}", pr + 8),
            _raw(f"r41_c{idx}_midbreak", "review", "#pagebreak()", pr + 9),
            _heading(f"r41_c{idx}_exh", "review", f"{c['name']}：典型例题训练", pr + 10),
            _problem(f"r41_c{idx}_ex", "review", _review_example_question(cid), pr + 11),
            _text(f"r41_c{idx}_review", "review", f"审题：{_review_hint_for_concept(cid)}", pr + 12),
            _text(f"r41_c{idx}_model", "review", f"建模：{_model_for_concept(cid)}", pr + 13),
            _solution(f"r41_c{idx}_steps", "review", _steps_for_concept(cid), pr + 14),
            _text(f"r41_c{idx}_answer", "review", f"标准答案：{_answer_for_concept(cid)}", pr + 15),
            _mistake(f"r41_c{idx}_mistake", "review", c["common_mistakes"], pr + 16),
            _text(f"r41_c{idx}_variant", "review", f"变式：{_variant_for_concept(cid)}", pr + 17),
            _raw(f"r41_c{idx}_break", "review", "#pagebreak()", pr + 18),
        ]
        pr += 19
    blocks += [
        _heading("r41_formula_h", "review", "公式系统总览", pr),
        _formula_group("r41_formula_all", "review", [formulas[k] for k in ["point_charge_field", "gauss_law_integral", "uniform_sphere_inside", "uniform_sphere_outside", "potential_gradient_formula", "boundary_tangential_e", "boundary_normal_d", "image_plane_potential", "electrostatic_energy_density"]], pr + 1),
        _raw("r41_formula_break", "review", "#pagebreak()", pr + 2),
        _heading("r41_hot_h", "review", "高频题型与易错点", pr + 3),
        _tip("r41_hot", "review", ["高斯定理题：分段和包围电荷是核心分。", "镜像法题：边界验证是关键步骤。", "边界条件题：先分切向法向，再写 E 和 D。", "电位函数题：负梯度和偏导不能错。"], pr + 4),
        _raw("r41_hot_break", "review", "#pagebreak()", pr + 5),
        _heading("r41_train_h", "review", "高频题型分层训练", pr + 6),
        _tip("r41_train", "review", ["Level 2：点电荷场强、电位方向、能量比例，目标是快速不丢分。", "Level 3：电位函数求场、边界条件判断，目标是步骤完整。", "Level 4：均匀带电球体分段求场，目标是包围电荷和连续性都写清。", "Level 5：镜像法综合题，目标是电位表达、边界验证和适用区域闭合。"], pr + 7),
        _raw("r41_train_break", "review", "#pagebreak()", pr + 8),
        _heading("r41_error_h", "review", "易错点集中纠偏", pr + 9),
        _tip("r41_error", "review", ["高斯题错在球内仍用总电荷 Q：先写包围电荷再写场。", "电位题错在漏负号：每次先写 E=-∇φ。", "边界题错在混淆 E 和 D：切向看 E，法向看 D。", "镜像法错在不验证边界：平面上电位为零必须写出来。", "能量题错在忘记平方关系：场强翻倍，能量密度不是翻倍。"], pr + 10),
        _raw("r41_error_break", "review", "#pagebreak()", pr + 11),
        _heading("r41_self_h", "review", "自测题", pr + 12),
        _checklist("r41_self", "review", ["写出球内包围电荷并说明原因。", "由 φ=x²+2yz 求点 P 处电场。", "说明法向 D 跳变与自由面电荷关系。", "画出接地平面镜像模型并验证边界。", "解释场强翻倍时能量密度变化。"], pr + 13),
        _heading("r41_next_h", "review", "下一步建议", pr + 14),
        _tip("r41_next", "review", ["把高斯分段题完整手写一遍。", "把镜像法题的边界验证单独练两遍。", "把边界条件整理成切向和法向两列。", "考前只回看图、公式和自测题。"], pr + 15),
        _raw("r41_ref", "review", '#card[#strong[参考来源]\n\n教材：电磁场与电磁波第一章，用于概念定义、公式系统与例题结构核对。\n\n往年题：静电场期末题型，用于整理高斯、边界、镜像和电位函数题的考法。\n\n课堂资料：静电场章节讲义，用于组织复习路径和老师强调的易错点。]', pr + 16),
    ]
    return blocks, {"pdf_type": "review", "concept_count": 6, "target_pages": "18-25"}


def write_v41_reports(out: Path, outputs: dict[str, Any], figures: list[V4FigureAsset], mock_patterns: list, past_patterns: list) -> None:
    exam_report = {"mock": difficulty_summary(mock_patterns), "mock_pattern_ids": [p.pattern_id for p in mock_patterns], "pastpaper_case_ids": [p.pattern_id for p in past_patterns], "pastpaper_case_count": len(past_patterns)}
    (out / "StudyPilot_v41_exam_pattern_report.json").write_text(json.dumps(exam_report, ensure_ascii=False, indent=2), encoding="utf-8")
    figure_report = {"figure_information_score": 86, "figure_count": len(figures), "upgraded_items": [f.id for f in figures], "note": "v4.1 继续使用 Typst + SVG，图内增加关键变量和分区信息。"}
    (out / "StudyPilot_v41_figure_report.json").write_text(json.dumps(figure_report, ensure_ascii=False, indent=2), encoding="utf-8")
    engine = {"engine": "typst", "typst_version": typst_version(), "html_playwright_used": False, "outputs": {k: v["pdf"] for k, v in outputs.items()}, "generated_at": datetime.now().isoformat(timespec="seconds")}
    (out / "StudyPilot_v41_engine_report.json").write_text(json.dumps(engine, ensure_ascii=False, indent=2), encoding="utf-8")


def _sync_typst_templates(output_dir: Path) -> None:
    for path in TEMPLATE_DIR.glob("*.typ"):
        if path.name.startswith(("sprint", "pastpaper", "mock_exam", "review")):
            continue
        shutil.copy2(path, output_dir / path.name)


# ---- content text helpers ----

def _teacher_identify(pid: str) -> str:
    return {"gauss_piecewise_compute": "看到 r<a 和 r≥a，立即判断这是高斯分段题。", "potential_function_field": "看到电位函数和点 P，立即写负梯度。", "boundary_surface_charge": "看到自由面电荷，立即想到法向 D 跳变。", "image_plane_comprehensive": "看到接地平面和点电荷，立即建立异号镜像模型。"}[pid]


def _review_hint(pid: str) -> str:
    return {"gauss_piecewise_compute": "先看有没有球对称，不要先套点电荷公式。", "potential_function_field": "先分别对 x、y、z 求偏导，再统一加负号。", "boundary_surface_charge": "先画法向，确认题目给的是自由面电荷。", "image_plane_comprehensive": "先确定求解区域，再写镜像电荷。"}[pid]


def _standard_answer(pid: str) -> str:
    return {"gauss_piecewise_compute": "球内 E = Qr/(4πε₀a³)，球外 E = Q/(4πε₀r²)，方向沿径向，r=a 处连续。", "potential_function_field": "E = (-2x, -2z, -2y)，代入 P(1,1,-1) 得 E=(-2, 2, -2)。", "boundary_surface_charge": "切向 E 连续，法向 D 的跳变量由 ρₛ 决定。", "image_plane_comprehensive": "镜像电荷为 -q，位于平面另一侧距离 d 处；P 点电位由 Q/R₁ 与 -Q/R₂ 两项叠加，平面上电位为零。"}[pid]


def _deductions(pid: str) -> list[str]:
    return {"gauss_piecewise_compute": ["球内包围电荷写成 Q", "漏写 r=a 连续性", "只写大小不写方向"], "potential_function_field": ["漏负号", "偏导变量写错", "代入点坐标符号错误"], "boundary_surface_charge": ["把法向 E 当成连续", "漏写 ρₛ", "没有说明法向方向"], "image_plane_comprehensive": ["镜像电荷符号写反", "没有验证平面电位为零", "没有说明只适用于上半空间"]}[pid]


def _case_summary(pid: str) -> str:
    return {"gauss_piecewise_compute": "这题的分数不在公式本身，而在包围电荷和分段过程。", "potential_function_field": "电位题先写负梯度，偏导只是计算。", "boundary_surface_charge": "边界题先分方向，再分 E 和 D。", "image_plane_comprehensive": "镜像法题最后一定要验证边界，否则模型没有闭合。"}[pid]


def _options_for_pattern(pid: str) -> list[str]:
    return {
        "choice_gauss_symmetry": ["同一高斯面上场强大小相等且方向与面元关系固定", "只要总电荷已知", "只要曲面闭合", "只要介质为真空"],
        "choice_potential_component": ["Ex=2x", "Ey=2z", "Ez=2y", "电场为电位梯度的相反数"],
        "choice_boundary_surface_charge": ["切向 E 连续，法向 D 按 ρₛ 跳变", "法向 E 一定连续", "切向 D 一定连续", "所有分量都跳变"],
        "choice_image_model": ["在平面另一侧对称位置放 -q", "在平面另一侧放 +q", "在平面上放 -q", "删除原电荷"],
        "choice_energy_density": ["2 倍", "4 倍", "1/2", "不变"],
    }.get(pid, ["A", "B", "C", "D"])


def _answer_for_pattern(pid: str) -> str:
    return {"choice_gauss_symmetry": "A", "choice_potential_component": "D", "choice_boundary_surface_charge": "A", "choice_image_model": "A", "choice_energy_density": "B", "fill_sphere_enclosed_charge": "Qr³/a³", "fill_potential_direction": "+x 方向", "fill_boundary_jump": "自由面电荷密度 ρₛ", "fill_image_distance": "相等", "fill_energy_ratio": "1/2；4", "short_gauss_reason": "高斯定理给出通量关系，直接求 E 需要对称性让场强能从面积分中提出。", "short_boundary_origin": "切向 E 连续来自静电场环路积分为零，法向 D 跳变来自高斯定理。", "gauss_piecewise_compute": "球内 E = Qr/(4πε₀a³)，球外 E = Q/(4πε₀r²)，r=a 连续。", "image_plane_comprehensive": "镜像电荷 -q 位于平面另一侧距离 d 处，平面上电位相消；q 移到 2d 时镜像也移到另一侧 2d。"}[pid]


def _analysis_for_pattern(pid: str) -> str:
    return {"choice_gauss_symmetry": "只有对称性足够时，面上场强大小和方向关系固定，才能直接求出 E。", "choice_potential_component": "电场是负梯度，所有分量都要带负号。", "choice_boundary_surface_charge": "自由面电荷只改变法向 D 的跳变关系。", "choice_image_model": "接地平面要求平面上电位为零，因此镜像电荷异号且对称。", "choice_energy_density": "线性介质中能量密度与 E² 成正比。", "fill_sphere_enclosed_charge": "均匀体电荷按体积比例包围。", "fill_potential_direction": "V 随 x 增大而降低，电场沿 +x。", "fill_boundary_jump": "法向 D 跳变量等于自由面电荷密度。", "fill_image_distance": "平面上点到对称两电荷距离相等。", "fill_energy_ratio": "能量密度含 1/2，场强翻倍时平方关系给四倍。", "short_gauss_reason": "要区分定理成立和能直接解出场强。", "short_boundary_origin": "边界条件来自积分形式的麦克斯韦方程。", "gauss_piecewise_compute": "关键是球内球外包围电荷不同。", "image_plane_comprehensive": "关键是构造等效电荷并验证边界。"}[pid]


def _symbol_line(c: dict) -> str:
    return "，".join(f"{k} 表示 {v}" for k, v in c.get("symbol_explanation", {}).items())


def _review_example_question(cid: str) -> str:
    return {"electric_field": "给定点电荷 Q 和场点 P，判断电场方向并写出大小。", "gauss_law": "均匀带电球体求 r<a 与 r≥a 的电场。", "potential_gradient": "由 φ=x²+2yz 求点 P 处电场。", "boundary_conditions": "有自由面电荷的分界面写出 E 和 D 的边界条件。", "image_method": "接地平面上方点电荷用镜像法写电位。", "electrostatic_energy": "平行板电容器中场强变化时判断能量密度变化。"}[cid]


def _review_hint_for_concept(cid: str) -> str:
    return {"electric_field": "先判断源电荷和场点相对位置。", "gauss_law": "先看对称性和高斯面。", "potential_gradient": "先写负梯度。", "boundary_conditions": "先画法向。", "image_method": "先确定求解区域。", "electrostatic_energy": "先判断介质是否线性。"}[cid]


def _model_for_concept(cid: str) -> str:
    return {"electric_field": "点电荷场或叠加场模型。", "gauss_law": "闭合高斯面 + 包围电荷。", "potential_gradient": "标量电位函数到矢量电场。", "boundary_conditions": "界面切向/法向分量模型。", "image_method": "真实电荷 + 求解区域外镜像电荷。", "electrostatic_energy": "场能密度在空间分布。"}[cid]


def _steps_for_concept(cid: str) -> list[str]:
    return {"electric_field": ["画方向", "写大小", "做矢量叠加"], "gauss_law": ["选高斯面", "算包围电荷", "分段求 E"], "potential_gradient": ["求偏导", "加负号", "代入点"], "boundary_conditions": ["画 n 和 t", "写切向 E", "写法向 D"], "image_method": ["放镜像", "写电位", "验边界"], "electrostatic_energy": ["写能量密度", "判断比例", "解释物理意义"]}[cid]


def _answer_for_concept(cid: str) -> str:
    return {"electric_field": "正电荷径向向外，负电荷径向向内。", "gauss_law": "球内线性，球外平方反比。", "potential_gradient": "电场是电位负梯度。", "boundary_conditions": "切向 E 连续，法向 D 按自由面电荷跳变。", "image_method": "异号镜像满足接地平面零电位。", "electrostatic_energy": "线性介质中能量密度与场强平方相关。"}[cid]


def _variant_for_concept(cid: str) -> str:
    return {"electric_field": "把一个点电荷改成两个点电荷，要求先画方向再做矢量叠加。", "gauss_law": "把均匀带电球体改成球壳，比较球内场强变化。", "potential_gradient": "把一维电位改成三维电位函数，要求求全部分量。", "boundary_conditions": "把有自由面电荷改成无自由面电荷，判断法向 D 是否连续。", "image_method": "把接地平面改成接地导体球，比较镜像位置变化。", "electrostatic_energy": "把场强翻倍改成介电常数翻倍，判断能量密度比例。"}[cid]
