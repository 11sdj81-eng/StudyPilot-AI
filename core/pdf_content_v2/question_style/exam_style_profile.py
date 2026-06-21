"""ExamStyleProfile — per-course question style rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExamStyleProfile:
    course_id: str
    course_name: str
    question_type: str  # or "*" for all
    style_rules: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
    required_elements: list[str] = field(default_factory=list)
    example_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id, "course_name": self.course_name,
            "question_type": self.question_type, "style_rules": self.style_rules,
            "forbidden_patterns": self.forbidden_patterns,
            "required_elements": self.required_elements,
            "example_patterns": self.example_patterns,
        }


# ═══════════════════════════════════════════════════════════════════════════
# 概率论与随机过程
# ═══════════════════════════════════════════════════════════════════════════

PROBABILITY_STYLE = [
    ExamStyleProfile(
        course_id="probability_ch2", course_name="概率论与随机过程",
        question_type="选择题",
        style_rules=["考查明确概念判断、公式适用条件、分布性质"],
        forbidden_patterns=[
            "请选择一个", "以下说法错误的是",  # too vague without specifics
        ],
        required_elements=["具体分布或函数条件", "4个互斥且有意义选项", "唯一正确答案"],
        example_patterns=[
            "设 X 的分布函数为 F(x)，下列说法正确的是：",
            "设 X~B(n,p)，则 E(X)等于：",
            "下列函数中可作为密度函数的是：",
        ],
    ),
    ExamStyleProfile(
        course_id="probability_ch2", course_name="概率论与随机过程",
        question_type="填空题",
        style_rules=["有具体条件或公式空缺", "答案唯一且可验证"],
        forbidden_patterns=[
            "请填写一个", "请写出一个", "请列举",
        ],
        required_elements=["具体参数条件", "明确空缺位置", "可数值验证的答案"],
        example_patterns=[
            "设 X 的密度函数为 f(x)，则 P{a<X≤b}=______。",
            "设 X~P(3)，则 P{X=2}=______。",
            "设 F(x) 为 X 的分布函数，则 F(+∞)=______。",
        ],
    ),
    ExamStyleProfile(
        course_id="probability_ch2", course_name="概率论与随机过程",
        question_type="计算题",
        style_rules=["有具体数据、条件和求解目标", "步骤可逐步验证"],
        forbidden_patterns=[
            "请计算一个", "计算某概率",  # too vague
        ],
        required_elements=["具体分布类型和参数", "明确求解目标", "标准答案"],
        example_patterns=[
            "设 X~B(10,0.2)，求 P{X=2} 和 E(X)。",
            "设 X 的密度为 f(x)=k(1-x²), -1<x<1，求 k 和 P{0<X<1/2}。",
            "设 X~N(170,36)，求 P{X>180}。",
        ],
    ),
    ExamStyleProfile(
        course_id="probability_ch2", course_name="概率论与随机过程",
        question_type="综合题",
        style_rules=["至少两步以上", "识别分布→列公式→计算→解释"],
        forbidden_patterns=["请证明以下结论"],
        required_elements=["完整场景", "多步推理", "评分点分解"],
        example_patterns=[
            "设 X~N(μ,σ²)，Y=2X+3，(1)求 Y 的分布；(2)求 E(Y)和 D(Y)；(3)说明推导依据。",
        ],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
# 电磁场与电磁波
# ═══════════════════════════════════════════════════════════════════════════

FIELD_WAVE_STYLE = [
    ExamStyleProfile(
        course_id="field_wave_ch1", course_name="电磁场与电磁波",
        question_type="*",
        style_rules=["考查物理概念、公式、边界条件、方向判断"],
        forbidden_patterns=[
            "请说明.*重要性", "请谈谈.*理解", "请掌握",
        ],
        required_elements=["物理场景", "具体参数", "矢量方向"],
        example_patterns=[
            "半径为 R 的均匀带电球体体电荷密度为 ρ，求 r<R 和 r>R 处的电场强度。",
            "已知电位 φ=3x²-2y²(V)，求点(1,1,0)处的电场强度。",
            "z>0 区域为介质 ε₁，z<0 为 ε₂，分界面 z=0 上无自由电荷，写出边界条件。",
        ],
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
# 数字电路逻辑设计
# ═══════════════════════════════════════════════════════════════════════════

DIGITAL_LOGIC_STYLE = [
    ExamStyleProfile(
        course_id="digital_logic_ch3", course_name="数字电路逻辑设计",
        question_type="*",
        style_rules=["考查逻辑函数、真值表、卡诺图、电路分析"],
        forbidden_patterns=[
            "请说明.*意义", "请谈谈.*应用",
        ],
        required_elements=["具体逻辑函数或电路", "明确输入/输出"],
        example_patterns=[
            "用卡诺图化简 F(A,B,C,D)=Σm(0,2,5,7,8,10,13,15)，画出最简与或式。",
            "分析下图所示组合逻辑电路，写出输出函数表达式。",
            "用 3-8 译码器 74LS138 和与非门实现函数 F=Σm(1,3,5,7)。",
        ],
    ),
]


def get_style(course_id: str, question_type: str = "*") -> ExamStyleProfile | None:
    registry = {
        "probability_ch2": PROBABILITY_STYLE,
        "field_wave_ch1": FIELD_WAVE_STYLE,
        "digital_logic_ch3": DIGITAL_LOGIC_STYLE,
    }
    styles = registry.get(course_id, [])
    for s in styles:
        if s.question_type == question_type or s.question_type == "*":
            return s
    return styles[0] if styles else None
