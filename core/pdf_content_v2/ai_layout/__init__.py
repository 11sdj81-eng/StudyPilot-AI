"""AI Layout Reviewer — visual quality assessment for PDF 3.0.

Currently uses heuristic scoring from real PyMuPDF metrics.
AI vision scoring is reserved for when a vision model API is available.
"""

from core.pdf_content_v2.ai_layout.ai_layout_reviewer import (
    AILayoutReviewer, LayoutScores, LayoutFeedback, AILayoutReport,
)
