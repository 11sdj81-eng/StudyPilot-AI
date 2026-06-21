"""Syllabus profile placeholder: 电磁场与电磁波 第一章 静电场."""

from core.pdf_content_v2.course_profiles.base import (
    CourseProfile, ExpectedConcept, ExpectedFormula, ExpectedQuestionType,
)

FIELD_WAVE_CH1_PROFILE = CourseProfile(
    course_id="field_wave_ch1",
    course_name="电磁场与电磁波",
    chapter_name="第一章 静电场",
    subject_type="engineering",
    expected_concepts=[
        ExpectedConcept(name="电场强度", english_key="electric_field", priority=5),
        ExpectedConcept(name="高斯定理", english_key="gauss_law", priority=5),
        ExpectedConcept(name="电位与梯度", english_key="potential_gradient", priority=5),
        ExpectedConcept(name="边界条件", english_key="boundary_conditions", priority=5),
        ExpectedConcept(name="镜像法", english_key="image_method", priority=4),
        ExpectedConcept(name="静电能量", english_key="electrostatic_energy", priority=3),
    ],
    expected_formulas=[
        ExpectedFormula(name="Coulomb", display_hint="E=Q/(4πε₀R²)", belongs_to="电场强度"),
        ExpectedFormula(name="Gauss Integral", display_hint="∫D·dS=Q", belongs_to="高斯定理"),
        ExpectedFormula(name="E=-∇φ", display_hint="E=-∇φ", belongs_to="电位与梯度"),
        ExpectedFormula(name="Tangential E", display_hint="E₁t=E₂t", belongs_to="边界条件"),
    ],
    expected_question_types=[
        ExpectedQuestionType(name="选择/填空题", typical_score_share=0.30),
        ExpectedQuestionType(name="简答/推导题", typical_score_share=0.20),
        ExpectedQuestionType(name="计算题", typical_score_share=0.30),
        ExpectedQuestionType(name="综合题", typical_score_share=0.20),
    ],
)
