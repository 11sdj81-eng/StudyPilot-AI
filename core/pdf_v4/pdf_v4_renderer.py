"""StudyPilot PDF v4 renderer: structured blocks to Typst PDFs."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from core.pdf_v4.content_blocks import ContentBlock, visible_blocks
from core.pdf_v4.figure_builder import build_v4_figures
from core.pdf_v4.latex_engine import latex_available
from core.pdf_v4.symbol_normalizer import normalize_math, normalize_text
from core.pdf_v4.typst_asset_manager import V4FigureAsset, write_figure_manifest
from core.pdf_v4.typst_engine import compile_typst, typst_available, typst_version
from core.study_pdf_v3_renderer import load_v3_chapter_data


OUT_DIR = Path("data/outputs/pdf_v4")
TEMPLATE_DIR = Path("templates/pdf_v4_typst")


def render_all_v4_pdfs(output_dir: str | Path = OUT_DIR) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not typst_available():
        if latex_available():
            raise RuntimeError("LaTeX fallback is available but not implemented as primary v4 output in this build.")
        raise RuntimeError("v4 正式引擎无法生成，当前环境缺少正式排版工具。")

    data = load_v3_chapter_data()
    figures = build_v4_figures()
    write_figure_manifest(figures, out / "StudyPilot_v4_figure_manifest.json")
    _sync_typst_templates(out)
    figure_map = {f.id: f for f in figures}
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    specs = {
        "Sprint": ("sprint.typ", build_sprint_blocks),
        "PastPaper": ("pastpaper.typ", build_pastpaper_blocks),
        "MockExam": ("mock_exam.typ", build_mock_blocks),
        "Review": ("review.typ", build_review_blocks),
    }
    outputs: dict[str, Any] = {}
    for name, (template_name, builder) in specs.items():
        blocks, meta = builder(data, figure_map)
        body = render_blocks(blocks)
        typ_path = out / f"StudyPilot_v4_{name}.typ"
        pdf_path = out / f"StudyPilot_v4_{name}.pdf"
        typ_path.write_text(env.get_template(template_name).render(body=body), encoding="utf-8")
        compile_typst(typ_path, pdf_path)
        outputs[name] = {
            "typst": str(typ_path.resolve()),
            "pdf": str(pdf_path.resolve()),
            "blocks": [b.to_dict() for b in visible_blocks(blocks)],
            "metadata": meta,
        }
    write_engine_report(out / "StudyPilot_v4_engine_report.json", outputs, figures)
    return outputs


def write_engine_report(path: Path, outputs: dict[str, Any], figures: list[V4FigureAsset]) -> None:
    report = {
        "engine": "typst",
        "typst_available": typst_available(),
        "typst_version": typst_version(),
        "latex_fallback_used": False,
        "html_playwright_used": False,
        "source_asset_note": "教材/试卷/PPT 精确裁剪图尚未接入 v4；本轮使用高质量 SVG 重绘图，未在用户 PDF 中伪装为教材原图。",
        "outputs": {k: v["pdf"] for k, v in outputs.items()},
        "figure_count": len(figures),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _sync_typst_templates(output_dir: Path) -> None:
    for path in TEMPLATE_DIR.glob("*.typ"):
        if path.name.startswith(("sprint", "pastpaper", "mock_exam", "review")):
            continue
        shutil.copy2(path, output_dir / path.name)


def build_sprint_blocks(data: dict[str, Any], figures: dict[str, V4FigureAsset]) -> tuple[list[ContentBlock], dict[str, Any]]:
    formulas = _formula_map(data)
    blocks = [
        _raw("sp_cover", "sprint", _cover("第一章静电场\\\\考前 30 分钟救命册", "短、密、清楚，进考场前也能快速扫读。", [("资料定位", "Sprint v4"), ("建议用时", "30 分钟 / 5 分钟"), ("核心范围", "高斯、镜像、边界、电位、能量"), ("日期", _date())]), 1),
        _raw("sp_toc", "sprint", '#compact-toc(("30 分钟使用路径", "5 分钟保底区", "高频救命卡", "核心图像速记", "保底题", "最后检查清单"), "考前快速回正公式和题型。", "先扫图，再看卡，最后做保底题。", "高斯分段、镜像区域、边界分量、电位负号、能量系数")', 2),
        _heading("sp_path_h", "sprint", "30 分钟使用路径", 3),
        _tip("sp_path", "sprint", ["前 8 分钟：只看三张图，确认题型入口。", "中间 15 分钟：扫高频救命卡，把公式和条件绑在一起。", "最后 7 分钟：做保底题并检查易错点。"], 4),
        _heading("sp_5_h", "sprint", "5 分钟保底区", 5),
        _checklist("sp_5", "sprint", ["高斯题：先判对称性，再算包围电荷。", "镜像题：镜像电荷在求解区域外。", "边界题：切向看 E，法向看 D。", "电位题：负号不能丢。", "能量题：1/2 不能漏。"], 6),
        _heading("sp_fig_h", "sprint", "三类核心图像速记", 7),
        _figure("sp_fig1", "sprint", figures["gauss_surface_charge"], "1-1", 8),
        _figure("sp_fig2", "sprint", figures["image_grounded_plane"], "1-2", 9),
        _figure("sp_fig3", "sprint", figures["boundary_conditions"], "1-3", 10),
        _heading("sp_cards_h", "sprint", "高频救命卡", 11),
    ]
    cards = [
        ("高斯定理", "闭合面通量由包围电荷决定。", [formulas["gauss_law_integral"], formulas["uniform_sphere_inside"]], "有足够对称性时可直接求场。", "最后 10 秒：球内包围电荷不是总电荷。"),
        ("镜像法", "用求解区域外的假想电荷满足边界。", [formulas["image_plane_potential"]], "接地平面、接地球等规则边界。", "最后 10 秒：镜像是假电荷，边界是真条件。"),
        ("边界条件", "过界面先分切向和法向。", [formulas["boundary_tangential_e"], formulas["boundary_normal_d"]], "介质分界面、导体表面。", "最后 10 秒：切向 E，法向 D。"),
        ("电位关系", "电场指向电位降低最快方向。", [formulas["potential_gradient_formula"]], "静电场，由电位函数求场。", "最后 10 秒：负号不能丢。"),
        ("静电能量", "能量储存在电场中。", [formulas["electrostatic_energy_density"]], "线性介质常用。", "最后 10 秒：能量密度有 1/2。"),
    ]
    pr = 12
    for name, line, fs, condition, last in cards:
        body = f'#card[\n#strong[{_t(name)}]  {_t(line)}\n\n必背公式：{", ".join(_math_inline(f["math"]) for f in fs)}\n\n适用条件：{_t(condition)}\n\n#strong[{_t(last)}]\n]'
        blocks.append(_raw(f"sp_card_{pr}", "sprint", body, pr))
        pr += 1
    blocks += [
        _heading("sp_q_h", "sprint", "保底题", pr),
        _tip("sp_q", "sprint", ["球内高斯面包围的是全部 Q 吗？不是，按体积比例。", "电位求电场最常漏什么？负号。", "边界条件口诀是什么？切向看 E，法向看 D。"], pr + 1),
        _heading("sp_final_h", "sprint", "最后检查清单", pr + 2),
        _checklist("sp_final", "sprint", ["分段条件是否写清。", "方向是否说明。", "边界是否验证。", "单位和系数是否检查。"], pr + 3),
    ]
    return blocks, {"pdf_type": "sprint"}


def build_pastpaper_blocks(data: dict[str, Any], figures: dict[str, V4FigureAsset]) -> tuple[list[ContentBlock], dict[str, Any]]:
    formulas = _formula_map(data)
    cases = [
        ("均匀带电球体分段求场", "半径为 a 的均匀带电绝缘球体总电荷为 Q，求 r<a 与 r≥a 的电场。", figures["charged_sphere_piecewise"], [formulas["gauss_law_integral"], formulas["uniform_sphere_inside"], formulas["uniform_sphere_outside"]], ["选同心球面为高斯面。", "球内按体积比例取包围电荷。", "球外包围全部电荷。", "检查 r=a 处连续。"], "球内 E = Qr/(4πε₀a³)，球外 E = Q/(4πε₀r²)。"),
        ("接地平面镜像法", "点电荷 q 位于接地导体平面上方距离 d 处，建立镜像模型并说明边界条件。", figures["image_potential_pr1r2"], [formulas["image_plane_potential"]], ["在平面另一侧放置 -q。", "P 点电位由真实电荷和镜像电荷叠加。", "平面上两距离相等，电位相消。", "说明结果只适用于真实电荷一侧。"], "镜像电荷为 -q，平面上电位为零。"),
        ("介质分界面边界条件", "两介质分界面存在自由面电荷，写出切向电场和法向电位移关系。", figures["boundary_conditions"], [formulas["boundary_tangential_e"], formulas["boundary_normal_d"]], ["先画法向 n 和切向 t。", "切向 E 连续。", "法向 D 按 ρₛ 跳变。", "不要把法向 E 写成必然连续。"], "E₁t = E₂t，D₁n - D₂n = ρₛ。"),
    ]
    blocks = [
        _raw("pp_cover", "pastpaper", _cover("第一章静电场\\\\真题精讲", "像辅导班讲义一样拆题：审题、建模、公式、步骤、扣分。", [("资料定位", "PastPaper v4"), ("题量", "3 道高频题"), ("讲法", "题内闭合讲解"), ("日期", _date())]), 1),
        _raw("pp_toc", "pastpaper", '#compact-toc(("高斯定理计算题", "镜像法综合题", "边界条件题", "参考来源"), "做完题后复盘，或考前补综合题。", "先看题目和图，再看建模步骤，最后对照扣分点。", "高斯分段、接地边界、切向和法向条件")', 2),
    ]
    pr = 3
    for idx, (title, problem, fig, fs, steps, answer) in enumerate(cases, start=1):
        blocks += [
            _heading(f"pp_h{idx}", "pastpaper", f"题 {idx}：{title}", pr),
            _problem(f"pp_p{idx}", "pastpaper", problem, pr + 1),
            _text(f"pp_review{idx}", "pastpaper", "审题：先圈出电荷分布、边界条件和要求量，不要一上来套公式。", pr + 2),
            _figure(f"pp_f{idx}", "pastpaper", fig, f"2-{idx}", pr + 3),
            _formula_group(f"pp_formula{idx}", "pastpaper", fs, pr + 4),
            _solution(f"pp_s{idx}", "pastpaper", steps, pr + 5),
            _text(f"pp_a{idx}", "pastpaper", f"标准答案：{answer}", pr + 6),
            _mistake(f"pp_m{idx}", "pastpaper", ["漏写适用条件", "跳步导致扣过程分", "方向或边界验证不完整"], pr + 7),
            _text(f"pp_v{idx}", "pastpaper", "变式：把球体换成球壳、把接地平面换成导体球、把无面电荷换成有面电荷。", pr + 8),
        ]
        pr += 10
    blocks.append(_references("pp_ref", "pastpaper", pr))
    return blocks, {"pdf_type": "pastpaper"}


def build_mock_blocks(data: dict[str, Any], figures: dict[str, V4FigureAsset]) -> tuple[list[ContentBlock], dict[str, Any]]:
    qs = _mock_questions(figures)
    blocks = [
        _raw("mk_cover", "mockexam", _cover("电磁场与电磁波\\\\第一章静电场模拟试卷", "90 分钟 · 100 分 · 正式模拟卷", [("选择题", "5 × 4 = 20 分"), ("填空题", "5 × 4 = 20 分"), ("简答题", "2 × 10 = 20 分"), ("计算综合", "2 × 20 = 40 分")]), 1),
        _heading("mk_body_h", "mockexam", "试卷正文", 2),
    ]
    pr = 3
    for section_title, kind in [("一、选择题", "choice"), ("二、填空题", "fill"), ("三、简答题", "short"), ("四、计算与综合题", "calc")]:
        blocks.append(_heading(f"mk_{kind}_h", "mockexam", section_title, pr))
        pr += 1
        for q in [q for q in qs if q["kind"] == kind]:
            blocks.append(_raw(f"mk_q{q['no']}", "mockexam", _question_typ(q), pr))
            pr += 1
    blocks += [
        _raw("mk_answer_break", "mockexam", "#pagebreak()", pr),
        _heading("mk_ans_h", "mockexam", "参考答案与评分标准", pr + 1),
    ]
    pr += 2
    for q in qs:
        blocks.append(_raw(f"mk_ans{q['no']}", "mockexam", f'#card[#strong[{q["no"]}. {_t(q["answer"])}]\n\n解析：{_t(q["analysis"])}\n\n评分：{_t("；".join(q["rubric"]))}]', pr))
        pr += 1
    return blocks, {"pdf_type": "mockexam", "question_count": 14, "score_total": 100}


def build_review_blocks(data: dict[str, Any], figures: dict[str, V4FigureAsset]) -> tuple[list[ContentBlock], dict[str, Any]]:
    formulas = _formula_map(data)
    blocks = [
        _raw("rv_cover", "review", _cover("第一章静电场\\\\章节复习讲义", "教材主线 + 辅导书讲法 + 考试导向。", [("资料定位", "Review v4"), ("适合", "打印 / GoodNotes"), ("章节", "第一章 静电场"), ("日期", _date())]), 1),
        _raw("rv_toc", "review", '#compact-toc(("学习地图", "核心概念", "公式系统", "典型例题", "易错点", "自测题"), "完整复习第一章，适合长期保存。", "先读地图，再按概念看图和公式，最后做自测。", "高斯、边界、镜像、电位、能量")', 2),
        _heading("rv_map_h", "review", "学习地图", 3),
        _tip("rv_map", "review", ["先用电场强度建立矢量场概念。", "再用高斯定理处理高对称分布。", "接着用电位降低矢量计算难度。", "遇到介质和导体时检查边界条件。", "镜像法与静电能量负责综合题和工程解释。"], 4),
        _heading("rv_concept_h", "review", "核心概念与图像", 5),
        _figure("rv_f1", "review", figures["point_charge_lines"], "4-1", 6),
        _text("rv_c1", "review", "电场强度是单位正试验电荷受力，关键是方向和叠加。你必须会先画方向，再写大小。", 7),
        _figure("rv_f2", "review", figures["gauss_surface_charge"], "4-2", 8),
        _text("rv_c2", "review", "高斯定理不是只背公式，而是把闭合面通量和包围电荷联系起来。你必须会判断对称性。", 9),
        _figure("rv_f3", "review", figures["potential_gradient"], "4-3", 10),
        _text("rv_c3", "review", "电位像高度，电场指向电位降低最快方向。你必须会由电位函数求电场。", 11),
        _figure("rv_f4", "review", figures["boundary_conditions"], "4-4", 12),
        _text("rv_c4", "review", "边界条件先分切向和法向。你必须会区分 E 与 D 的连续和跳变。", 13),
        _figure("rv_f5", "review", figures["image_potential_pr1r2"], "4-5", 14),
        _text("rv_c5", "review", "镜像法用求解区域外的假想电荷满足边界。你必须会验证接地边界。", 15),
        _figure("rv_f6", "review", figures["energy_density"], "4-6", 16),
        _text("rv_c6", "review", "静电能量储存在场中。你必须会写能量密度并解释高场区域风险。", 17),
        _heading("rv_formula_h", "review", "公式系统", 18),
        _formula_group("rv_formulas", "review", [formulas[k] for k in ["point_charge_field", "gauss_law_integral", "potential_gradient_formula", "boundary_tangential_e", "boundary_normal_d", "image_plane_potential", "electrostatic_energy_density"]], 19),
        _heading("rv_examples_h", "review", "典型例题", 20),
        _problem("rv_ex1", "review", "均匀带电球体求场：先选同心球面，再分球内球外。", 21),
        _solution("rv_ex1s", "review", ["球内包围电荷按体积比例。", "球外包围全部电荷。", "在 r=a 处检查连续性。"], 22),
        _problem("rv_ex2", "review", "接地平面镜像法：先画真实电荷与镜像电荷，再验证平面电位为零。", 23),
        _solution("rv_ex2s", "review", ["镜像电荷异号且对称。", "P 点电位为两项叠加。", "平面上两距离相等所以电位相消。"], 24),
        _heading("rv_self_h", "review", "自测题", 25),
        _checklist("rv_self", "review", ["球内高斯面包围电荷如何写？", "电位求电场为什么有负号？", "有自由面电荷时哪个分量跳变？", "镜像电荷是真实电荷吗？", "能量密度为什么和场强平方有关？"], 26),
        _references("rv_ref", "review", 27),
    ]
    return blocks, {"pdf_type": "review"}


def render_blocks(blocks: list[ContentBlock]) -> str:
    return "\n\n".join(str(block.content) for block in visible_blocks(blocks))


def _raw(id_: str, pdf_type: str, content: str, pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="raw", pdf_type=pdf_type, content=content, render_priority=pr)


def _heading(id_: str, pdf_type: str, text: str, pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="heading", pdf_type=pdf_type, content=f"= {_t(text)}", render_priority=pr)


def _text(id_: str, pdf_type: str, text: str, pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="text", pdf_type=pdf_type, content=_t(text), render_priority=pr)


def _problem(id_: str, pdf_type: str, text: str, pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="problem", pdf_type=pdf_type, content=f'#example[#strong[题目：] {_t(text)}]', render_priority=pr, keep_together=True)


def _solution(id_: str, pdf_type: str, steps: list[str], pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="solution", pdf_type=pdf_type, content=f'#card[#strong[解题步骤]\n#step-list(({_typ_list(steps)}))]', render_priority=pr)


def _mistake(id_: str, pdf_type: str, items: list[str], pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="mistake", pdf_type=pdf_type, content=f'#mistake[#strong[扣分点：] {_t("；".join(items))}]', render_priority=pr)


def _tip(id_: str, pdf_type: str, items: list[str], pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="tip", pdf_type=pdf_type, content=f'#tip[#step-list(({_typ_list(items)}))]', render_priority=pr)


def _checklist(id_: str, pdf_type: str, items: list[str], pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="checklist", pdf_type=pdf_type, content=f'#card[#strong[检查清单]\n#step-list(({_typ_list(items)}))]', render_priority=pr)


def _figure(id_: str, pdf_type: str, fig: V4FigureAsset, no: str, pr: int) -> ContentBlock:
    typst_path = os.path.relpath(fig.path, OUT_DIR)
    return ContentBlock(id=id_, block_type="figure", pdf_type=pdf_type, content=f'#figure-block("{no}", "{_esc(fig.title)}", "{_esc(typst_path)}", "{_esc(fig.caption)}")', render_priority=pr, keep_together=True)


def _formula_group(id_: str, pdf_type: str, formulas: list[dict[str, str]], pr: int) -> ContentBlock:
    parts = []
    for idx, f in enumerate(formulas, start=1):
        parts.append(f'#formula-card("{_esc(f["name"])}", ${f["math"]}$, "{_esc(f["meaning"])}", "{_esc(f["condition"])}", number: "{idx}")')
    return ContentBlock(id=id_, block_type="formula", pdf_type=pdf_type, content="\n".join(parts), render_priority=pr, keep_together=True)


def _references(id_: str, pdf_type: str, pr: int) -> ContentBlock:
    return ContentBlock(id=id_, block_type="reference", pdf_type=pdf_type, content='#card[#strong[参考来源]\n\n教材：电磁场与电磁波第一章，用于概念定义、公式符号、章节范围和典型例题核对。\n\n往年题：静电场相关期末题，用于整理高斯定理、镜像法、边界条件等高频考法和阅卷扣分点。\n\n课堂资料：静电场章节讲义，用于组织复习顺序、老师强调内容和考前回看位置。\n\n整理原则：正文只呈现可用于复习的结论、步骤、图注和来源类型，不展示系统字段、低质量 OCR 摘要或内部检索信息。]', render_priority=pr)


def _cover(title: str, subtitle: str, meta: list[tuple[str, str]]) -> str:
    title = title.replace("\\\\", "\n")
    items = ", ".join(f'(label: "{_esc(k)}", value: "{_esc(v)}")' for k, v in meta)
    return f'#cover("{_esc(title)}", "{_esc(subtitle)}", ({items}))'


def _question_typ(q: dict[str, Any]) -> str:
    opts = ""
    if q.get("options"):
        opts = "\n" + "\n".join(f"{chr(65+i)}. {_t(opt)}" for i, opt in enumerate(q["options"]))
    fig = ""
    if q.get("figure"):
        f = q["figure"]
        typst_path = os.path.relpath(f["path"], OUT_DIR)
        fig = f'\n#figure-block("{f["no"]}", "{_esc(f["title"])}", "{_esc(typst_path)}", "{_esc(f["caption"])}")'
    return f'#card[#strong[{q["no"]}.] {_t(q["question"])} #text(size: 8.8pt)[（{q["points"]} 分）]{opts}{fig}]'


def _mock_questions(figures: dict[str, V4FigureAsset]) -> list[dict[str, Any]]:
    return [
        _q(1, "choice", 4, "球对称电荷分布中，何时可把 E 从高斯面积分中提出？", ["同一球面上场强大小相等且方向与面元关系固定", "只要总电荷已知", "只要半径足够大", "只要介质均匀"], "A", "关键是对称性保证面上场强大小相等。", ["选 A 得 4 分"]),
        _q(2, "choice", 4, "已知电位 φ=x²+2yz，关于电场判断正确的是？", ["电场等于电位梯度", "Ex=-2x", "Ey=-2y", "Ez=-2z"], "B", "电场为负梯度，Ex=-2x。", ["选 B 得 4 分"]),
        _q(3, "choice", 4, "介质界面存在自由面电荷时，正确说法是？", ["法向 D 按 ρₛ 跳变", "法向 E 必连续", "切向 D 必连续", "所有分量都连续"], "A", "法向电位移跳变由自由面电荷决定。", ["选 A 得 4 分"]),
        _q(4, "choice", 4, "接地平面镜像法中，镜像电荷应如何设置？", ["异号且关于平面对称", "同号且关于平面对称", "放在平面上", "放在无穷远"], "A", "异号镜像保证平面电位为零。", ["选 A 得 4 分"]),
        _q(5, "choice", 4, "场强增为 2 倍，线性介质中能量密度约变为？", ["2 倍", "4 倍", "1/2", "不变"], "B", "能量密度与场强平方成正比。", ["选 B 得 4 分"]),
        _q(6, "fill", 4, "均匀带电球体内，高斯面包围电荷与 ____ 成正比。", [], "r³", "包围电荷按体积比例。", ["填 r³ 得 4 分"]),
        _q(7, "fill", 4, "由电位求电场时，电场方向指向电位 ____ 的方向。", [], "降低最快", "负梯度表示下降最快方向。", ["填降低最快得 4 分"]),
        _q(8, "fill", 4, "无自由面电荷时，介质分界面两侧法向 D ____。", [], "连续", "法向 D 的跳变由自由面电荷决定。", ["填连续得 4 分"]),
        _q(9, "fill", 4, "接地平面镜像法中，平面上到真实电荷和镜像电荷的距离 ____。", [], "相等", "距离相等、电荷异号，电位相消。", ["填相等得 4 分"]),
        _q(10, "fill", 4, "静电能量密度公式中最常漏掉的系数是 ____。", [], "1/2", "系数是常见扣分点。", ["填 1/2 得 4 分"]),
        _q(11, "short", 10, "说明高斯定理题先判断对称性的原因。", [], "只有对称性足够时，才能把场强从面积分中提出直接求 E。", "高斯定理总成立，直接求场需要额外对称性。", ["通量关系 3 分", "对称性作用 5 分", "表达 2 分"], _fig_q(figures["gauss_surface_charge"], "3-1")),
        _q(12, "short", 10, "说明切向 E 与法向 D 边界条件的来源。", [], "切向 E 连续来自静电场环路积分为零；法向 D 跳变来自高斯定理。", "要把积分定理和边界条件对应起来。", ["切向来源 4 分", "法向来源 4 分", "表达 2 分"], _fig_q(figures["boundary_conditions"], "3-2")),
        _q(13, "calc", 20, "半径 a 的均匀带电绝缘球体总电荷 Q，求 r<a 与 r≥a 的电场，并检查 r=a 处连续性。", [], "球内 E = Qr/(4πε₀a³)，球外 E = Q/(4πε₀r²)，边界处连续。", "分段计算包围电荷。", ["高斯面 4 分", "包围电荷 6 分", "球内结果 4 分", "球外结果 4 分", "连续性 2 分"], _fig_q(figures["charged_sphere_piecewise"], "3-3")),
        _q(14, "calc", 20, "点电荷 q 位于接地导体平面上方距离 d 处，建立镜像模型并验证边界条件。", [], "在平面另一侧放 -q；平面上两项电位相消，总电位为零。", "镜像模型只用于真实电荷所在半空间。", ["镜像设置 5 分", "电位叠加 5 分", "边界验证 6 分", "适用区域 4 分"], _fig_q(figures["image_grounded_plane"], "3-4")),
    ]


def _q(no: int, kind: str, points: int, question: str, options: list[str], answer: str, analysis: str, rubric: list[str], figure: dict[str, str] | None = None) -> dict[str, Any]:
    return {"no": no, "kind": kind, "points": points, "question": question, "options": options, "answer": answer, "analysis": analysis, "rubric": rubric, "figure": figure}


def _fig_q(fig: V4FigureAsset, no: str) -> dict[str, str]:
    return {"no": no, "title": fig.title, "path": fig.path, "caption": fig.caption}


def _formula_map(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    result = {}
    for f in data["formulas"]:
        result[f["id"]] = {
            "name": normalize_text(f["display_name"]),
            "math": _typst_math(f["id"]),
            "meaning": normalize_text(f.get("user_visible_text", "")),
            "condition": normalize_text(f.get("conditions", "")),
        }
    return result


def _typst_math(formula_id: str) -> str:
    formulas = {
        "point_charge_field": 'upright("E = Q/(4π ε₀ R²) R̂")',
        "gauss_law_integral": 'upright("∫S D·dS = Q")',
        "uniform_sphere_inside": 'upright("E = Qr/(4π ε₀ a³), r<a")',
        "uniform_sphere_outside": 'upright("E = Q/(4π ε₀ r²), r≥a")',
        "potential_gradient_formula": 'upright("E = -∇φ")',
        "boundary_tangential_e": 'upright("E₁t = E₂t")',
        "boundary_normal_d": 'upright("D₁n - D₂n = ρₛ")',
        "image_plane_potential": 'upright("φ = 1/(4π ε₀)(Q/R₁ - Q/R₂)")',
        "electrostatic_energy_density": 'upright("wₑ = 1/2 D·E")',
    }
    return formulas.get(formula_id, 'upright("E = 0")')


def _math_inline(math: str) -> str:
    return f"${math}$"


def _typ_list(items: list[str]) -> str:
    return ", ".join(f"[{_t(item)}]" for item in items)


def _t(text: object) -> str:
    value = normalize_text(text)
    value = value.replace(">=", "大于等于").replace("<=", "小于等于").replace("<", "小于").replace(">", "大于")
    return value.replace("[", "\\[").replace("]", "\\]")


def _esc(text: object) -> str:
    value = normalize_text(text)
    value = value.replace(">=", "大于等于").replace("<=", "小于等于").replace("<", "小于").replace(">", "大于")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _date() -> str:
    return datetime.now().strftime("%Y-%m-%d")
