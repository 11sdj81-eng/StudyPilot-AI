"""Knowledge Coverage Validator for PDF 3.0.

Checks generated content against syllabus-level CourseProfile.
Discovers "AI didn't cover ≠ won't be tested" gaps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.course_profiles.base_profile import BaseCourseProfile
from core.course_profiles.profile_registry import get_profile as get_unified_profile
from core.pdf_content_v2.models import ConceptCard, FormulaCard, ExampleCard


SOURCE_PRIORITY = ["textbook", "ppt", "past_exam", "ai_derived", "web_retrieved"]


@dataclass
class CoverageGap:
    """A single missing coverage item."""
    item_type: str  # concept / formula / question_type
    item_name: str
    fill_source: str = ""       # where auto-fill came from
    fill_confidence: float = 0.0
    filled: bool = False

    def to_dict(self) -> dict:
        return {
            "item_type": self.item_type, "item_name": self.item_name,
            "fill_source": self.fill_source, "fill_confidence": self.fill_confidence,
            "filled": self.filled,
        }


@dataclass
class CoverageReport:
    """Full coverage validation report."""
    expected_concepts: int = 0
    covered_concepts: int = 0
    missing_concepts: list[str] = field(default_factory=list)
    concept_coverage_rate: float = 0.0

    expected_formulas: int = 0
    covered_formulas: int = 0
    missing_formulas: list[str] = field(default_factory=list)
    formula_coverage_rate: float = 0.0

    expected_question_types: int = 0
    covered_question_types: int = 0
    missing_question_types: list[str] = field(default_factory=list)
    question_type_coverage_rate: float = 0.0

    overall_coverage_rate: float = 0.0
    coverage_passed: bool = False
    gaps: list[CoverageGap] = field(default_factory=list)
    auto_fill_attempted: bool = False
    auto_fill_success_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _str(v):
            return v if isinstance(v, str) else getattr(v, "name", str(v)) if hasattr(v, "name") else str(v)
        return {
            "expected_concepts": self.expected_concepts,
            "covered_concepts": self.covered_concepts,
            "missing_concepts": [_str(m) for m in self.missing_concepts],
            "concept_coverage_rate": round(self.concept_coverage_rate, 4),
            "expected_formulas": self.expected_formulas,
            "covered_formulas": self.covered_formulas,
            "missing_formulas": [_str(m) for m in self.missing_formulas],
            "formula_coverage_rate": round(self.formula_coverage_rate, 4),
            "expected_question_types": self.expected_question_types,
            "covered_question_types": self.covered_question_types,
            "missing_question_types": [_str(m) for m in self.missing_question_types],
            "question_type_coverage_rate": round(self.question_type_coverage_rate, 4),
            "overall_coverage_rate": round(self.overall_coverage_rate, 4),
            "coverage_passed": self.coverage_passed,
            "gaps": [g.to_dict() for g in self.gaps],
            "auto_fill_attempted": self.auto_fill_attempted,
            "auto_fill_success_count": self.auto_fill_success_count,
            "warnings": self.warnings,
        }


class CoverageValidator:
    """Validate that generated content covers the syllabus-level profile.

    NEVER silently skips validation. If no explicit profile exists,
    uses GenericCourseProfile as mandatory fallback.
    """

    def __init__(self, profile: BaseCourseProfile | None = None, course_id: str = ""):
        self.profile = profile
        self.course_id = course_id

    def validate(
        self,
        concepts: list[ConceptCard] | list[dict],
        formulas: list[FormulaCard] | list[dict] | None = None,
        examples: list[ExampleCard] | list[dict] | None = None,
        typst_text: str = "",
        filenames: list[str] | None = None,
    ) -> CoverageReport:
        """Compare generated content against the syllabus profile.

        If no profile provided, auto-loads from unified registry.
        GenericCourseProfile is used as mandatory fallback for unknown courses.
        Validation is NEVER silently skipped.
        """
        if not self.profile and self.course_id:
            self.profile = get_unified_profile(self.course_id, filenames=filenames)
        if not self.profile:
            return CoverageReport(warnings=["No CourseProfile and no course_id — cannot validate coverage"])

        report = CoverageReport()

        # ── 1. Concept coverage ──
        concept_text = self._collect_concept_text(concepts, typst_text)
        report.expected_concepts = len(self.profile.expected_concepts)
        covered, missing = self._match_items(
            self.profile.expected_concepts, concept_text, item_type="concept"
        )
        report.covered_concepts = len(covered)
        report.missing_concepts = list(missing) if missing else []
        report.concept_coverage_rate = (
            report.covered_concepts / report.expected_concepts
            if report.expected_concepts > 0 else 1.0
        )

        # ── 2. Formula coverage ──
        formula_text = self._collect_formula_text(formulas, typst_text)
        report.expected_formulas = len(self.profile.expected_formulas)
        f_covered, f_missing = self._match_items(
            self.profile.expected_formulas, formula_text, item_type="formula"
        )
        report.covered_formulas = len(f_covered)
        report.missing_formulas = list(f_missing) if f_missing else []
        report.formula_coverage_rate = (
            report.covered_formulas / report.expected_formulas
            if report.expected_formulas > 0 else 1.0
        )

        # ── 3. Question type coverage ──
        qtype_text = self._collect_question_text(examples, typst_text)
        report.expected_question_types = len(self.profile.expected_question_types)
        q_covered, q_missing = self._match_items(
            self.profile.expected_question_types, qtype_text, item_type="question_type"
        )
        report.covered_question_types = len(q_covered)
        report.missing_question_types = list(q_missing) if q_missing else []
        report.question_type_coverage_rate = (
            report.covered_question_types / report.expected_question_types
            if report.expected_question_types > 0 else 1.0
        )

        # ── 4. Overall ──
        report.overall_coverage_rate = (
            (report.concept_coverage_rate + report.formula_coverage_rate + report.question_type_coverage_rate) / 3
        )
        report.coverage_passed = report.overall_coverage_rate >= (self.profile.coverage_threshold or 0.95)

        # ── 5. Gaps ──
        for m in missing:
            name = m if isinstance(m, str) else getattr(m, "name", str(m))
            report.gaps.append(CoverageGap(item_type="concept", item_name=name, filled=False))
        for m in f_missing:
            name = m if isinstance(m, str) else getattr(m, "name", str(m))
            report.gaps.append(CoverageGap(item_type="formula", item_name=name, filled=False))
        for m in q_missing:
            name = m if isinstance(m, str) else getattr(m, "name", str(m))
            report.gaps.append(CoverageGap(item_type="question_type", item_name=name, filled=False))

        return report

    def auto_fill(self, report: CoverageReport, concepts_data: list[dict] | None = None) -> CoverageReport:
        """Attempt to fill coverage gaps using source priority: 教材 > AI > 联网.

        Currently: marks gaps with best available source level.
        Future: can invoke LLM for AI_DERIVED or web search for WEB_RETRIEVED.
        """
        report.auto_fill_attempted = True
        filled = 0

        for gap in report.gaps:
            if gap.filled:
                filled += 1
                continue

            # Check if this gap is a concept that's covered by a broader concept card
            # (e.g. "0-1分布" covered by "常见离散分布" card)
            if gap.item_type == "concept":
                # Try broader match
                broader_match = self._find_broader_coverage(gap.item_name, concepts_data or [])
                if broader_match:
                    gap.fill_source = f"textbook (broader: {broader_match})"
                    gap.fill_confidence = 0.75
                    gap.filled = True
                    filled += 1
                    continue

            # Can't fill — mark for AI_DERIVED
            if not gap.filled:
                gap.fill_source = "ai_derived"
                gap.fill_confidence = 0.50  # lower confidence because AI-generated
                gap.filled = True  # marked as fillable even if not actually generated
                filled += 1

        report.auto_fill_success_count = filled

        # Recalculate overall rate after auto-fill
        still_missing = sum(1 for g in report.gaps if g.fill_confidence < 0.6)
        report.overall_coverage_rate = max(
            0.0,
            1.0 - (still_missing / max(1, report.expected_concepts + report.expected_formulas + report.expected_question_types))
        )
        report.coverage_passed = report.overall_coverage_rate >= (self.profile.coverage_threshold if self.profile else 0.95)
        return report

    # ── Internal ──────────────────────────────────────────────────────────

    def _collect_concept_text(self, concepts, typst_text: str) -> str:
        """Build a combined text representation for concept matching."""
        parts = [typst_text]
        for c in concepts:
            if isinstance(c, dict):
                parts.append(c.get("title", ""))
                parts.append(c.get("explanation", ""))
                parts.append(c.get("definition", ""))
            elif hasattr(c, "title"):
                parts.append(c.title)
                parts.append(c.explanation)
        return " ".join(parts).lower()

    def _collect_formula_text(self, formulas, typst_text: str) -> str:
        parts = [typst_text]
        if formulas:
            for f in formulas:
                if isinstance(f, dict):
                    parts.append(f.get("title", ""))
                    parts.append(f.get("display_text", ""))
                elif hasattr(f, "title"):
                    parts.append(f.title)
                    parts.append(f.display_text)
        return " ".join(parts).lower()

    def _collect_question_text(self, examples, typst_text: str) -> str:
        parts = [typst_text]
        if examples:
            for e in examples:
                if isinstance(e, dict):
                    parts.append(e.get("problem", ""))
                    parts.append(e.get("question_type", ""))
                elif hasattr(e, "problem"):
                    parts.append(e.problem)
                    parts.append(e.question_type)
        return " ".join(parts).lower()

    def _match_items(self, expected: list, text: str, item_type: str = "concept") -> tuple[list, list]:
        """Match expected items (strings or ExpectedConcept objects) against generated text."""
        covered = []
        missing = []
        for item in expected:
            # Handle both string items and ExpectedConcept objects
            if isinstance(item, str):
                name = item.lower()
                display = ""
                latex = ""
            elif hasattr(item, "name"):
                name = item.name.lower()
                display = getattr(item, "display_hint", "") or ""
                latex = getattr(item, "latex_hint", "") or ""
            else:
                name = str(item).lower()
                display = ""
                latex = ""

            if name and name in text:
                covered.append(item)
                continue
            if display and display.lower() in text:
                covered.append(item)
                continue
            if latex and latex.lower() in text:
                covered.append(item)
                continue
            if item_type == "concept" and len(name) >= 3:
                key = name.replace("分布", "").replace("随机", "").strip()
                if len(key) >= 2 and key in text:
                    covered.append(item)
                    continue
            missing.append(item)
        return covered, missing

    def _find_broader_coverage(self, concept_name: str, concepts_data: list[dict]) -> str | None:
        """Check if a missing concept is implicitly covered by a broader concept card."""
        # Maps specific concepts to their broader concept container
        broader_map = {
            "0-1分布": "常见离散分布",
            "几何分布": "常见离散分布",
            "超几何分布": "常见离散分布",
            "二项分布": "常见离散分布",
            "泊松分布": "常见离散分布",
            "均匀分布": "常见连续分布",
            "指数分布": "常见连续分布",
            "正态分布": "常见连续分布",
        }
        broader = broader_map.get(concept_name)
        if not broader:
            return None
        for c in concepts_data:
            title = c.get("title", "") if isinstance(c, dict) else getattr(c, "title", "")
            if broader in str(title):
                return broader
        return None


def build_coverage_warning(report: CoverageReport) -> str:
    """Build a PDF-cover warning block if coverage is incomplete."""
    if report.coverage_passed:
        return ""

    lines = [
        "#block-title(\"知识覆盖警告\")",
        "",
        "以下知识点在当前生成内容中未充分覆盖，建议补充资料：",
        "",
    ]
    for gap in report.gaps:
        if not gap.filled or gap.fill_confidence < 0.6:
            source_note = f" (来源: {gap.fill_source})" if gap.fill_source else ""
            lines.append(f"- {gap.item_name}{source_note}")

    if report.auto_fill_attempted:
        filled_count = sum(1 for g in report.gaps if g.filled and g.fill_confidence >= 0.6)
        lines.append("")
        lines.append(f"已自动补全 {filled_count} 项（置信度 ≥ 0.6）。")
        lines.append("其余建议通过上传教材或真题补充。")

    lines.append(f"当前覆盖率: {report.overall_coverage_rate:.1%}")
    return "\n".join(lines)
