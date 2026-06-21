"""ExamPatternLibrary — registered question templates per course.

AI can ONLY vary background/data/difficulty within these patterns.
No free-form question generation allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExamPattern:
    """A registered exam question pattern for a specific course + concept.

    AI may vary: context (background story), data (numbers), difficulty (easy/medium/hard).
    AI may NOT: invent new patterns, change the concept, add concepts not in the course profile.
    """

    def __init__(self, pattern_id: str, course_id: str, concept_id: str,
                 question_type: str, stem_template: str,
                 answer_template: str, solution_steps: list[str],
                 grading_points: list[str], common_mistakes: list[str],
                 difficulty: str = "中等", source: str = "textbook",
                 variant_hints: list[str] | None = None):
        self.pattern_id = pattern_id
        self.course_id = course_id
        self.concept_id = concept_id
        self.question_type = question_type
        self.stem_template = stem_template
        self.answer_template = answer_template
        self.solution_steps = list(solution_steps)
        self.grading_points = list(grading_points)
        self.common_mistakes = list(common_mistakes)
        self.difficulty = difficulty
        self.source = source
        self.variant_hints = list(variant_hints or [])

    def generate(self, params: dict | None = None) -> dict:
        """Generate a real question from this pattern, optionally varying data."""
        p = params or {}
        stem = self.stem_template.format(**p) if p else self.stem_template
        answer = self.answer_template.format(**p) if p else self.answer_template
        return {
            "pattern_id": self.pattern_id, "concept_id": self.concept_id,
            "question_type": self.question_type, "stem": stem,
            "answer": answer, "solution_steps": list(self.solution_steps),
            "grading_points": list(self.grading_points),
            "common_mistakes": list(self.common_mistakes),
            "difficulty": self.difficulty, "source": self.source,
        }

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id, "course_id": self.course_id,
            "concept_id": self.concept_id, "question_type": self.question_type,
            "stem_template": self.stem_template[:100],
            "difficulty": self.difficulty, "source": self.source,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Probability Chapter 2 patterns
# ═══════════════════════════════════════════════════════════════════════════

PROB_CH2_PATTERNS: list[ExamPattern] = [
    # ── Distribution function ──
    ExamPattern("prob_cdf_validate", "probability_ch2", "distribution_function",
        "选择题",
        "设随机变量 X 的分布函数为 F(x)={{0, x<0; x², 0≤x<1; 1, x≥1}}。下列说法正确的是：",
        "B。F(x)满足单调不减、右连续、F(-∞)=0、F(+∞)=1，是合法的分布函数。",
        ["验证单调性", "验证右连续性", "验证端点极限"],
        ["三条性质逐条验证 3 分", "结论正确 1 分"],
        ["只验证其中一条就下结论", "x=1处忘记检查右连续"],
        source="textbook",
        variant_hints=["更改分段函数形式", "改为判断是否合法的判断题"]),

    ExamPattern("prob_cdf_interval", "probability_ch2", "distribution_function",
        "填空题",
        "设 X 的分布函数为 F(x)。若 a<b，则 P{{a<X≤b}}=______。",
        "F(b)-F(a)（注意区间左开右闭）",
        ["由分布函数定义 F(x)=P{{X≤x}}", "P{{a<X≤b}}=P{{X≤b}}-P{{X≤a}}=F(b)-F(a)"],
        ["公式正确 3 分", "区间开闭说明 2 分"],
        ["混淆 P{{X<x}} 和 P{{X≤x}}", "忘记右连续性导致区间端点错误"],
        source="textbook",
        variant_hints=["改为求 P{{X>b}}", "改为 P{{a≤X<b}}"]),

    # ── Discrete random variable ──
    ExamPattern("prob_discrete_law", "probability_ch2", "discrete_random_variable",
        "计算题",
        "一盒中有 3 个白球和 2 个黑球，从中随机取 2 个球。以 X 表示取到的白球数。(1)求 X 的分布律；(2)求 P{{X≥1}}。",
        "(1) P{{X=0}}=1/10, P{{X=1}}=6/10, P{{X=2}}=3/10；(2) P{{X≥1}}=0.9",
        ["确定 X 取值：{{0,1,2}}", "P{{X=0}}=C(2,2)/C(5,2)=1/10", "P{{X=1}}=C(3,1)·C(2,1)/C(5,2)=6/10", "P{{X=2}}=C(3,2)/C(5,2)=3/10", "验证 ∑p_i=1，P{{X≥1}}=1-P{{X=0}}=0.9"],
        ["正确列出分布律 3 分", "验证归一化 1 分", "概率计算正确 2 分"],
        ["组合数计算错误", "遗漏取值", "忘记验证概率和为 1"],
        source="textbook",
        variant_hints=["改变白球黑球数量", "改为有放回抽样（二项分布）"]),

    # ── Continuous random variable ──
    ExamPattern("prob_pdf_constant", "probability_ch2", "continuous_random_variable",
        "计算题",
        "设 X 的密度函数为 f(x)={{k(1-x²), -1<x<1; 0, 其他}}。(1)求常数 k；(2)求 P{{0<X<1/2}}。",
        "(1) k=3/4；(2) P{{0<X<1/2}}=11/32",
        ["由归一化 ∫f(x)dx=1 求 k", "∫_{-1}^{1} k(1-x²)dx = k·4/3 = 1 → k=3/4", "P=∫_0^{1/2} (3/4)(1-x²)dx = 11/32"],
        ["归一化条件 2 分", "k 正确 2 分", "区间积分 2 分"],
        ["归一化积分漏负区间", "分段积分端点取错", "密度值当概率"],
        source="textbook",
        variant_hints=["改变密度函数形式", "改为求分布函数 F(x)"]),

    # ── Binomial distribution ──
    ExamPattern("prob_binomial_calc", "probability_ch2", "binomial",
        "计算题",
        "设某产品次品率为 0.1，随机抽取 10 件，以 X 表示次品数。(1)指出 X 的分布及参数；(2)求恰有 2 件次品的概率；(3)求至少 1 件次品的概率。",
        "(1) X~B(10,0.1)；(2) P{{X=2}}=C(10,2)·0.1²·0.9⁸≈0.1937；(3) P{{X≥1}}=1-0.9¹⁰≈0.6513",
        ["识别：n=10次独立重复，p=0.1", "P{{X=2}}代入二项公式", "至少→补事件：1-P{{X=0}}"],
        ["分布识别 2 分", "二项公式 2 分", "补事件技巧 2 分", "计算正确 1 分"],
        ["忘记组合数 C(10,2)", "p 和 1-p 混淆", "至少问忘记补事件"],
        source="textbook",
        variant_hints=["改变 n 和 p", "改为求 P{{X≤2}}"]),

    # ── Poisson distribution ──
    ExamPattern("prob_poisson_approx", "probability_ch2", "poisson",
        "计算题",
        "某保险公司有 3000 个客户，每个客户一年内索赔概率为 0.001。用泊松近似求一年内恰有 2 人索赔的概率。",
        "λ=np=3, P{{X=2}}≈3²·e⁻³/2!≈0.2240",
        ["检查近似条件：n大(3000), p小(0.001), λ=np=3适中", "泊松公式：P{{X=2}}=λ²e^{-λ}/2!", "代入 λ=3：9·e⁻³/2≈0.2240"],
        ["验证近似条件 2 分", "正确计算 λ 2 分", "泊松公式 2 分", "数值正确 1 分"],
        ["不验证近似条件就使用", "λ=np 计算错误", "e^{-λ} 取值不准确"],
        source="textbook",
        variant_hints=["改变 n 和 p", "改为求 P{{X≤2}}"]),

    # ── Normal distribution ──
    ExamPattern("prob_normal_standardize", "probability_ch2", "normal",
        "计算题",
        "设 X~N(170,36)。(1)求 P{{X>180}}；(2)求 P{{164<X<176}}。（Φ(1.67)=0.9525, Φ(1)=0.8413）",
        "(1) P{{X>180}}=1-Φ(1.67)=0.0475；(2) P{{164<X<176}}=Φ(1)-Φ(-1)=0.6826",
        ["(1) 标准化: Z=(180-170)/6=1.67", "P{{X>180}}=1-Φ(1.67)=0.0475", "(2) Z₁=(164-170)/6=-1, Z₂=1", "Φ(-1)=1-Φ(1)=0.1587, P=0.8413-0.1587=0.6826"],
        ["标准化公式 2 分", "注意 σ=6(非σ²=36) 2 分", "Φ(-z)转换 2 分", "结果正确 1 分"],
        ["标准化时除以方差 σ² 而非标准差 σ", "Φ(-z)=1-Φ(z) 转换错误", "忘记标准化步骤"],
        source="textbook",
        variant_hints=["改变 μ 和 σ²", "改为求 P{{X<c}}=0.05 的 c"]),

    # ── RV function distribution ──
    ExamPattern("prob_rv_transform", "probability_ch2", "rv_function_distribution",
        "综合题",
        "设 X~N(μ,σ²)，Y=2X+3。(1)判断变换单调性；(2)求 Y 的概率密度函数；(3)求 E(Y) 和 D(Y)。",
        "Y~N(2μ+3, 4σ²)。(2) f_Y(y)=f_X((y-3)/2)·(1/2), Y~N(2μ+3, 4σ²)。(3) E(Y)=2μ+3, D(Y)=4σ²",
        ["g(x)=2x+3 严格单调增", "反函数 x=(y-3)/2, |h'(y)|=1/2", "代入得 Y~N(2μ+3, 4σ²)", "E(aX+b)=aE(X)+b, D(aX+b)=a²D(X)"],
        ["单调性判断 3 分", "公式推导 5 分", "期望方差 4 分", "结论说明 3 分", "规范性 5 分"],
        ["漏 |h'(y)| 绝对值", "非单调函数不分区", "方差漏 a² 系数"],
        source="textbook",
        variant_hints=["改为 Y=X²（非单调）", "改为 Y=|X|"]),
]

# ═══════════════════════════════════════════════════════════════════════════
# Field Wave Chapter 1 patterns (placeholder)
# ═══════════════════════════════════════════════════════════════════════════

FIELD_WAVE_CH1_PATTERNS: list[ExamPattern] = [
    ExamPattern("fw_gauss_sphere", "field_wave_ch1", "gauss_law",
        "计算题",
        "半径为 R 的均匀带电球体，体电荷密度为 ρ。求 r<R 和 r>R 处的电场强度。",
        "r<R: E=ρr/(3ε₀)；r>R: E=ρR³/(3ε₀r²)",
        ["分析对称性：球对称", "取半径为 r 的球形高斯面", "r<R: 包围电荷 Q=ρ·(4πr³/3)", "r>R: 包围电荷 Q=ρ·(4πR³/3)", "由高斯定理 ∮E·dS=Q/ε₀ 求解"],
        ["对称性分析 2 分", "高斯面选择 2 分", "包围电荷计算 3 分", "结果正确 3 分"],
        ["对称性不够硬提场强", "球内包围电荷写为总电荷", "漏分段条件"],
        source="textbook",
        variant_hints=["改为均匀带电球壳", "改为无限长圆柱"]),
]

# ═══════════════════════════════════════════════════════════════════════════
# Digital Logic Chapter 3 patterns (placeholder)
# ═══════════════════════════════════════════════════════════════════════════

DIGITAL_LOGIC_CH3_PATTERNS: list[ExamPattern] = [
    ExamPattern("dl_kmap_simplify", "digital_logic_ch3", "karnaugh_map",
        "计算题",
        "用卡诺图化简 F(A,B,C,D)=Σm(0,2,5,7,8,10,13,15)，画出最简与或式。",
        "F=B'D'+BD（经过卡诺图化简）",
        ["画4变量卡诺图", "填入16个最小项", "圈出质蕴含项", "写出最简表达式"],
        ["卡诺图正确 3 分", "圈法正确 3 分", "最简式正确 2 分"],
        ["卡诺图行列标错", "圈不满足2^n个", "漏掉必要质蕴含项"],
        source="textbook",
        variant_hints=["改为 F=ΠM(...)", "增加无关项 d(...)"]),
]


class ExamPatternLibrary:
    """Central library of registered exam patterns per course.

    Rules:
        1. Every MockExam question MUST come from a registered pattern.
        2. AI may vary background, data (numbers), and difficulty.
        3. AI may NOT invent new patterns or change the concept.
        4. Template questions ("请填写...") are REJECTED.
    """

    def __init__(self):
        self._patterns: dict[str, list[ExamPattern]] = {
            "probability_ch2": list(PROB_CH2_PATTERNS),
            "field_wave_ch1": list(FIELD_WAVE_CH1_PATTERNS),
            "digital_logic_ch3": list(DIGITAL_LOGIC_CH3_PATTERNS),
        }

    def get_patterns(self, course_id: str) -> list[ExamPattern]:
        return self._patterns.get(course_id, [])

    def get_for_concept(self, course_id: str, concept_id: str) -> list[ExamPattern]:
        return [p for p in self.get_patterns(course_id) if p.concept_id == concept_id]

    def get_by_type(self, course_id: str, question_type: str) -> list[ExamPattern]:
        return [p for p in self.get_patterns(course_id) if p.question_type == question_type]

    def count(self, course_id: str) -> int:
        return len(self.get_patterns(course_id))

    def all_courses(self) -> list[str]:
        return list(self._patterns.keys())

    def stats(self) -> dict:
        return {
            course_id: {
                "total": len(patterns),
                "by_type": {t: sum(1 for p in patterns if p.question_type == t)
                            for t in set(p.question_type for p in patterns)},
                "by_concept": {c: sum(1 for p in patterns if p.concept_id == c)
                               for c in set(p.concept_id for p in patterns)},
            }
            for course_id, patterns in self._patterns.items()
        }


_library: ExamPatternLibrary | None = None


def get_library() -> ExamPatternLibrary:
    global _library
    if _library is None:
        _library = ExamPatternLibrary()
    return _library
