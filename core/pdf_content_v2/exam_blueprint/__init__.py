"""Exam Blueprint System — real exam structure for MockExam generation."""

from core.pdf_content_v2.exam_blueprint.exam_blueprint import (
    ExamBlueprint, ExamSectionBlueprint, BlueprintSource,
)
from core.pdf_content_v2.exam_blueprint.exam_blueprint_registry import (
    ExamBlueprintRegistry, PROBABILITY_CH2_BLUEPRINT,
    FIELD_WAVE_CH1_BLUEPRINT, DIGITAL_LOGIC_CH3_BLUEPRINT,
)
from core.pdf_content_v2.exam_blueprint.exam_blueprint_validator import (
    ExamBlueprintValidator, BlueprintValidationReport,
)
