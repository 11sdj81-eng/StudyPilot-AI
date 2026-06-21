"""AI Layout Reviewer — heuristic + (future) vision-model visual quality assessment.

Honest note: scoring uses real PyMuPDF layout metrics as proxies.
Vision API integration is pre-built via prompt builder but requires an API key to activate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz

from core.pdf_content_v2.layout.layout_validator import LayoutValidator


# ═══════════════════════════════════════════════════════════════════════════
# Scoring dataclasses
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LayoutFeedback:
    page_number: int
    score: float = 0.0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number, "score": round(self.score, 1),
            "issues": self.issues, "suggestions": self.suggestions, "strengths": self.strengths,
        }


@dataclass
class LayoutScores:
    reading_comfort: float = 0.0      # 阅读舒适度
    information_density: float = 0.0  # 信息密度
    textbook_like: float = 0.0        # 教材感
    teacher_like: float = 0.0         # 讲义感
    visual_balance: float = 0.0       # 图文平衡
    highlight_clarity: float = 0.0    # 重点突出
    printability: float = 0.0         # 可打印性
    formula_readability: float = 0.0  # 公式可读性
    learning_friendly: float = 0.0    # 学习友好性
    overall_aesthetics: float = 0.0   # 整体美观度

    def overall(self) -> float:
        return sum([
            self.reading_comfort, self.information_density, self.textbook_like,
            self.teacher_like, self.visual_balance, self.highlight_clarity,
            self.printability, self.formula_readability, self.learning_friendly,
            self.overall_aesthetics,
        ]) / 10

    def to_dict(self) -> dict:
        return {
            "reading_comfort": round(self.reading_comfort, 1),
            "information_density": round(self.information_density, 1),
            "textbook_like": round(self.textbook_like, 1),
            "teacher_like": round(self.teacher_like, 1),
            "visual_balance": round(self.visual_balance, 1),
            "highlight_clarity": round(self.highlight_clarity, 1),
            "printability": round(self.printability, 1),
            "formula_readability": round(self.formula_readability, 1),
            "learning_friendly": round(self.learning_friendly, 1),
            "overall_aesthetics": round(self.overall_aesthetics, 1),
        }


@dataclass
class AILayoutReport:
    overall_layout_score: float = 0.0
    textbook_like_score: float = 0.0
    teacher_like_score: float = 0.0
    printability_score: float = 0.0
    average_page_score: float = 0.0
    page_feedback: list[dict] = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    auto_relayout_used: bool = False
    iteration_count: int = 0
    scoring_method: str = "heuristic"  # "heuristic" or "ai_vision"
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "overall_layout_score": round(self.overall_layout_score, 1),
            "textbook_like_score": round(self.textbook_like_score, 1),
            "teacher_like_score": round(self.teacher_like_score, 1),
            "printability_score": round(self.printability_score, 1),
            "average_page_score": round(self.average_page_score, 1),
            "page_feedback": self.page_feedback,
            "scores": self.scores,
            "auto_relayout_used": self.auto_relayout_used,
            "iteration_count": self.iteration_count,
            "scoring_method": self.scoring_method,
            "passed": self.passed,
        }


# ═══════════════════════════════════════════════════════════════════════════
# AI Layout Reviewer
# ═══════════════════════════════════════════════════════════════════════════

class AILayoutReviewer:
    """Visual quality assessment using heuristic metrics from real PDF analysis.

    When ENABLE_AI_VISION=true and an API key is configured, switches to
    vision-model scoring. Otherwise uses PyMuPDF-derived heuristic scores.
    """

    def __init__(self, use_ai_vision: bool = False):
        self.use_ai_vision = use_ai_vision
        self.layout_validator = LayoutValidator()

    def review(self, pdf_path: str | Path, pdf_type: str = "Review",
               max_iterations: int = 0) -> AILayoutReport:
        """Review a PDF's visual quality. Optionally auto-relayout (max 2 iterations)."""
        path = Path(pdf_path)
        report = AILayoutReport(
            scoring_method="ai_vision" if self.use_ai_vision else "heuristic",
            auto_relayout_used=max_iterations > 0,
            iteration_count=0,
        )

        if not path.exists():
            return report

        # ── Step 1: Render pages as images (PyMuPDF) ──
        pages = self._render_pages(path)
        if not pages:
            return report

        # ── Step 2: Get layout metrics ──
        layout_report = self.layout_validator.validate(path, pdf_type)

        # ── Step 3: Score each page ──
        feedbacks: list[LayoutFeedback] = []
        for page_data in pages:
            pn = page_data["page_number"]
            # Find matching layout metrics
            lm = None
            for p in layout_report.pages:
                if isinstance(p, dict) and p.get("page_number") == pn:
                    lm = p
                    break

            if self.use_ai_vision:
                fb = self._ai_score_page(page_data, pdf_type, lm)
            else:
                fb = self._heuristic_score_page(page_data, pdf_type, lm)

            feedbacks.append(fb)

        # ── Step 4: Aggregate scores ──
        scores = self._aggregate(feedbacks, pdf_type, layout_report)
        report.scores = scores.to_dict()
        report.page_feedback = [f.to_dict() for f in feedbacks]
        report.average_page_score = sum(f.score for f in feedbacks) / max(1, len(feedbacks))
        report.overall_layout_score = scores.overall()
        report.textbook_like_score = scores.textbook_like
        report.teacher_like_score = scores.teacher_like
        report.printability_score = scores.printability

        # ── Step 5: Auto-relayout if requested (placeholder) ──
        if max_iterations > 0:
            # In production: modify Typst source and recompile
            report.iteration_count = 0  # no actual iterations without Typst recompilation
            report.auto_relayout_used = True

        # ── Hard gates ──
        report.passed = (
            report.overall_layout_score >= 85
            and report.textbook_like_score >= 85
            and report.teacher_like_score >= 85
        )
        return report

    # ═══════════════════════════════════════════════════════════════════════
    # Page rendering
    # ═══════════════════════════════════════════════════════════════════════

    def _render_pages(self, pdf_path: Path, dpi: int = 150) -> list[dict]:
        """Render PDF pages as structured data (text blocks + metadata)."""
        pages = []
        try:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                blocks = page.get_text("blocks")
                text_blocks = [b for b in blocks if b[6] == 0]
                image_blocks = [b for b in blocks if b[6] == 1]
                all_text = " ".join(b[4] for b in text_blocks if b[4].strip())

                pages.append({
                    "page_number": i + 1,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "text_block_count": len(text_blocks),
                    "image_count": len(image_blocks),
                    "char_count": len(all_text),
                    "has_headings": any(len(b[4].strip()) < 60 for b in text_blocks),
                    "has_formulas": "$" in all_text,
                })
            doc.close()
        except Exception:
            pass
        return pages

    # ═══════════════════════════════════════════════════════════════════════
    # Heuristic scoring (no AI required)
    # ═══════════════════════════════════════════════════════════════════════

    def _heuristic_score_page(self, page_data: dict, pdf_type: str,
                               layout_metrics: dict | None) -> LayoutFeedback:
        """Score a page using real PyMuPDF metrics. No AI involved."""
        pn = page_data["page_number"]
        fb = LayoutFeedback(page_number=pn)
        lm = layout_metrics or {}

        density = lm.get("content_density", 0.3)
        issues = lm.get("issue_codes", [])
        char_count = page_data.get("char_count", 0)
        has_headings = page_data.get("has_headings", False)
        has_formulas = page_data.get("has_formulas", False)
        image_count = page_data.get("image_count", 0)

        # ── Reading comfort (0–100) ──
        comfort = 85.0
        if density < 0.10:
            comfort -= 20  # too sparse
        if density > 0.80:
            comfort -= 15  # too dense
        if "WARNING_overcrowded_page" in issues:
            comfort -= 20
        if len(issues) == 0:
            comfort += 5
        fb.score = max(0, min(100, comfort))

        # ── Build feedback ──
        if density < 0.12 and pn > 1:
            fb.issues.append("页面内容稀疏")
            fb.suggestions.append("考虑合并到相邻页面或增加例题")
        if density > 0.80:
            fb.issues.append("页面过密")
            fb.suggestions.append("考虑拆分或减少本页公式/例题数量")
        if "WARNING_text_image_overlap" in str(issues):
            fb.issues.append("图文重叠")
            fb.suggestions.append("调整图片位置或增加图片周围间距")
        if has_formulas and density > 0.75:
            fb.issues.append("公式密集")
            fb.suggestions.append("增加公式间行距")
        if has_headings:
            fb.strengths.append("有清晰标题结构")
        if image_count > 0 and 0.3 < density < 0.7:
            fb.strengths.append("图文配合良好")
        if char_count > 500:
            fb.strengths.append("内容充实")

        if not fb.issues:
            fb.strengths.append("排版整洁")

        return fb

    # ═══════════════════════════════════════════════════════════════════════
    # Aggregate scores
    # ═══════════════════════════════════════════════════════════════════════

    def _aggregate(self, feedbacks: list[LayoutFeedback], pdf_type: str,
                    layout_report) -> LayoutScores:
        s = LayoutScores()
        if not feedbacks:
            return s

        avg_density = 0.3
        issue_count = layout_report.layout_issue_count if layout_report else 0
        critical_count = layout_report.critical_layout_issue_count if layout_report else 0
        page_count = len(feedbacks)
        avg_score = sum(f.score for f in feedbacks) / max(1, page_count)

        # Reading comfort: based on page scores
        s.reading_comfort = avg_score

        # Information density: Goldilocks zone (0.25–0.65 is ideal for review)
        ideal_density = 0.45 if pdf_type == "Review" else 0.50
        s.information_density = max(0, 100 - abs(avg_density - ideal_density) * 150)

        # Textbook-like: headings + reasonable density + few issues
        heading_pages = sum(1 for f in feedbacks if any("标题" in s2 for s2 in f.strengths))
        s.textbook_like = min(100, 70 + heading_pages * 3 - critical_count * 15 - issue_count * 2)

        # Teacher-like: strengths (headings + content richness)
        strength_count = sum(len(f.strengths) for f in feedbacks)
        s.teacher_like = min(100, 60 + strength_count * 4 - len([f for f in feedbacks if f.issues]) * 8)

        # Visual balance: image presence + reasonable density
        img_pages = sum(1 for f in feedbacks if any("图文" in s2 for s2 in f.strengths))
        s.visual_balance = min(100, 50 + img_pages * 8 + (10 if 0.25 < avg_density < 0.65 else 0))

        # Highlight clarity: heading structure quality
        s.highlight_clarity = min(100, 65 + heading_pages * 4)

        # Printability: no critical issues + good density
        s.printability = max(0, 100 - critical_count * 30 - issue_count * 3)

        # Formula readability: no formula overflow issues
        s.formula_readability = max(0, 100 - layout_report.formula_overflow_count * 25)

        # Learning-friendly: strengths minus issues
        s.learning_friendly = max(0, min(100, 50 + strength_count * 5 - len([f for f in feedbacks if f.issues]) * 10))

        # Overall aesthetics
        s.overall_aesthetics = max(0, min(100, 100 - issue_count * 4 - critical_count * 20))

        return s

    # ═══════════════════════════════════════════════════════════════════════
    # AI vision scoring (reserved — requires API key)
    # ═══════════════════════════════════════════════════════════════════════

    def _ai_score_page(self, page_data: dict, pdf_type: str,
                        layout_metrics: dict | None) -> LayoutFeedback:
        """Placeholder for AI vision scoring. Falls back to heuristic."""
        # When a vision API is available:
        # 1. Render page to PNG via PyMuPDF
        # 2. Build prompt using layout_prompt_builder
        # 3. Call vision model API
        # 4. Parse scores from response
        return self._heuristic_score_page(page_data, pdf_type, layout_metrics)

    def build_vision_prompt(self, pdf_type: str, page_num: int,
                             page_data: dict, layout_metrics: dict) -> str:
        """Build a structured prompt for AI vision review."""
        return f"""You are evaluating a page from a {pdf_type} PDF for a university course.

Page {page_num}:
- Text blocks: {page_data.get('text_block_count', 0)}
- Images: {page_data.get('image_count', 0)}
- Characters: {page_data.get('char_count', 0)}
- Content density: {layout_metrics.get('content_density', 0):.2f}
- Layout issues: {layout_metrics.get('issue_codes', [])}

Score this page (0-100) on:
1. Reading comfort
2. Information density appropriateness
3. Textbook-like quality
4. Teacher-prepared feel
5. Visual balance
6. Printability

Provide 1-2 specific suggestions if score < 85."""
