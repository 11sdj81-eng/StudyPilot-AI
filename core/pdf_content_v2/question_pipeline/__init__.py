"""Real Question Pipeline — eliminates template questions via exam pattern library."""

from core.pdf_content_v2.question_pipeline.exam_pattern_library import (
    ExamPatternLibrary, ExamPattern, get_library,
)
from core.pdf_content_v2.question_pipeline.question_source_priority import (
    QuestionSource, SourcePriority, get_source_priority,
)
from core.pdf_content_v2.question_pipeline.real_question_validator import (
    RealQuestionValidator, RealQuestionReport,
)
