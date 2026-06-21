"""Syllabus profile: 概率论与随机过程 第二章 随机变量及其分布."""

from core.pdf_content_v2.course_profiles.base import (
    CourseProfile, ExpectedConcept, ExpectedFormula, ExpectedQuestionType,
)

PROBABILITY_CH2_PROFILE = CourseProfile(
    course_id="probability_ch2",
    course_name="概率论与随机过程",
    chapter_name="第二章 随机变量及其分布",
    subject_type="math",
    expected_concepts=[
        ExpectedConcept(name="随机变量", english_key="random_variable", priority=5),
        ExpectedConcept(name="分布函数", english_key="distribution_function", priority=5),
        ExpectedConcept(name="离散型随机变量", english_key="discrete_random_variable", priority=5, depends_on=["随机变量"]),
        ExpectedConcept(name="连续型随机变量", english_key="continuous_random_variable", priority=5, depends_on=["随机变量"]),
        ExpectedConcept(name="0-1分布", english_key="bernoulli", priority=3),
        ExpectedConcept(name="二项分布", english_key="binomial", priority=5, depends_on=["离散型随机变量"]),
        ExpectedConcept(name="泊松分布", english_key="poisson", priority=5, depends_on=["离散型随机变量"]),
        ExpectedConcept(name="几何分布", english_key="geometric", priority=2),
        ExpectedConcept(name="超几何分布", english_key="hypergeometric", priority=2),
        ExpectedConcept(name="均匀分布", english_key="uniform", priority=4, depends_on=["连续型随机变量"]),
        ExpectedConcept(name="指数分布", english_key="exponential", priority=4, depends_on=["连续型随机变量"]),
        ExpectedConcept(name="正态分布", english_key="normal", priority=5, depends_on=["连续型随机变量"]),
        ExpectedConcept(name="随机变量函数的分布", english_key="rv_function_distribution", priority=5, depends_on=["离散型随机变量", "连续型随机变量"]),
    ],
    expected_formulas=[
        ExpectedFormula(name="CDF", display_hint="F(x)", latex_hint="F(x)=", belongs_to="分布函数"),
        ExpectedFormula(name="PMF", display_hint="P{X=x_k}", latex_hint="P\\{X=x_k\\}", belongs_to="离散型随机变量"),
        ExpectedFormula(name="PDF", display_hint="f(x)", latex_hint="f(x)", belongs_to="连续型随机变量"),
        ExpectedFormula(name="Binomial", display_hint="C(n,k)", latex_hint="C_n^k", belongs_to="二项分布"),
        ExpectedFormula(name="Poisson", display_hint="λ^k/k!", latex_hint="\\frac{\\lambda^k}{k!}", belongs_to="泊松分布"),
        ExpectedFormula(name="Normal", display_hint="N(μ,σ²)", latex_hint="\\frac{1}{\\sqrt{2\\pi}", belongs_to="正态分布"),
        ExpectedFormula(name="Exponential", display_hint="λe^{-λx}", latex_hint="\\lambda e^{-\\lambda x}", belongs_to="指数分布"),
        ExpectedFormula(name="Uniform", display_hint="1/(b-a)", latex_hint="\\frac{1}{b-a}", belongs_to="均匀分布"),
        ExpectedFormula(name="E(X)", display_hint="E(X)=", latex_hint="E(X)=", belongs_to="离散型随机变量"),
        ExpectedFormula(name="D(X)", display_hint="D(X)=", latex_hint="D(X)=", belongs_to="离散型随机变量"),
    ],
    expected_question_types=[
        ExpectedQuestionType(name="定义判断", typical_score_share=0.10),
        ExpectedQuestionType(name="概率计算", typical_score_share=0.25),
        ExpectedQuestionType(name="参数求解", typical_score_share=0.15),
        ExpectedQuestionType(name="分布函数", typical_score_share=0.20),
        ExpectedQuestionType(name="随机变量函数分布", typical_score_share=0.15),
        ExpectedQuestionType(name="综合计算", typical_score_share=0.15),
    ],
)
