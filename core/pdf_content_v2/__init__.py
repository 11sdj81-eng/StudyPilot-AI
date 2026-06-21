"""Evidence-first PDF content pipeline for StudyPilot PDF 2.0."""

from core.pdf_content_v2.builder import build_evidence_deck
from core.pdf_content_v2.models import (
    ConceptCard,
    ExamPatternCard,
    ExampleCard,
    LectureDocument,
    LectureSection,
    MarginNote,
    SourceRef,
)
from core.pdf_content_v2.quality_gate import PDFContentQualityGate
from core.pdf_content_v2.renderer import render_all_pdf_v2

__all__ = [
    "ConceptCard",
    "ExamPatternCard",
    "ExampleCard",
    "LectureDocument",
    "LectureSection",
    "MarginNote",
    "PDFContentQualityGate",
    "SourceRef",
    "build_evidence_deck",
    "render_all_pdf_v2",
]
