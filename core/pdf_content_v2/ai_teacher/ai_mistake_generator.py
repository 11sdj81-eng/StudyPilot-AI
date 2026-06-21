"""AI Mistake Generator — produce specific, actionable common mistakes."""

from typing import Any

# Per-concept mistake templates (course-agnostic by concept_id pattern)
MISTAKE_TEMPLATES: dict[str, list[str]] = {
    "distribution_function": [
        "只验证单调性，忘记验证右连续和端点极限",
        "混淆 P{X<x} 和 P{X≤x}，在分段点处答案错误",
        "看到分段函数就判定为分布函数，不逐条验证三条性质",
    ],
    "discrete_random_variable": [
        "分布律概率和不为 1，漏验证归一化条件",
        "超几何分布和二项分布混淆（不放回 vs 放回）",
        "组合数 C(n,k) 计算错误，尤其是 n 较大时",
    ],
    "continuous_random_variable": [
        "把密度值 f(a) 当作概率 P{X=a}（单点概率恒为零！）",
        "归一化积分时漏掉负区间或分段积分端点取错",
        "由密度求分布函数时忘记 C（积分常数），导致 F(-∞)≠0",
    ],
    "binomial": [
        "忘记组合数 C(n,k)，直接把 p^k(1-p)^{n-k} 当概率",
        "p 和 1-p 弄反：成功概率和失败概率代反",
        "至少问题忘记用补事件：P{X≥1}=1-P{X=0}",
    ],
    "poisson": [
        "λ=np 算错或忘记验证近似条件（n大p小λ适中）",
        "泊松分布 e^{-λ} 取值不精确导致结果偏差",
        "把泊松分布和二项分布混淆（泊松描述稀有事件）",
    ],
    "normal": [
        "标准化时除以方差 σ² 而非标准差 σ！这是最常见的致命错误",
        "Φ(-z)=1-Φ(z) 转换错误，忘记查表对称性",
        "忘记标准化步骤，直接用原参数查表",
    ],
    "exponential": [
        "参数混淆：均值是 1/λ，不是 λ",
        "忘记指数分布定义域 x>0，x≤0 时密度为 0",
        "无记忆性条件写错：P{X>s+t|X>s}=P{X>t}，不是 P{X>s}",
    ],
}


def generate_mistakes(concept_id: str, course_mistakes: list[str] | None = None) -> list[str]:
    """Generate specific, actionable common mistakes for a concept."""
    mistakes = list(course_mistakes or [])
    templates = MISTAKE_TEMPLATES.get(concept_id, [])
    for t in templates:
        if t not in mistakes:
            mistakes.append(t)
    # Ensure at least 3 specific mistakes
    while len(mistakes) < 3:
        mistakes.append(f"{concept_id}相关公式的适用条件容易忽略")
    return mistakes[:4]


def is_generic_mistake(mistake: str) -> bool:
    """Check if a mistake is too generic to be useful."""
    generic = ["要注意", "容易错", "需要记", "必须掌握", "不能忽略", "很重要", "要小心"]
    return any(g in mistake for g in generic) and len(mistake) < 20
