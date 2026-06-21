"""Formula Registry — single source of truth for all core formulas."""

from core.pdf_content_v2.formula_registry.formula_card import RegFormulaCard
from core.pdf_content_v2.formula_registry.formula_registry import FormulaRegistry
from core.pdf_content_v2.formula_registry.probability_formulas import PROBABILITY_CH2_FORMULAS
from core.pdf_content_v2.formula_registry.field_wave_formulas import FIELD_WAVE_CH1_FORMULAS
from core.pdf_content_v2.formula_registry.digital_logic_formulas import DIGITAL_LOGIC_CH3_FORMULAS

_registry = FormulaRegistry()
_registry.register_all(PROBABILITY_CH2_FORMULAS)
_registry.register_all(FIELD_WAVE_CH1_FORMULAS)
_registry.register_all(DIGITAL_LOGIC_CH3_FORMULAS)


def get_registry() -> FormulaRegistry:
    return _registry


def lookup(formula_id: str) -> RegFormulaCard | None:
    return _registry.lookup(formula_id)


def get_formulas_for_concept(concept_id: str) -> list[RegFormulaCard]:
    return _registry.by_concept(concept_id)
