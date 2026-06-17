"""StudyPilot v3 PDF renderer built on Jinja2 + MathJax + Playwright."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.diagram_generator_v3 import generate_v3_diagrams, write_diagram_manifest


BASE_CHAPTER = Path("data/golden_chapters/engineering/electromagnetic_static_chapter1")
OUTPUT_DIR = Path("data/outputs")
TEMPLATE_DIR = Path("templates/study_pdf_v3")


def render_all_v3_pdfs(output_dir: str | Path = OUTPUT_DIR) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_v3_chapter_data(BASE_CHAPTER)
    data["rendered_diagrams"] = generate_v3_diagrams(data["diagrams"])
    write_diagram_manifest(data["rendered_diagrams"], out / "StudyPilot_v3_diagram_manifest.json")

    env = _env()
    outputs: dict[str, Any] = {}
    specs = [
        ("Sprint", "sprint.html", build_sprint_context),
        ("PastPaper", "pastpaper.html", build_pastpaper_context),
        ("MockExam", "mock_exam.html", build_mock_exam_context),
        ("Review", "review.html", build_review_context),
    ]
    for name, template_name, builder in specs:
        context = builder(data)
        html_path = out / f"StudyPilot_v3_{name}.html"
        pdf_path = out / f"StudyPilot_v3_{name}.pdf"
        html = env.get_template(template_name).render(**context)
        html_path.write_text(html, encoding="utf-8")
        _print_pdf_with_playwright(html_path, pdf_path)
        outputs[name] = {
            "html": str(html_path.resolve()),
            "pdf": str(pdf_path.resolve()),
            "model": _safe_model(context),
        }
    return outputs


def load_v3_chapter_data(chapter_dir: str | Path = BASE_CHAPTER) -> dict[str, Any]:
    base = Path(chapter_dir)
    data = {
        "concepts": _load(base / "concepts.json"),
        "formulas": _load(base / "formulas.json"),
        "examples": _load(base / "examples.json"),
        "patterns": _load(base / "exam_patterns.json"),
        "diagrams": _load(base / "diagrams.json"),
        "strategies": _load(base / "teaching_strategies.json"),
    }
    _attach_formula_numbers(data["formulas"])
    return data


def build_sprint_context(data: dict[str, Any]) -> dict[str, Any]:
    concepts = _concepts_with_formulas(data)[:6]
    formulas = data["formulas"][:8]
    diagrams = _diagram_map(data)
    return _base_context(
        "第一章静电场考前冲刺",
        {
            "body_class": "sprint",
            "toc": ["最后 30 分钟怎么读", "高频救命卡", "关键图像速记", "必背公式", "5 分钟保底题", "最后检查清单", "参考来源"],
            "concepts": concepts,
            "formulas": formulas,
            "diagrams": [diagrams["gauss_sphere"], diagrams["boundary_interface"], diagrams["image_plane"]],
            "rescue_questions": [
                {"title": "高斯定理入口", "question": "看到球对称带电体，第一步应该选什么高斯面？", "answer": "选同心球面，并按场点位置计算包围电荷。"},
                {"title": "边界条件口诀", "question": "介质分界面处，切向和法向分别优先看哪个场量？", "answer": "切向看 E，法向看 D。"},
                {"title": "电位负梯度", "question": "由电位函数求电场时最容易漏掉什么？", "answer": "负号；电场指向电位降低最快方向。"},
                {"title": "镜像法区域", "question": "镜像电荷是否存在于真实求解区域？", "answer": "不是。镜像电荷是求解区域外的等效工具。"},
                {"title": "能量密度", "question": "静电能量密度公式中最常漏掉的系数是什么？", "answer": "系数 1/2。"},
            ],
            "sources": _sources(),
        },
    )


def build_pastpaper_context(data: dict[str, Any]) -> dict[str, Any]:
    diagrams = _diagram_map(data)
    formula_by_concept = _formula_text_by_concept(data)
    cases = []
    for example in data["examples"][:5]:
        concept_id = example["concept_ids"][0]
        cases.append(
            {
                **example,
                "diagram": _diagram_for_example(example, diagrams),
                "formula_text": "；".join(formula_by_concept.get(concept_id, [])),
                "source_location": _source_location(example),
                "modeling": _modeling_hint(concept_id),
            }
        )
    return _base_context("第一章静电场真题精讲", {"body_class": "pastpaper", "cases": cases, "sources": _sources()})


def build_review_context(data: dict[str, Any]) -> dict[str, Any]:
    diagrams = _diagram_map(data)
    concepts = []
    for concept in data["concepts"]:
        did = _normalize_diagram_id(concept.get("diagram_id", ""))
        concepts.append({**concept, "diagram": diagrams.get(did)})
    examples = []
    for example in data["examples"]:
        examples.append({**example, "diagram": _diagram_for_example(example, diagrams)})
    return _base_context(
        "第一章静电场章节复习讲义",
        {
            "body_class": "review",
            "toc": ["知识地图", "核心知识精讲", "公式总结表", "典型例题", "高频考点与易错点", "自测题", "下一步复习建议", "参考来源"],
            "concepts": concepts,
            "formulas": data["formulas"],
            "examples": examples,
            "patterns": data["patterns"],
            "self_tests": _self_tests(),
            "sources": _sources(),
        },
    )


def build_mock_exam_context(data: dict[str, Any]) -> dict[str, Any]:
    diagrams = _diagram_map(data)
    questions = [
        _q(1, "choice", 4, "关于电场强度的说法，正确的是哪一项？", ["电场强度只与试探电荷有关", "电场强度是标量", "电场强度方向按正试探电荷受力方向定义", "电场强度没有单位"], "C", "按定义判断，电场强度是矢量，方向为正试探电荷受力方向。", ["选 C 得 4 分"]),
        _q(2, "choice", 4, "高斯定理直接求电场时，最关键的前提是？", ["电荷量必须为零", "场具有足够对称性", "必须使用直角坐标", "只能用于导体"], "B", "高斯定理总成立，但直接提出场强需要对称性。", ["选 B 得 4 分"]),
        _q(3, "choice", 4, "由电位求电场时，应使用哪一关系？", ["E 与 V 同向增加", "E 是 V 的负梯度", "E 等于电荷量", "E 与面积成正比"], "B", "静电场中电场等于电位的负梯度。", ["选 B 得 4 分"]),
        _q(4, "choice", 4, "无自由面电荷的介质分界面上，下列说法正确的是？", ["切向 E 连续", "法向 E 必连续", "切向 D 必连续", "所有分量都跳变"], "A", "静电场边界条件中切向 E 连续。", ["选 A 得 4 分"]),
        _q(5, "choice", 4, "接地导体平面镜像法中，镜像电荷通常位于哪里？", ["真实求解区域内", "导体平面另一侧对称位置", "无穷远处", "原电荷同一点"], "B", "镜像电荷在平面另一侧对称位置，符号相反。", ["选 B 得 4 分"]),
        _q(6, "fill", 4, "点电荷电场大小随距离按 ______ 衰减。", [], "距离平方反比", "点电荷场强大小与 r² 成反比。", ["填出平方反比得 4 分"]),
        _q(7, "fill", 4, "均匀带电球体内部电场随 r ______ 增大。", [], "线性", "球内包围电荷与 r³ 成正比，代入高斯定理后 E 与 r 成正比。", ["填线性得 4 分"]),
        _q(8, "fill", 4, "电场线与等位线的关系是 ______。", [], "相互垂直", "电场方向是电位下降最快方向，垂直等位线。", ["填相互垂直得 4 分"]),
        _q(9, "fill", 4, "静电能量密度中常见的系数是 ______。", [], "1/2", "建立电场储能时出现 1/2 系数。", ["填 1/2 得 4 分"]),
        _q(10, "fill", 4, "边界条件中，法向 D 的跳变量由 ______ 决定。", [], "自由面电荷密度", "法向电位移跳变量等于自由面电荷密度。", ["填自由面电荷密度得 4 分"]),
        _q(11, "short", 10, "说明为什么高斯定理求场前必须先判断对称性。", [], "高斯定理本身给出通量关系；只有对称性足够时，才能把场强从面积分中提出，从而直接求出 E。", "没有对称性时通量仍可计算，但不能直接得到各点场强。", ["说明通量关系 4 分", "说明对称性作用 4 分", "表达清楚 2 分"], diagrams.get("gauss_sphere")),
        _q(12, "short", 10, "简述接地导体平面镜像法的建模步骤和适用区域。", [], "在导体平面另一侧放置异号镜像电荷，用原电荷与镜像电荷叠加满足平面零电位；结果只适用于真实电荷所在一侧。", "关键是验证边界条件，并说明镜像电荷不是求解区域内真实电荷。", ["镜像位置与符号 4 分", "零电位解释 4 分", "适用区域 2 分"], diagrams.get("image_plane")),
        _q(13, "calc", 20, "半径 a 的均匀带电绝缘球体总电荷为 Q，求球内 r<a 和球外 r≥a 的电场分布。", [], "球内 E = Qr/(4πε₀a³)，球外 E = Q/(4πε₀r²)，方向沿径向。", "同心球面为高斯面；球内包围电荷按体积比例取 Qr³/a³，球外包围全部电荷。", ["高斯面 4 分", "包围电荷 6 分", "球内结果 5 分", "球外结果 5 分"], diagrams.get("gauss_sphere")),
        _q(14, "calc", 20, "点电荷 q 位于接地导体平面上方距离 d 处。写出镜像电荷模型，并说明平面上电位为何为零。", [], "镜像电荷为 -q，位于导体平面另一侧距离 d 处；平面上任一点到两电荷距离相等，电位贡献大小相等符号相反，所以总电位为零。", "这是边界条件驱动的等效模型，不能把镜像电荷当作真实电荷。", ["镜像电荷 6 分", "电位叠加 6 分", "零电位验证 5 分", "区域说明 3 分"], diagrams.get("image_plane")),
    ]
    sections = {
        "choice": [q for q in questions if q["kind"] == "choice"],
        "fill": [q for q in questions if q["kind"] == "fill"],
        "short": [q for q in questions if q["kind"] == "short"],
        "calc": [q for q in questions if q["kind"] == "calc"],
    }
    return _base_context("第一章静电场模拟试卷", {"body_class": "mock", "sections": sections, "answers": questions, "mock_total_score": sum(q["points"] for q in questions), "mock_question_count": len(questions)})


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


def _load(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _attach_formula_numbers(formulas: list[dict[str, Any]]) -> None:
    for index, formula in enumerate(formulas, start=1):
        formula["number"] = f"1-{index}"


def _base_context(title: str, extra: dict[str, Any]) -> dict[str, Any]:
    course_name = extra.pop("course_name", None) or "课程资料"
    return {
        "title": title,
        "course_name": course_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        **extra,
    }


def _concepts_with_formulas(data: dict[str, Any]) -> list[dict[str, Any]]:
    by_concept = _formula_text_by_concept(data)
    return [{**concept, "formula_texts": by_concept.get(concept["id"], [])} for concept in data["concepts"]]


def _formula_text_by_concept(data: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for formula in data["formulas"]:
        result.setdefault(formula.get("concept_id", ""), []).append(formula["display_text"])
    return result


def _diagram_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for index, diagram in enumerate(data.get("rendered_diagrams", []), start=1):
        result[diagram["id"]] = {**diagram, "figure_no": f"1-{index}"}
    return result


def _diagram_for_example(example: dict[str, Any], diagrams: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    did = _normalize_diagram_id(example.get("diagram_id", ""))
    return diagrams.get(did)


def _normalize_diagram_id(value: str) -> str:
    return re.sub(r"^diagram_", "", value or "")


def _source_location(item: dict[str, Any]) -> str:
    refs = item.get("source_refs", [])
    if not refs:
        return "教材第一章相关小节"
    ref = refs[0]
    return f"{ref.get('file_name', '教材')} · {ref.get('page', '第一章')}"


def _modeling_hint(concept_id: str) -> str:
    return {
        "electric_field": "先画方向，再写大小，最后做矢量叠加。",
        "gauss_law": "判断对称性，选同心/同轴高斯面，分区域算包围电荷。",
        "potential_gradient": "由电位取负梯度，注意方向与等位线垂直。",
        "boundary_conditions": "分切向与法向，分别套用 E 和 D 的边界条件。",
        "image_method": "用求解区域外的镜像电荷满足接地边界。",
        "electrostatic_energy": "由能量密度判断空间能量分布和高场风险。",
    }.get(concept_id, "先识别模型，再选择公式。")


def _self_tests() -> list[dict[str, str]]:
    return [
        {"question": "为什么均匀带电球体内部电场不是平方反比？", "answer": "因为球内高斯面只包围部分电荷。", "analysis": "包围电荷随 r³ 增长，代入球面积 r² 后得到 E 与 r 成正比。"},
        {"question": "电位为零的点，电场一定为零吗？", "answer": "不一定。", "analysis": "电场取决于电位空间变化率，而不是电位本身数值。"},
        {"question": "边界条件中有自由面电荷时哪个量跳变？", "answer": "法向电位移 D。", "analysis": "切向 E 仍连续，法向 D 的差由自由面电荷密度决定。"},
        {"question": "接地平面镜像法中镜像电荷符号是什么？", "answer": "与原电荷相反。", "analysis": "这样平面上两项电位大小相等、符号相反。"},
        {"question": "静电能量密度最常漏掉什么？", "answer": "系数 1/2。", "analysis": "这是评分点之一，填空题尤其容易丢分。"},
    ]


def _q(no: int, kind: str, points: int, question: str, options: list[str], answer: str, analysis: str, rubric: list[str], diagram: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"no": no, "kind": kind, "points": points, "question": question, "options": options, "answer": answer, "analysis": analysis, "rubric": rubric, "diagram": diagram}


def _sources() -> list[str]:
    return [
        "教材来源：电磁场与电磁波教材第一章，用于章节范围、概念定义与公式符号核对。",
        "PPT来源：课堂静电场章节讲义，用于老师强调的高频考法与复习顺序。",
        "真题来源：往年题汇编中可确认的静电场考点，用于高斯定理、边界条件和镜像法题型整理。",
        "程序化教学图：StudyPilot v3 根据知识点自动生成，用于辅助理解，不替代教材原图。",
    ]


def _safe_model(context: dict[str, Any]) -> dict[str, Any]:
    safe = {k: v for k, v in context.items() if k not in {"concepts", "examples", "formulas", "patterns"}}
    if "sections" in safe:
        safe["mock_question_count"] = sum(len(items) for items in safe["sections"].values())
        safe["mock_score_total"] = sum(q["points"] for items in safe["sections"].values() for q in items)
    return safe
