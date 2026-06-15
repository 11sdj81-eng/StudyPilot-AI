"""Build a complete 100-point mock exam from structured study data."""

from __future__ import annotations

from core.study_databases import StudyDatabase
from core.study_objects import ExamPaper, QuestionCard, SolutionBlock


def build_complete_mock_exam(db: StudyDatabase) -> ExamPaper:
    questions: list[QuestionCard] = []

    def q(
        number: int,
        question: str,
        qtype: str,
        score: int,
        concept_ids: list[str],
        formula_ids: list[str],
        answer: str,
        steps: list[str],
        options: list[str] | None = None,
        diagram_type: str = "",
        difficulty: float = 0.6,
        source_basis: str = "上传真题题型结构 + 教材同范围例题",
    ) -> None:
        diagram = db.diagram_for_type(diagram_type) if diagram_type else None
        questions.append(
            QuestionCard(
                id=f"Q{number}",
                display_title=f"题 {number}",
                question=question,
                concept_ids=concept_ids,
                formula_ids=formula_ids,
                source_basis=source_basis,
                difficulty=difficulty,
                question_type=qtype,
                score=score,
                chapter=db.chapter,
                diagram_required=bool(diagram_type),
                diagram_type=diagram_type,
                diagram_id=diagram.id if diagram else "",
                solution=SolutionBlock(steps=steps, answer=answer, rubric=[]),
                metadata={
                    "knowledge_point": "、".join(db.concepts[c].name for c in concept_ids if c in db.concepts),
                    "chapter": db.chapter,
                    "difficulty": difficulty,
                    "question_type": qtype,
                    "in_scope": True,
                    "reliability": "教材例题/真题考法同范围改编",
                },
                options=options or [],
            )
        )

    q(1, "已知某区域电位 φ(x,y,z)=Ax²+Byz，下列关于 Ex 的判断正确的是：", "choice", 4, ["potential_gradient"], ["potential_gradient_formula"], "B", ["使用 E=-∇φ", "Ex=-∂φ/∂x=-2Ax"], ["Ex=2Ax", "Ex=-2Ax", "Ex=-By", "Ex=0"], "potential_field", 0.55)
    q(2, "均匀带电球体外部求电场，最适合选取的高斯面是：", "choice", 4, ["gauss_law"], ["gauss_law_integral"], "A", ["球对称问题选同心球面"], ["同心球面", "任意闭合面", "圆柱面", "矩形面"], "gauss_sphere", 0.45)
    q(3, "介质分界面存在自由面电荷密度 ρₛ 时，正确的法向边界条件是：", "choice", 4, ["boundary_conditions"], ["boundary_normal_d"], "A", ["法向看 D 的跳变"], ["D₁n-D₂n=ρₛ", "E₁n=E₂n", "D₁t=D₂t", "φ₁=-φ₂"], "boundary", 0.62)
    q(4, "接地无限大导体平面上方 z=h 处有点电荷 Q，镜像电荷应为：", "choice", 4, ["image_method"], ["image_plane_potential"], "B", ["接地平面镜像电荷等量异号，位置对称"], ["Q'=Q，z=-h", "Q'=-Q，z=-h", "Q'=Q，z=h", "Q'=-Q，z=0"], "image_plane", 0.7)
    q(5, "静电能量密度常用表达式是：", "choice", 4, ["electrostatic_energy"], ["electrostatic_energy_density"], "B", ["能量密度含系数 1/2"], ["we=D·E", "we=1/2 D·E", "we=ρₛE", "we=φ/Q"], "", 0.4)

    q(6, "球对称电位移大小为 D(r)，半径 r 的球面通量为 ______。", "blank", 4, ["gauss_law"], ["gauss_law_integral"], "D(r)4πr²", ["球面面积为 4πr²"], [], "gauss_sphere", 0.55)
    q(7, "电位与电场强度的关系为 ______。", "blank", 4, ["potential_gradient"], ["potential_gradient_formula"], "E = -∇φ", ["直接使用本章电位负梯度公式"], [], "", 0.45)
    q(8, "无自由面电荷时，分界面法向电位移满足 ______。", "blank", 4, ["boundary_conditions"], ["boundary_normal_d"], "D₁n = D₂n", ["令 ρₛ=0"], [], "boundary", 0.55)
    q(9, "接地平面镜像法中，镜像电荷不是真实电荷，只在 ______ 区域用于等效求解。", "blank", 4, ["image_method"], ["image_plane_potential"], "求解区域", ["镜像电荷位于求解区域外"], [], "image_plane", 0.6)
    q(10, "静电能量密度公式中容易漏掉的系数是 ______。", "blank", 4, ["electrostatic_energy"], ["electrostatic_energy_density"], "1/2", ["识别 we=1/2 D·E"], [], "", 0.35)

    q(11, "说明为什么高斯定理永远成立，但并非任何电荷分布都能用它直接求出场强。", "short_answer", 10, ["gauss_law"], ["gauss_law_integral"], "高斯定理给出总通量，只有对称性足够时才能把场强提出积分号。", ["先说明定理成立", "再说明直接求场需要对称性", "列举球、柱、平面对称"], [], "gauss_sphere", 0.7)
    q(12, "说明镜像电荷是否真实存在，并解释为什么必须说明镜像法的求解区域。", "short_answer", 10, ["image_method"], ["image_plane_potential"], "镜像电荷是假想等效电荷，只保证求解区域内边界条件和场解正确。", ["说明镜像电荷是假想的", "说明不能解释导体内部真实电荷", "指出平面问题适用于 z>0"], [], "image_plane", 0.72)

    q(13, "半径 a 的均匀带电球体，总电荷 Q。求 r<a 和 r>a 两区域电场强度。", "calculation", 20, ["gauss_law"], ["gauss_law_integral", "uniform_sphere_inside", "uniform_sphere_outside"], "球内 E=Qr/(4πε₀a³)，球外 E=Q/(4πε₀r²)。", ["选同心球面", "球内包围电荷 Qr³/a³", "球外包围全部电荷 Q", "写出分段答案"], [], "gauss_sphere", 0.75)
    q(14, "接地无限大导体平面 z=0 上方 z=h 处有点电荷 Q。写出镜像电荷并说明电位表达式如何满足边界。", "calculation", 20, ["image_method"], ["image_plane_potential"], "镜像电荷 Q'=-Q，位于 z=-h；平面上两项电位抵消。", ["放置镜像电荷", "写电位叠加", "代入 z=0 验证", "说明只适用于 z>0"], [], "image_plane", 0.82)

    if len(questions) != 14 or sum(q.score for q in questions) != 100:
        raise ValueError("MockExam 题量或总分不满足 14 题 / 100 分")

    return ExamPaper(
        title="第一章 静电场 BUPT Style Mock Exam",
        instructions=["90 分钟，100 分。", "选择题 5 道，填空题 5 道，简答题 2 道，计算/综合题 2 道。", "每题均绑定知识点、公式和来源依据。"],
        questions=questions,
        source_basis="考试题型库驱动 + 本章公式约束 + 教材同范围例题改编",
        score_total=100,
    )
