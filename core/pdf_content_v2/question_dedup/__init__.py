"""Question Deduplication — 4-level duplicate detection for PDF 3.0."""

from core.pdf_content_v2.question_dedup.question_fingerprint import QuestionFingerprint
from core.pdf_content_v2.question_dedup.question_deduplicator import (
    QuestionDeduplicator, DuplicateReport, DuplicateLevel, DuplicatePair,
)
