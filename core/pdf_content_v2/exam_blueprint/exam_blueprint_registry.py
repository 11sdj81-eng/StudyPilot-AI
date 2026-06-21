"""ExamBlueprintRegistry — all course blueprints in one place."""

from __future__ import annotations

from core.pdf_content_v2.exam_blueprint.exam_blueprint import (
    ExamBlueprint, ExamSectionBlueprint, BlueprintSource,
)


# ═══════════════════════════════════════════════════════════════════════════
# 概率论与随机过程 第二章 随机变量及其分布
# ═══════════════════════════════════════════════════════════════════════════

PROBABILITY_CH2_BLUEPRINT = ExamBlueprint(
    course_id="probability_ch2", chapter_id="ch2",
    course_name="概率论与随机过程", chapter_name="第二章 随机变量及其分布",
    total_score=100,
    sections=[
        ExamSectionBlueprint("一、选择题", "选择题", 5, 4, 20,
            required_concepts=["分布函数", "离散型随机变量", "连续型随机变量"],
            difficulty_range=["基础", "中等"]),
        ExamSectionBlueprint("二、填空题", "填空题", 4, 5, 20,
            required_concepts=["常见离散分布", "常见连续分布"],
            difficulty_range=["基础", "中等"]),
        ExamSectionBlueprint("三、计算题", "计算题", 4, 10, 40,
            required_concepts=["分布函数", "连续型随机变量", "常见离散分布", "常见连续分布"],
            difficulty_range=["中等", "综合"]),
        ExamSectionBlueprint("四、综合题", "综合题", 1, 20, 20,
            required_concepts=["随机变量函数的分布"],
            difficulty_range=["综合"]),
    ],
    difficulty_distribution={"基础": 0.35, "中等": 0.45, "综合": 0.20},
    concept_weight_distribution={
        "分布函数": 0.15, "离散型随机变量": 0.15, "连续型随机变量": 0.20,
        "常见离散分布": 0.20, "常见连续分布": 0.20, "随机变量函数分布": 0.10,
    },
    source=BlueprintSource.DEFAULT_PROFILE, confidence=0.85,
)

# ═══════════════════════════════════════════════════════════════════════════
# 电磁场与电磁波 第一章 静电场
# ═══════════════════════════════════════════════════════════════════════════

FIELD_WAVE_CH1_BLUEPRINT = ExamBlueprint(
    course_id="field_wave_ch1", chapter_id="ch1",
    course_name="电磁场与电磁波", chapter_name="第一章 静电场",
    total_score=100,
    sections=[
        ExamSectionBlueprint("一、选择/填空题", "选择/填空", 6, 5, 30,
            required_concepts=["电场强度", "高斯定理", "电位"],
            difficulty_range=["基础", "中等"]),
        ExamSectionBlueprint("二、简答/推导题", "简答/推导", 2, 10, 20,
            required_concepts=["高斯定理", "边界条件"],
            difficulty_range=["中等"]),
        ExamSectionBlueprint("三、计算题", "计算题", 3, 10, 30,
            required_concepts=["高斯定理", "电位与梯度", "镜像法"],
            difficulty_range=["中等", "综合"]),
        ExamSectionBlueprint("四、综合题", "综合题", 1, 20, 20,
            required_concepts=["镜像法", "边界条件"],
            difficulty_range=["综合"]),
    ],
    difficulty_distribution={"基础": 0.30, "中等": 0.40, "综合": 0.30},
    concept_weight_distribution={
        "电场强度": 0.15, "高斯定理": 0.25, "电位与梯度": 0.20,
        "边界条件": 0.20, "镜像法": 0.15, "静电能量": 0.05,
    },
    source=BlueprintSource.DEFAULT_PROFILE, confidence=0.85,
)

# ═══════════════════════════════════════════════════════════════════════════
# 数字电路逻辑设计 第三章 组合逻辑电路
# ═══════════════════════════════════════════════════════════════════════════

DIGITAL_LOGIC_CH3_BLUEPRINT = ExamBlueprint(
    course_id="digital_logic_ch3", chapter_id="ch3",
    course_name="数字电路逻辑设计", chapter_name="第三章 组合逻辑电路",
    total_score=100,
    sections=[
        ExamSectionBlueprint("一、选择/填空题", "选择/填空", 6, 5, 30,
            required_concepts=["逻辑代数", "卡诺图"],
            difficulty_range=["基础", "中等"]),
        ExamSectionBlueprint("二、逻辑函数化简", "化简", 2, 10, 20,
            required_concepts=["逻辑代数", "卡诺图"],
            difficulty_range=["中等"]),
        ExamSectionBlueprint("三、组合电路分析", "分析", 2, 12, 24,
            required_concepts=["编码器/译码器", "数据选择器", "加法器"],
            difficulty_range=["中等"]),
        ExamSectionBlueprint("四、设计题", "设计", 1, 26, 26,
            required_concepts=["组合逻辑", "卡诺图", "编码器/译码器"],
            difficulty_range=["综合"]),
    ],
    difficulty_distribution={"基础": 0.25, "中等": 0.40, "综合": 0.35},
    concept_weight_distribution={
        "逻辑代数": 0.20, "卡诺图": 0.25, "组合逻辑": 0.20,
        "编码器/译码器": 0.15, "数据选择器": 0.10, "加法器": 0.10,
    },
    source=BlueprintSource.DEFAULT_PROFILE, confidence=0.85,
)


class ExamBlueprintRegistry:
    """Central registry for exam blueprints."""

    def __init__(self):
        self._blueprints: dict[str, ExamBlueprint] = {
            "probability_ch2": PROBABILITY_CH2_BLUEPRINT,
            "field_wave_ch1": FIELD_WAVE_CH1_BLUEPRINT,
            "digital_logic_ch3": DIGITAL_LOGIC_CH3_BLUEPRINT,
        }

    def get(self, course_id: str) -> ExamBlueprint | None:
        return self._blueprints.get(course_id)

    def get_default(self) -> ExamBlueprint:
        return PROBABILITY_CH2_BLUEPRINT

    def all_blueprints(self) -> dict[str, ExamBlueprint]:
        return dict(self._blueprints)

    def register(self, blueprint: ExamBlueprint) -> None:
        self._blueprints[blueprint.course_id] = blueprint
