"""Formula access service for StudyPilot v2.0 object rendering."""

from __future__ import annotations

from core.study_objects import FormulaCard, StudyDocument


REQUIRED_FORMULA_IDS = [
    "gauss_law_integral",
    "uniform_sphere_inside",
    "uniform_sphere_outside",
    "potential_gradient_formula",
    "boundary_tangential_e",
    "boundary_normal_d",
    "image_plane_potential",
    "electrostatic_energy_density",
]


class FormulaRenderError(ValueError):
    pass


def validate_formula_db(formulas: dict[str, FormulaCard]) -> None:
    missing = [fid for fid in REQUIRED_FORMULA_IDS if fid not in formulas]
    if missing:
        raise FormulaRenderError("formula_db 缺少必要公式：" + "、".join(missing))
    invalid = [
        fid for fid, formula in formulas.items()
        if not str(formula.latex or "").strip() or not str(formula.display_text or "").strip()
    ]
    if invalid:
        raise FormulaRenderError("formula_db 存在空公式：" + "、".join(invalid))


def render_formula(formula_id: str, document: StudyDocument) -> str:
    formula = document.formulas.get(formula_id)
    if formula is None:
        raise FormulaRenderError(f"公式不存在：{formula_id}")
    text = str(formula.display_text or "").strip()
    if not text:
        raise FormulaRenderError(f"公式 display_text 为空：{formula_id}")
    return text


def render_formula_list(formula_ids: list[str], document: StudyDocument) -> str:
    rendered = [render_formula(fid, document) for fid in formula_ids if fid in document.formulas]
    if not rendered:
        raise FormulaRenderError("公式列表为空")
    return "；".join(rendered)
