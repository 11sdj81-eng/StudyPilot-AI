"""Registered formulas: 数字电路逻辑设计 第三章 组合逻辑电路 (placeholder)."""

from core.pdf_content_v2.formula_registry.formula_card import RegFormulaCard

COURSE = "digital_logic_ch3"
CHAPTER = "ch3"

DIGITAL_LOGIC_CH3_FORMULAS: list[RegFormulaCard] = [
    RegFormulaCard(
        formula_id="dl_ch3_demorgan", course_id=COURSE, chapter_id=CHAPTER,
        concept_id="boolean_algebra", title="De Morgan 定理",
        display_formula="(AB)' = A' + B',  (A+B)' = A'B'",
        typst_formula="$(A B)' = A' + B', quad (A+B)' = A' B'$",
        plain_text="与或互换取反", conditions=["适用于布尔代数"],
        common_variants=["多变量: (ABC)' = A'+B'+C'"],
        common_mistakes=["忘记括号", "直接对偶不取反"],
        source_refs=["数字电路逻辑设计 §3.2"], source_level="textbook", exam_priority="★★★★",
    ),
    RegFormulaCard(
        formula_id="dl_ch3_minterm", course_id=COURSE, chapter_id=CHAPTER,
        concept_id="karnaugh_map", title="最小项表达式",
        display_formula="F = Σm(0,1,3,7)", typst_formula="$F = Sigma m(0,1,3,7)$",
        plain_text="用最小项之和表示逻辑函数", conditions=["每个最小项对应一个输入组合"],
        source_refs=["数字电路逻辑设计 §3.3"], source_level="textbook", exam_priority="★★★★",
    ),
]
