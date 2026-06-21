"""Formula quality validator — enforces FormulaRegistry on PDF output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.pdf_content_v2.formula_registry import get_registry


@dataclass
class FormulaReport:
    expected_formula_count: int = 0
    covered_formula_count: int = 0
    missing_formulas: list[str] = field(default_factory=list)
    unregistered_formula_count: int = 0
    formula_issue_count: int = 0
    latex_leak_count: int = 0
    condition_missing_count: int = 0
    duplicate_formula_variant_count: int = 0
    passed: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "expected_formula_count": self.expected_formula_count,
            "covered_formula_count": self.covered_formula_count,
            "missing_formulas": self.missing_formulas,
            "unregistered_formula_count": self.unregistered_formula_count,
            "formula_issue_count": self.formula_issue_count,
            "latex_leak_count": self.latex_leak_count,
            "condition_missing_count": self.condition_missing_count,
            "duplicate_formula_variant_count": self.duplicate_formula_variant_count,
            "passed": self.passed,
            "details": self.details,
        }


class FormulaValidator:
    """Validates that all formulas in generated PDFs come from the registry."""

    LATEX_LEAK_PATTERNS = [
        r'\\frac\{', r'\\sqrt\{', r'\\int_', r'\\sum_', r'\\begin\{',
        r'\\cdot', r'\\times', r'\\alpha', r'\\beta', r'\\lambda',
        r'\\varepsilon', r'\\infty', r'\\partial', r'\\nabla',
    ]
    POWER_NOTATION_LEAK = re.compile(r'(?<![\\$a-zA-Z])\^[0-9{\(]')  # raw ^ not inside math mode
    CONDITION_KEYWORDS = ["条件", "适用", "当", "其中", "要求"]

    def validate(
        self,
        course_id: str,
        typst_text: str,
        generated_formula_ids: list[str] | None = None,
    ) -> FormulaReport:
        """Run full formula validation on generated Typst content."""
        report = FormulaReport()
        registry = get_registry()

        expected_ids = registry.get_expected_ids(course_id)
        report.expected_formula_count = len(expected_ids)

        # ── 1. Expected formula coverage ──
        if generated_formula_ids is None:
            generated_formula_ids = self._extract_formula_ids(typst_text, expected_ids)

        report.covered_formula_count = len(generated_formula_ids)
        for fid in expected_ids:
            if fid not in generated_formula_ids:
                report.missing_formulas.append(fid)

        # ── 2. Unregistered formula detection ──
        report.unregistered_formula_count = self._count_unregistered(typst_text, expected_ids)

        # ── 3. LaTeX leak detection ──
        for pattern in self.LATEX_LEAK_PATTERNS:
            report.latex_leak_count += len(re.findall(pattern, typst_text))

        # ── 4. Power notation leaks (raw ^ outside math mode) ──
        report.latex_leak_count += len(self.POWER_NOTATION_LEAK.findall(typst_text))

        # ── 5. Condition missing check ──
        formula_blocks = re.findall(r'#formula-card\(', typst_text)
        condition_blocks = sum(1 for kw in self.CONDITION_KEYWORDS if kw in typst_text)
        if len(formula_blocks) > 0 and condition_blocks < len(formula_blocks):
            report.condition_missing_count = len(formula_blocks) - condition_blocks

        # ── 6. Duplicate variants ──
        report.duplicate_formula_variant_count = self._count_duplicate_variants(typst_text)

        # ── 7. Formula issue count (aggregate) ──
        report.formula_issue_count = (
            len(report.missing_formulas)
            + report.unregistered_formula_count
            + report.latex_leak_count
            + report.condition_missing_count
            + report.duplicate_formula_variant_count
        )

        # ── 8. Hard gate ──
        report.passed = (
            len(report.missing_formulas) == 0
            and report.unregistered_formula_count == 0
            and report.latex_leak_count == 0
            and report.condition_missing_count == 0
        )
        report.details = {
            "course_id": course_id,
            "registry_total": len(registry.all_formulas()),
            "registry_stats": registry.stats(course_id),
        }
        return report

    def _extract_formula_ids(self, text: str, expected_ids: list[str]) -> list[str]:
        """Extract which registered formulas are present in the text."""
        found = []
        registry = get_registry()
        for fid in expected_ids:
            formula = registry.lookup(fid)
            if not formula:
                continue
            # Check for formula title or display text presence
            if formula.title in text or formula.display_formula[:10] in text:
                found.append(fid)
            # Check Typst formula hint
            elif formula.typst_formula and formula.typst_formula[:15] in text:
                found.append(fid)
        return found

    def _count_unregistered(self, text: str, expected_ids: list[str]) -> int:
        """Detect formula-like strings that aren't in the registry."""
        # Find potential math blocks
        math_blocks = re.findall(r'\$[^$]+\$', text)
        unregistered = 0
        registry = get_registry()
        registered_texts = set()
        for fid in expected_ids:
            f = registry.lookup(fid)
            if f:
                registered_texts.add(f.display_formula[:10])
                registered_texts.add(f.typst_formula[:15])

        # Heuristic: flag math blocks containing common formula patterns
        # that aren't in our registry
        formula_indicators = [
            r'P\s*\\\{', r'F\s*\(', r'f\s*\(', r'E\s*\(', r'D\s*\(',
            r'\\int', r'\\sum', r'\\frac', r'\\sigma', r'\\mu',
            r'e\^', r'\\lambda', r'C_', r'\\Phi',
        ]
        for block in math_blocks:
            for indicator in formula_indicators:
                if re.search(indicator, block):
                    # Check if this block matches any registered formula
                    matched = False
                    for rt in registered_texts:
                        if rt and rt in block:
                            matched = True
                            break
                    if not matched:
                        unregistered += 1
                    break  # count each block once
        return unregistered

    def _count_duplicate_variants(self, text: str) -> int:
        """Detect if the same formula appears in multiple notations."""
        # Check for both LaTeX and plain notation of the same concept
        dupes = 0
        pairs = [
            (r'F\(x\)\s*=', r'F\s*\(x\)\s*='),  # spacing variants
            (r'e\^\{-', r'e\^\(-'),  # brace vs paren
            (r'\\int_', r'∫'),  # LaTeX vs Unicode integral
        ]
        for p1, p2 in pairs:
            if re.search(p1, text) and re.search(p2, text):
                dupes += 1
        return dupes
