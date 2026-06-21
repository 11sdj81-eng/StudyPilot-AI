"""Question Style — fake question detection + real exam style enforcement."""

from core.pdf_content_v2.question_style.fake_question_detector import (
    FakeQuestionDetector, FakeQuestionResult,
)
from core.pdf_content_v2.question_style.exam_style_profile import (
    ExamStyleProfile, PROBABILITY_STYLE, FIELD_WAVE_STYLE, DIGITAL_LOGIC_STYLE,
)
from core.pdf_content_v2.question_style.exam_question_style_validator import (
    StyleValidator, StyleValidationReport,
)
from core.pdf_content_v2.question_style.real_question_rewriter import (
    RealQuestionRewriter, RewriteResult,
)
