"""RealQuestionRewriter — converts fake questions to real exam-style questions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.question_style.fake_question_detector import FakeQuestionResult
from core.pdf_content_v2.question_style.exam_style_profile import ExamStyleProfile


@dataclass
class RewriteResult:
    success: bool
    original: str = ""
    rewritten: str = ""
    rewritten_answer: str = ""
    rewritten_steps: list[str] = field(default_factory=list)
    rewritten_scoring: list[str] = field(default_factory=list)
    rewritten_mistakes: list[str] = field(default_factory=list)
    source_level: str = "ai_derived"
    confidence: float = 0.0
    strategy: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success, "original": self.original[:80],
            "rewritten": self.rewritten[:120], "source_level": self.source_level,
            "confidence": self.confidence, "strategy": self.strategy,
        }


class RealQuestionRewriter:
    """Rewrite fake/template questions into real exam-style questions.

    Uses rule-based templates keyed to concept + question type.
    No LLM dependency — operates on structured data.
    """

    # ── Rewrite templates by concept × question_type ──
    REWRITE_TEMPLATES: dict[str, dict[str, dict]] = {
        # Distribution function
        "distribution_function": {
            "填空题": {
                "stem": "设随机变量 X 的分布函数为 F(x)，若 a<b，则 P{a<X≤b}=______。",
                "answer": "F(b)-F(a)（注意：区间左开右闭）",
                "steps": ["由分布函数定义 F(x)=P{X≤x}", "P{a<X≤b}=P{X≤b}-P{X≤a}=F(b)-F(a)"],
                "scoring": ["公式 3 分", "注意区间开闭 2 分"],
                "mistakes": ["混淆 P{X<x} 和 P{X≤x}", "忘记右连续性"],
            },
            "计算题": {
                "stem": "判断函数 F(x)={0, x<0; x², 0≤x<1; 1, x≥1} 是否为某随机变量的分布函数，并说明理由。",
                "answer": "是合法的分布函数。满足单调不减、右连续、F(-∞)=0、F(+∞)=1。",
                "steps": ["验证单调性：x²在[0,1)上单调增", "验证右连续：分段点处左右极限相等", "验证端点：F(-∞)=0, F(+∞)=1"],
                "scoring": ["单调性 2 分", "右连续性 2 分", "端点极限 1 分"],
                "mistakes": ["只检查一两条性质", "分段点未验证连续性"],
            },
        },
        # Discrete random variable
        "discrete_random_variable": {
            "填空题": {
                "stem": "一盒中有 3 白 2 黑共 5 球，随机取 2 球，以 X 表示取到的白球数，则 P{X=1}=______。",
                "answer": "C(3,1)·C(2,1)/C(5,2) = 6/10 = 0.6",
                "steps": ["确定 X 取值：0,1,2", "P{X=1}=C(3,1)·C(2,1)/C(5,2)=6/10"],
                "scoring": ["组合数公式 2 分", "计算正确 3 分"],
                "mistakes": ["组合数计算错误", "忘记分母 C(5,2)"],
            },
        },
        # Continuous random variable
        "continuous_random_variable": {
            "填空题": {
                "stem": "设连续型随机变量 X 的密度函数为 f(x)，则 ∫_{-∞}^{∞} f(x)dx =______。",
                "answer": "1（归一化条件）",
                "steps": ["密度函数必须满足归一化条件", "∫f(x)dx=1"],
                "scoring": ["写出归一化条件 2 分", "结果正确 3 分"],
                "mistakes": ["忘记归一化条件", "积分区间错误"],
            },
            "计算题": {
                "stem": "设 X 的密度函数为 f(x)={k(1-x²), -1<x<1; 0, 其他}。求：(1)常数 k；(2)P{0<X<1/2}。",
                "answer": "(1)k=3/4；(2)P=11/32",
                "steps": ["∫_{-1}^{1} k(1-x²)dx=1 → k[x-x³/3]_{-1}^{1}=k·(4/3)=1 → k=3/4", "P=∫_0^{1/2} (3/4)(1-x²)dx = 11/32"],
                "scoring": ["归一化 2 分", "k 正确 1 分", "区间积分 2 分"],
                "mistakes": ["归一化积分漏负区间", "分段积分端点取错"],
            },
        },
        # Common discrete distributions
        "common_discrete_distributions": {
            "填空题": {
                "stem": "设 X~B(10, 0.2)，则 E(X)=______，D(X)=______。",
                "answer": "E(X)=np=2, D(X)=np(1-p)=1.6",
                "steps": ["二项分布 B(n,p) 的 E(X)=np", "D(X)=np(1-p)", "代入 n=10, p=0.2"],
                "scoring": ["E(X) 2 分", "D(X) 2 分", "结果正确 1 分"],
                "mistakes": ["E(X)和D(X)公式混淆", "p和1-p弄反"],
            },
            "计算题": {
                "stem": "已知某产品次品率为 0.1，随机抽取 10 件。设 X 为次品数。(1)指出 X 的分布；(2)求恰有 2 件次品的概率；(3)求至少 1 件次品的概率。",
                "answer": "(1)X~B(10,0.1)；(2)P{X=2}=C(10,2)·0.1²·0.9⁸≈0.1937；(3)P{X≥1}=1-P{X=0}=1-0.9¹⁰≈0.6513",
                "steps": ["识别：n=10次独立重复，p=0.1", "P{X=2}代入二项公式", "至少→补事件：1-P{X=0}"],
                "scoring": ["识别分布 2 分", "P{X=2} 2 分", "补事件 2 分", "计算正确 1 分"],
                "mistakes": ["忘记 C(10,2)", "p和1-p混淆", "至少问忘记补事件"],
            },
        },
        # Common continuous distributions
        "common_continuous_distributions": {
            "填空题": {
                "stem": "设 X~N(170, 36)，则标准化后 Z=______~N(0,1)。",
                "answer": "Z=(X-170)/6",
                "steps": ["标准化公式：Z=(X-μ)/σ", "μ=170, σ=6（注意：σ²=36, σ=6）"],
                "scoring": ["公式正确 2 分", "μ代入正确 1 分", "σ（非σ²）正确 2 分"],
                "mistakes": ["混淆 σ 和 σ²，除以方差而非标准差"],
            },
            "计算题": {
                "stem": "设 X~N(170, 36)，求 P{X>180}。（Φ(1.67)=0.9525）",
                "answer": "P{X>180}=1-Φ((180-170)/6)=1-Φ(1.67)=0.0475",
                "steps": ["标准化：Z=(180-170)/6=1.67", "P{X>180}=1-Φ(1.67)=1-0.9525=0.0475"],
                "scoring": ["标准化 2 分", "查表 2 分", "结果正确 1 分"],
                "mistakes": ["忘记减均值除标准差", "Φ(-z)=1-Φ(z)弄反"],
            },
        },
        # RV function distribution
        "rv_function_distribution": {
            "综合题": {
                "stem": "设 X~N(μ,σ²)，Y=2X+3。(1)求 Y 的概率密度函数；(2)求 E(Y)和 D(Y)；(3)推导依据。",
                "answer": "Y~N(2μ+3, 4σ²)。(2)E(Y)=2μ+3, D(Y)=4σ²。(3)正态分布线性变换仍为正态。",
                "steps": ["判定 g(X)=2X+3 严格单调", "反函数 X=(Y-3)/2, |h'(Y)|=1/2", "代入公式得 f_Y(y)", "E(aX+b)=aE(X)+b, D(aX+b)=a²D(X)"],
                "scoring": ["单调判定 3 分", "公式推导 5 分", "期望/方差 4 分", "结论说明 3 分", "规范性 5 分"],
                "mistakes": ["漏 |h'(y)|", "非单调不分区", "方差漏 a²"],
            },
        },
    }

    def rewrite(self, question: dict, detector_result: FakeQuestionResult) -> RewriteResult:
        """Attempt to rewrite a fake question into a real exam question."""
        stem = str(question.get("stem", question.get("problem", "")))
        qtype = str(question.get("type", question.get("question_type", "")))
        concept_id = self._guess_concept(stem)

        templates = self.REWRITE_TEMPLATES.get(concept_id, {})
        template = templates.get(qtype, templates.get("计算题", templates.get("填空题")))

        if not template:
            return RewriteResult(
                success=False, original=stem, confidence=0.0,
                strategy=f"无匹配重写模板 (concept={concept_id}, type={qtype})",
            )

        return RewriteResult(
            success=True, original=stem,
            rewritten=template["stem"], rewritten_answer=template["answer"],
            rewritten_steps=template.get("steps", []),
            rewritten_scoring=template.get("scoring", []),
            rewritten_mistakes=template.get("mistakes", []),
            source_level="ai_derived",
            confidence=0.80,
            strategy=f"模板重写: {concept_id}::{qtype}",
        )

    def _guess_concept(self, text: str) -> str:
        m = {
            "分布函数": "distribution_function",
            "离散": "discrete_random_variable", "分布律": "discrete_random_variable",
            "连续": "continuous_random_variable", "密度": "continuous_random_variable",
            "二项": "common_discrete_distributions", "泊松": "common_discrete_distributions",
            "正态": "common_continuous_distributions", "指数": "common_continuous_distributions",
            "均匀": "common_continuous_distributions",
            "随机变量函数": "rv_function_distribution", "变换": "rv_function_distribution",
        }
        for kw, cid in m.items():
            if kw in text:
                return cid
        return "common_discrete_distributions"
