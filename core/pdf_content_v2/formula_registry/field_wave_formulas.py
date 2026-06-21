"""Registered formulas: 电磁场与电磁波 第一章 静电场 (placeholder)."""

from core.pdf_content_v2.formula_registry.formula_card import RegFormulaCard

COURSE = "field_wave_ch1"
CHAPTER = "ch1"

FIELD_WAVE_CH1_FORMULAS: list[RegFormulaCard] = [
    RegFormulaCard(
        formula_id="fw_ch1_coulomb", course_id=COURSE, chapter_id=CHAPTER,
        concept_id="electric_field", title="库仑定律 / 点电荷电场",
        display_formula="E = Q/(4πε₀R²) R̂", typst_formula="$bold(E) = Q\\/(4 pi epsilon_0 R^2) bold(R)_hat$",
        plain_text="点电荷电场强度随距离平方衰减", conditions=["真空点电荷", "R 为源点到场点距离"],
        common_variants=["连续分布: E=∫(ρdV)/(4πε₀R²)R̂"],
        common_mistakes=["忘记方向矢量", "距离二次方写成一次方"],
        source_refs=["电磁场与电磁波 §1.2"], source_level="textbook", exam_priority="★★★★★",
    ),
    RegFormulaCard(
        formula_id="fw_ch1_gauss", course_id=COURSE, chapter_id=CHAPTER,
        concept_id="gauss_law", title="高斯定理",
        display_formula="∫_S D·dS = Q", typst_formula="$integral_S bold(D) dot dif bold(S) = Q$",
        plain_text="闭合曲面的电位移通量等于包围的自由电荷", conditions=["闭合曲面", "右侧为包围自由电荷"],
        common_variants=["球对称: E=Qr/(4πε₀a³) (r<a)", "球对称: E=Q/(4πε₀r²) (r>a)"],
        common_mistakes=["没有对称性硬提场强", "球内包围电荷写成总电荷"],
        source_refs=["电磁场与电磁波 §1.3"], source_level="textbook", exam_priority="★★★★★",
    ),
    RegFormulaCard(
        formula_id="fw_ch1_potential", course_id=COURSE, chapter_id=CHAPTER,
        concept_id="potential_gradient", title="电位与电场关系",
        display_formula="E = -∇φ", typst_formula="$bold(E) = -nabla phi$",
        plain_text="电场方向是电位下降最快方向", conditions=["静电场无旋"],
        common_variants=["点电荷: φ=Q/(4πε₀R)"],
        common_mistakes=["漏掉负号", "认为电位为零处电场为零"],
        source_refs=["电磁场与电磁波 §1.4"], source_level="textbook", exam_priority="★★★★★",
    ),
    RegFormulaCard(
        formula_id="fw_ch1_boundary", course_id=COURSE, chapter_id=CHAPTER,
        concept_id="boundary_conditions", title="边界条件",
        display_formula="E₁t=E₂t,  D₁n-D₂n=ρₛ", typst_formula="$E_(1t)=E_(2t), quad D_(1n)-D_(2n)=rho_s$",
        plain_text="切向E连续，法向D跳变等于自由面电荷密度", conditions=["静电场分界面"],
        common_variants=["无自由面电荷: D₁n=D₂n"],
        common_mistakes=["把法向E写成连续", "把切向D写成连续"],
        source_refs=["电磁场与电磁波 §1.5"], source_level="textbook", exam_priority="★★★★★",
    ),
]
