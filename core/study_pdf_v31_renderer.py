"""StudyPilot PDF v3.1 renderer with design system and asset manager."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.diagram_asset_manager import DiagramAssetManager
from core.diagram_generator_v31 import generate_v31_teaching_assets, write_v31_diagram_catalog
from core.pdf_design_system import css_variables
from core.study_pdf_v3_renderer import load_v3_chapter_data
from core.teaching_asset import TeachingAsset
from core.teaching_asset_manager import TeachingAssetManager


OUTPUT_DIR = Path("data/outputs")
TEMPLATE_DIR = Path("templates/study_pdf_v31")


def render_all_v31_pdfs(output_dir: str | Path = OUTPUT_DIR) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_v3_chapter_data()
    assets = generate_v31_teaching_assets()
    write_v31_diagram_catalog(assets, out / "teaching_asset_manifest.json")
    asset_manager = TeachingAssetManager(assets)
    diagram_manager = DiagramAssetManager(asset_manager)
    env = _env()

    specs = [
        ("Sprint", "sprint.html", build_sprint_context),
        ("PastPaper", "pastpaper.html", build_pastpaper_context),
        ("MockExam", "mock_exam.html", build_mock_exam_context),
        ("Review", "review.html", build_review_context),
    ]
    outputs: dict[str, Any] = {}
    for name, template_name, builder in specs:
        context = builder(data, diagram_manager)
        html_path = out / f"StudyPilot_v31_{name}.html"
        pdf_path = out / f"StudyPilot_v31_{name}.pdf"
        html_path.write_text(env.get_template(template_name).render(**context), encoding="utf-8")
        _print_pdf_with_playwright(html_path, pdf_path)
        outputs[name] = {"html": str(html_path.resolve()), "pdf": str(pdf_path.resolve()), "model": _safe_model(context)}

    asset_manager.export_manifest(out / "teaching_asset_manifest.json")
    diagram_manager.export_usage_report(out / "diagram_usage_report.json")
    return outputs


def build_sprint_context(data: dict[str, Any], dm: DiagramAssetManager) -> dict[str, Any]:
    concepts = _concepts_with_formulas(data)
    diagrams = [
        _asset_to_diagram(dm.select_diagram("gauss_law", "sprint", usage_context="quick_memory"), "S-1"),
        _asset_to_diagram(dm.select_diagram("image_method", "sprint", usage_context="quick_memory"), "S-2"),
        _asset_to_diagram(dm.select_diagram("boundary_conditions", "sprint", usage_context="quick_memory"), "S-3"),
    ]
    cards = []
    for c in concepts:
        cards.append(
            {
                "name": c["name"],
                "one_line": c["plain_explanation"],
                "formulas": c.get("formula_texts", [])[:2] or ["以教材公式表为准"],
                "conditions": c.get("conditions", ""),
                "exam_usage": c.get("exam_usage", []),
                "micro_question": _micro_question(c["id"]),
                "steps": _sprint_steps(c["id"]),
                "mistake": c.get("common_mistakes", ["先看条件"])[0],
                "review_location": c.get("review_location", "教材第一章"),
                "ten_second": c.get("exam_reminder", ""),
            }
        )
    return _base(
        "第一章静电场考前救命册",
        {
            "body_class": "sprint compact",
            "toc": ["如果只剩 5 分钟", "三张速记图", "救命卡", "5 分钟保底题", "参考来源"],
            "reading": {
                "title": "怎么用这份资料",
                "scene": "考试前 30 分钟、进考场前 5 分钟、公式混乱时快速回正。",
                "path": "先看三张图，再扫救命卡，最后做 5 道保底题。",
                "hotspots": "高斯分段、镜像区域、边界条件、电位负号、能量 1/2。",
            },
            "diagrams": [d for d in diagrams if d],
            "cards": cards,
            "rescue_questions": _sprint_rescue_questions(),
            "sources": _sources(False),
        },
    )


def build_pastpaper_context(data: dict[str, Any], dm: DiagramAssetManager) -> dict[str, Any]:
    formula_map = _formula_text_by_concept(data)
    diagram_for_concept = {
        "gauss_law": _asset_to_diagram(dm.select_diagram("gauss_law", "pastpaper", usage_context="exam_case"), "P-1"),
        "image_method": _asset_to_diagram(dm.select_diagram("image_method", "pastpaper", usage_context="exam_case"), "P-2"),
        "boundary_conditions": _asset_to_diagram(dm.select_diagram("boundary_conditions", "pastpaper", usage_context="exam_case"), "P-3"),
    }
    cases = []
    for ex in [e for e in data["examples"] if e["id"] in {"ex_gauss_sphere", "ex_image_plane", "ex_boundary_interface"}]:
        cid = ex["concept_ids"][0]
        cases.append(
            {
                **ex,
                "diagram": diagram_for_concept.get(cid),
                "why_tested": _why_tested(cid),
                "keyword_hint": _keyword_hint(cid),
                "teacher_comment": _teacher_comment(cid),
                "modeling": _modeling(cid),
                "formula_text": "；".join(formula_map.get(cid, [])),
                "takeaway": _takeaway(cid),
            }
        )
    return _base(
        "第一章静电场真题精讲",
        {
            "body_class": "pastpaper",
            "toc": [f"题 {i+1}：{case['display_name']}" for i, case in enumerate(cases)] + ["参考来源"],
            "reading": {
                "title": "老师讲题阅读法",
                "scene": "做完一套卷后复盘，或考前专门补综合题。",
                "path": "先看关键词识别，再看图，最后对照扣分点改自己的解答。",
                "hotspots": "高斯分段、镜像边界验证、边界条件分量识别。",
            },
            "cases": cases,
            "sources": _sources(False),
        },
    )


def build_mock_exam_context(data: dict[str, Any], dm: DiagramAssetManager) -> dict[str, Any]:
    gauss = _asset_to_diagram(dm.select_diagram("gauss_law", "mockexam", question_type="calculation", usage_context="problem_statement"), "M-1")
    image = _asset_to_diagram(dm.select_diagram("image_method", "mockexam", question_type="calculation", usage_context="problem_statement"), "M-2")
    boundary = _asset_to_diagram(dm.select_diagram("boundary_conditions", "mockexam", question_type="short", usage_context="exam_case"), "M-3")
    questions = _mock_questions(gauss, image, boundary)
    sections = {
        "choice": [q for q in questions if q["kind"] == "choice"],
        "fill": [q for q in questions if q["kind"] == "fill"],
        "short": [q for q in questions if q["kind"] == "short"],
        "calc": [q for q in questions if q["kind"] == "calc"],
    }
    return _base(
        "第一章静电场模拟试卷",
        {
            "body_class": "mock",
            "sections": sections,
            "answers": questions,
            "mock_question_count": len(questions),
            "mock_score_total": sum(q["points"] for q in questions),
            "mock_difficulty_score": 82,
        },
    )


def build_review_context(data: dict[str, Any], dm: DiagramAssetManager) -> dict[str, Any]:
    concepts = _concepts_with_formulas(data)
    examples_by_concept = _examples_by_concept(data, dm)
    formula_by_concept = _formulas_by_concept(data)
    diagram_map = {
        "electric_field": _asset_to_diagram(dm.select_diagram("electric_field", "review", usage_context="full_explanation"), "R-1"),
        "potential_gradient": _asset_to_diagram(dm.select_diagram("potential_gradient", "review", usage_context="full_explanation"), "R-2"),
        "electrostatic_energy": _asset_to_diagram(dm.select_diagram("electrostatic_energy", "review", usage_context="full_explanation"), "R-3"),
    }
    blocks = []
    for c in concepts:
        blocks.append(
            {
                "concept": c,
                "diagram": diagram_map.get(c["id"]),
                "formulas": formula_by_concept.get(c["id"], [])[:2],
                "examples": examples_by_concept.get(c["id"], [])[:1],
                "must_know": _must_know(c["id"]),
            }
        )
    return _base(
        "第一章静电场章节复习讲义",
        {
            "body_class": "review",
            "toc": ["知识地图", "核心知识精讲", "公式总表", "自测题", "参考来源"],
            "reading": {
                "title": "长期复习路径",
                "scene": "适合打印、导入 GoodNotes、期末前反复翻。",
                "path": "按知识主线读，每节看公式、图、例题，再做自测回看。",
                "hotspots": "高斯定理、边界条件、镜像法是大题核心；电位和能量是填空与简答高频。",
            },
            "concept_blocks": blocks,
            "formulas": data["formulas"],
            "self_tests": _self_tests_v31(),
            "sources": _sources(False),
        },
    )


def _print_pdf_with_playwright(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1754})
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        try:
            page.wait_for_function("document.body.classList.contains('math-ready')", timeout=5000)
        except Exception:
            pass
        page.pdf(path=str(pdf_path), format="A4", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        browser.close()


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html", "xml"]))


def _base(title: str, extra: dict[str, Any]) -> dict[str, Any]:
    course_name = extra.pop("course_name", None) or "课程资料"
    return {"title": title, "course_name": course_name, "generated_at": datetime.now().strftime("%Y-%m-%d"), "design_css": css_variables(), **extra}


def _asset_to_diagram(asset: TeachingAsset | None, figure_no: str) -> dict[str, Any] | None:
    if not asset:
        return None
    return {"asset_id": asset.id, "figure_no": figure_no, "title": asset.title, "path": asset.path, "caption": asset.caption, "why_needed": asset.why_needed, "source": asset.source}


def _concepts_with_formulas(data: dict[str, Any]) -> list[dict[str, Any]]:
    formula_map = _formula_text_by_concept(data)
    return [{**c, "formula_texts": formula_map.get(c["id"], [])} for c in data["concepts"]]


def _formula_text_by_concept(data: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for f in data["formulas"]:
        result.setdefault(f.get("concept_id", ""), []).append(f["display_text"])
    return result


def _formulas_by_concept(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for f in data["formulas"]:
        result.setdefault(f.get("concept_id", ""), []).append(f)
    return result


def _examples_by_concept(data: dict[str, Any], dm: DiagramAssetManager) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for ex in data["examples"]:
        cid = ex["concept_ids"][0]
        item = {
            **ex,
            "keyword_hint": _keyword_hint(cid),
            "teacher_comment": _teacher_comment(cid),
            "diagram": None,
        }
        result.setdefault(cid, []).append(item)
    return result


def _mock_questions(gauss: dict | None, image: dict | None, boundary: dict | None) -> list[dict[str, Any]]:
    return [
        _q(1, "choice", 4, "某球对称电荷分布中，选半径 r 的球面为高斯面。下列哪种情况下可以把 E 从面积分中提出？", ["场强方向处处沿径向且同一球面上大小相等", "只要电荷总量已知", "只要球面半径足够大", "只要介质为真空"], "A", "能提出面积分的关键是同一高斯面上场强大小相等、方向与面元关系固定。", ["选 A 得 4 分"]),
        _q(2, "choice", 4, "已知 φ=x²+2yz，下列关于电场分量判断正确的是？", ["Ex=2x", "Ey=2z", "Ez=2y", "电场为电位梯度的相反数"], "D", "电场为负梯度，三个分量都要带负号。", ["选 D 得 4 分"]),
        _q(3, "choice", 4, "两介质界面存在自由面电荷时，以下最准确的是？", ["E 的法向分量一定连续", "D 的法向分量按面电荷跳变", "D 的切向分量一定连续", "E 的所有分量都跳变"], "B", "自由面电荷改变法向 D 的边界条件。", ["选 B 得 4 分"]),
        _q(4, "choice", 4, "接地导体平面上方点电荷 q 的镜像问题中，若只关心上半空间电位，正确建模是？", ["在下半空间放 -q", "在下半空间放 +q", "在平面上放 +q", "删除原电荷"], "A", "异号镜像电荷保证导体平面零电位。", ["选 A 得 4 分"]),
        _q(5, "choice", 4, "平行板间电场局部增大到原来的 2 倍，能量密度近似变为原来的多少倍？", ["2 倍", "4 倍", "1/2", "不变"], "B", "能量密度与场强平方成正比。", ["选 B 得 4 分"]),
        _q(6, "fill", 4, "均匀带电球体内，半径 r 的高斯面包围电荷与 ______ 成正比。", [], "r³", "体电荷均匀时，包围电荷按体积比例增长。", ["填 r³ 得 4 分"]),
        _q(7, "fill", 4, "若 V(x)=V0-kx，k>0，则电场方向沿 ______。", [], "+x 方向", "电场为负梯度，因此沿电位下降方向。", ["方向正确 4 分"]),
        _q(8, "fill", 4, "接地平面镜像法中，平面上任一点到原电荷和镜像电荷的距离关系是 ______。", [], "相等", "这保证两项电位大小相等、符号相反。", ["填相等得 4 分"]),
        _q(9, "fill", 4, "无自由面电荷时，介质分界面两侧法向 D 的关系是 ______。", [], "连续", "法向 D 的跳变由自由面电荷决定；无自由面电荷则连续。", ["填连续得 4 分"]),
        _q(10, "fill", 4, "静电能量密度可用场量 D 与 E 的点乘表示，并含有系数 ______。", [], "1/2", "常见漏分点是漏写 1/2。", ["填 1/2 得 4 分"]),
        _q(11, "short", 10, "说明高斯定理题为什么要先判断对称性，并举出一个不能直接用高斯面求 E 的情形。", [], "高斯定理给出闭合面通量关系；只有场在高斯面上具有固定方向和相同大小时才能直接求 E。缺少球、柱或面对称的任意电荷分布通常不能直接提出 E。", "强调定理成立与直接求场不是同一件事。", ["通量关系 3 分", "对称性作用 4 分", "反例 3 分"], gauss),
        _q(12, "short", 10, "结合介质分界面图，说明切向 E 和法向 D 的边界条件分别来自什么物理约束。", [], "切向 E 的连续来自静电场环路积分为零；法向 D 的跳变来自高斯定理，跳变量由自由面电荷密度决定。", "把积分定理和边界条件对应起来。", ["切向来源 4 分", "法向来源 4 分", "表达 2 分"], boundary),
        _q(13, "calc", 20, "半径 a 的均匀带电绝缘球体总电荷为 Q。求 r<a 与 r≥a 的电场，并说明 r=a 处结果是否连续。", [], "球内 E = Qr/(4πε₀a³)，球外 E = Q/(4πε₀r²)，r=a 处两式均为 Q/(4πε₀a²)，连续。", "分段求包围电荷，并在边界处检查连续性。", ["高斯面 4 分", "球内包围电荷 5 分", "球内结果 4 分", "球外结果 4 分", "连续性 3 分"], gauss),
        _q(14, "calc", 20, "点电荷 q 位于接地导体平面上方距离 d 处。建立镜像模型，写出上半空间某点 P 的电位表达思路，并验证平面边界条件。", [], "在平面另一侧对称位置放 -q。P 点电位为真实电荷和镜像电荷电位代数叠加；平面上任一点到两电荷距离相等，贡献相消，总电位为零。", "必须说明结果只适用于上半空间。", ["镜像模型 5 分", "电位叠加 5 分", "边界验证 6 分", "适用区域 4 分"], image),
    ]


def _q(no: int, kind: str, points: int, question: str, options: list[str], answer: str, analysis: str, rubric: list[str], diagram: dict | None = None) -> dict[str, Any]:
    return {"no": no, "kind": kind, "points": points, "question": question, "options": options, "answer": answer, "analysis": analysis, "rubric": rubric, "diagram": diagram}


def _micro_question(cid: str) -> str:
    return {
        "gauss_law": "球内 r<a 时包围电荷是不是总电荷 Q？",
        "image_method": "镜像电荷是真实存在的吗？",
        "boundary_conditions": "有自由面电荷时，哪个法向量跳变？",
        "potential_gradient": "由电位求电场时负号在哪里？",
        "electrostatic_energy": "场强翻倍，能量密度变几倍？",
    }.get(cid, "先判断方向还是先代公式？")


def _sprint_steps(cid: str) -> list[str]:
    return {
        "gauss_law": ["判对称", "选闭合面", "算包围电荷"],
        "image_method": ["画边界", "放镜像", "验零电位"],
        "boundary_conditions": ["分切法", "写条件", "看面电荷"],
    }.get(cid, ["看定义", "选公式", "查单位"])


def _sprint_rescue_questions() -> list[dict[str, str]]:
    return [
        {"question": "球内高斯面包围的是全部 Q 吗？", "answer": "不是，按体积比例取。", "review": "高斯定理救命卡"},
        {"question": "电位求电场最常漏什么？", "answer": "负号。", "review": "电位关系救命卡"},
        {"question": "边界条件口诀是什么？", "answer": "切向看 E，法向看 D。", "review": "边界条件图"},
        {"question": "镜像电荷在哪一侧？", "answer": "真实求解区域外。", "review": "镜像法速记图"},
        {"question": "能量密度和场强是什么关系？", "answer": "与场强平方成正比。", "review": "静电能量救命卡"},
    ]


def _why_tested(cid: str) -> str:
    return {
        "gauss_law": "这类题能同时考对称性、包围电荷和分段表达，是期末计算题的高频模板。",
        "image_method": "镜像法题能检查你是否真正理解边界条件，而不是只会背公式。",
        "boundary_conditions": "边界条件题短但扣分密集，特别容易混淆 E 和 D 的分量。",
    }.get(cid, "该题用于检查基础概念是否能转化为解题步骤。")


def _keyword_hint(cid: str) -> str:
    return {
        "gauss_law": "球对称、均匀带电、求 r 处电场、分 r<a 与 r>a。",
        "image_method": "接地导体、无限大平面、点电荷、电位为零。",
        "boundary_conditions": "介质分界面、自由面电荷、切向、法向。",
        "potential_gradient": "给定电位函数、求电场、等位线。",
    }.get(cid, "先圈出电荷分布、边界条件和要求量。")


def _teacher_comment(cid: str) -> str:
    return {
        "gauss_law": "这题第一眼先不要急着代公式，先看场在你选的面上是否大小相同。",
        "image_method": "镜像法不是魔法，核心是用假电荷把边界条件做出来。",
        "boundary_conditions": "边界条件最怕混写，先画法向，再分切向和法向。",
    }.get(cid, "先建模，再代公式。")


def _modeling(cid: str) -> str:
    return {
        "gauss_law": "同心球面作为高斯面，球内和球外分开处理包围电荷。",
        "image_method": "真实电荷所在半空间为求解区域，另一侧放置异号镜像电荷。",
        "boundary_conditions": "把场量拆成切向和法向，按界面是否有自由面电荷写条件。",
    }.get(cid, "识别物理模型并写出适用条件。")


def _takeaway(cid: str) -> str:
    return {
        "gauss_law": "高斯题的分数主要在高斯面、包围电荷和分段条件。",
        "image_method": "镜像法答案必须验证边界，且必须说明适用区域。",
        "boundary_conditions": "切向 E、法向 D 是边界条件题的核心记忆点。",
    }.get(cid, "把题型入口和公式条件绑定记忆。")


def _must_know(cid: str) -> str:
    return {
        "electric_field": "会判断点电荷电场方向，并知道它是矢量。",
        "gauss_law": "会选高斯面、算包围电荷、写分段答案。",
        "potential_gradient": "会由电位函数求电场，负号不能丢。",
        "boundary_conditions": "会区分切向 E 和法向 D。",
        "image_method": "会画镜像电荷并验证接地边界。",
        "electrostatic_energy": "会写能量密度并解释高场风险。",
    }.get(cid, "会把概念用于题目。")


def _self_tests_v31() -> list[dict[str, str]]:
    return [
        {"question": "为什么球内电场随 r 线性变化？", "answer": "包围电荷随 r³ 变化，高斯面面积随 r² 变化。", "analysis": "两者相除得到 r。", "review": "高斯定理小节"},
        {"question": "电位为零处电场是否一定为零？", "answer": "不一定。", "analysis": "电场取决于电位变化率。", "review": "电位与电场关系"},
        {"question": "边界有自由面电荷时，法向 D 如何变化？", "answer": "按自由面电荷密度跳变。", "analysis": "来自高斯定理的边界形式。", "review": "边界条件"},
        {"question": "镜像法答案为什么要验证边界？", "answer": "因为镜像电荷是为满足边界条件构造的等效源。", "analysis": "不验证边界就无法说明等效问题正确。", "review": "镜像法"},
        {"question": "静电能量密度最常见漏分点是什么？", "answer": "漏掉 1/2。", "analysis": "公式记忆和单位检查都要关注系数。", "review": "静电能量"},
    ]


def _sources(source_hit: bool) -> list[str]:
    base = [
        "教材来源：电磁场与电磁波教材第一章，用于章节范围、概念定义与公式符号核对。",
        "真题来源：往年题汇编中可确认的静电场考点，用于题型和扣分点整理。",
        "PPT来源：课堂讲义中的章节顺序和老师强调内容，用于阅读路径组织。",
    ]
    if not source_hit:
        base.append("图资产说明：教材/试卷图资产未命中，本轮使用程序化重绘教学图；未伪装为教材原图。")
    return base


def _safe_model(context: dict[str, Any]) -> dict[str, Any]:
    safe = {k: v for k, v in context.items() if k not in {"cards", "cases", "concept_blocks", "formulas", "answers", "sections"}}
    if "mock_question_count" in context:
        safe["mock_question_count"] = context["mock_question_count"]
        safe["mock_score_total"] = context["mock_score_total"]
        safe["mock_difficulty_score"] = context["mock_difficulty_score"]
    return safe
