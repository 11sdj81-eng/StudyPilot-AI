"""Course profiles for PDF 2.2 — generic course/chapter configuration system."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# Course profile definitions
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class ChapterProfile:
    chapter_id: str
    chapter_name: str
    course_name: str
    subject_type: str  # math, engineering
    seed_dir: str  # relative to data/golden_chapters/
    concept_ids: list[str]
    pdf_title_suffix: str  # e.g. "第二章 · 30分钟冲刺讲义"
    forbidden_keywords: list[str] = field(default_factory=list)
    required_keywords: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Registered course profiles
# ═══════════════════════════════════════════════════════════════════════════

COURSE_PROFILES: dict[str, dict[str, ChapterProfile]] = {
    "概率论与随机过程": {
        "ch2": ChapterProfile(
            chapter_id="probability_random_var_ch2",
            chapter_name="第二章 随机变量及其分布",
            course_name="概率论与随机过程",
            subject_type="math",
            seed_dir="math/probability_random_var_ch2",
            concept_ids=[
                "random_variable", "distribution_function",
                "discrete_random_variable", "continuous_random_variable",
                "common_discrete_distributions", "common_continuous_distributions",
                "rv_function_distribution",
            ],
            pdf_title_suffix="第二章 · 随机变量及其分布",
            forbidden_keywords=[
                "静电场", "电磁场与电磁波", "高斯定理", "镜像法",
                "边界条件", "电位与电场", "电荷", "介质分界面",
            ],
            required_keywords=[
                "概率论与随机过程", "第二章", "随机变量", "分布函数",
                "离散型随机变量", "连续型随机变量", "二项分布", "泊松分布", "正态分布",
            ],
        ),
    },
    "电磁场与电磁波": {
        "ch1": ChapterProfile(
            chapter_id="electromagnetic_static_chapter1",
            chapter_name="第一章 静电场",
            course_name="电磁场与电磁波",
            subject_type="engineering",
            seed_dir="engineering/electromagnetic_static_chapter1",
            concept_ids=[
                "electric_field", "gauss_law", "potential_gradient",
                "boundary_conditions", "image_method", "electrostatic_energy",
            ],
            pdf_title_suffix="第一章 · 静电场",
            forbidden_keywords=[
                "概率论", "随机变量", "二项分布", "泊松分布", "正态分布",
            ],
            required_keywords=[
                "电磁场与电磁波", "静电场", "电场强度", "高斯定理",
                "电位", "边界条件", "镜像法",
            ],
        ),
    },
    "数字电路逻辑设计": {
        "ch3": ChapterProfile(
            chapter_id="digital_logic_combinational_ch3",
            chapter_name="第三章 组合逻辑电路",
            course_name="数字电路逻辑设计",
            subject_type="engineering",
            seed_dir="engineering/digital_logic_combinational_ch3",
            concept_ids=[
                "combinational_logic", "karnaugh_map", "encoder_decoder",
                "multiplexer", "adder_comparator",
            ],
            pdf_title_suffix="第三章 · 组合逻辑电路",
            forbidden_keywords=[
                "静电场", "概率论", "电磁场", "高斯", "镜像法",
            ],
            required_keywords=[
                "数字电路", "组合逻辑", "卡诺图", "译码器",
                "数据选择器", "逻辑函数",
            ],
        ),
    },
}


def get_profile(course_name: str, chapter_key: str = "ch2") -> ChapterProfile | None:
    """Get a course chapter profile by course name and chapter key."""
    course = COURSE_PROFILES.get(course_name, {})
    return course.get(chapter_key)


def get_seed_path(course_name: str, chapter_key: str = "ch2") -> Path:
    """Get the seed data directory for a course chapter."""
    profile = get_profile(course_name, chapter_key)
    if profile:
        return Path("data/golden_chapters") / profile.seed_dir
    return Path("data/golden_chapters/math/probability_random_var_ch2")


def list_courses() -> list[str]:
    """List all registered course names."""
    return list(COURSE_PROFILES.keys())


def list_chapters(course_name: str) -> list[str]:
    """List chapter keys for a course."""
    course = COURSE_PROFILES.get(course_name, {})
    return list(course.keys())
