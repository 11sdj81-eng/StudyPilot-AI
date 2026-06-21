"""Syllabus profile placeholder: 数字电路逻辑设计 第三章 组合逻辑电路."""

from core.pdf_content_v2.course_profiles.base import (
    CourseProfile, ExpectedConcept, ExpectedFormula, ExpectedQuestionType,
)

DIGITAL_LOGIC_CH3_PROFILE = CourseProfile(
    course_id="digital_logic_ch3",
    course_name="数字电路逻辑设计",
    chapter_name="第三章 组合逻辑电路",
    subject_type="engineering",
    expected_concepts=[
        ExpectedConcept(name="组合逻辑基础", english_key="combinational_logic", priority=5),
        ExpectedConcept(name="逻辑代数与化简", english_key="boolean_algebra", priority=5),
        ExpectedConcept(name="卡诺图", english_key="karnaugh_map", priority=4),
        ExpectedConcept(name="编码器与译码器", english_key="encoder_decoder", priority=4),
        ExpectedConcept(name="数据选择器", english_key="multiplexer", priority=3),
        ExpectedConcept(name="加法器与比较器", english_key="adder_comparator", priority=4),
    ],
    expected_formulas=[
        ExpectedFormula(name="De Morgan", display_hint="(AB)'=A'+B'", belongs_to="逻辑代数与化简"),
        ExpectedFormula(name="最小项表达式", display_hint="Σm", belongs_to="卡诺图"),
    ],
    expected_question_types=[
        ExpectedQuestionType(name="选择/填空题", typical_score_share=0.30),
        ExpectedQuestionType(name="逻辑化简", typical_score_share=0.20),
        ExpectedQuestionType(name="电路分析", typical_score_share=0.20),
        ExpectedQuestionType(name="设计题", typical_score_share=0.30),
    ],
)
