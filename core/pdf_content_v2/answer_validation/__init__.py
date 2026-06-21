"""Answer Validation — math-backed answer verification for PDF 3.0."""

from core.pdf_content_v2.answer_validation.answer_validator import (
    AnswerValidator, ValidationResult, ValidatedQuestion,
)
from core.pdf_content_v2.answer_validation.probability_validator import ProbabilityValidator
from core.pdf_content_v2.answer_validation.field_wave_validator import FieldWaveValidator
from core.pdf_content_v2.answer_validation.digital_logic_validator import DigitalLogicValidator

VALIDATOR_MAP = {
    "math": ProbabilityValidator,
    "engineering": FieldWaveValidator,  # default for engineering
}
