"""RegFormulaCard — authoritative formula definition in the registry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegFormulaCard:
    """A single registered formula — the ONLY valid source for core formulas in PDF output.

    Fields:
        formula_id:       Unique ID, e.g. "prob_ch2_cdf"
        course_id:        e.g. "probability_ch2"
        chapter_id:       e.g. "ch2"
        concept_id:       e.g. "distribution_function"
        title:            Human-readable name, e.g. "分布函数"
        display_formula:  ASCII/Unicode display, e.g. "F(x)=P{X≤x}"
        typst_formula:    Typst math-mode text, e.g. "$F(x)=P{X<=x}$"
        plain_text:       Plain text description, e.g. "分布函数等于X不超过x的概率"
        conditions:       Applicability conditions
        common_variants:  Common variant forms
        common_mistakes:  Frequent student mistakes
        source_refs:      Where this formula was verified from
        source_level:     textbook / ppt / past_exam / ai_derived / web_retrieved
        exam_priority:    1-5 stars
    """
    formula_id: str
    course_id: str
    chapter_id: str
    concept_id: str
    title: str
    display_formula: str
    typst_formula: str
    plain_text: str
    conditions: list[str] = field(default_factory=list)
    common_variants: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    source_level: str = "textbook"
    exam_priority: str = "★★★"

    def to_dict(self) -> dict:
        return {
            "formula_id": self.formula_id, "course_id": self.course_id,
            "chapter_id": self.chapter_id, "concept_id": self.concept_id,
            "title": self.title, "display_formula": self.display_formula,
            "typst_formula": self.typst_formula, "plain_text": self.plain_text,
            "conditions": self.conditions, "common_variants": self.common_variants,
            "common_mistakes": self.common_mistakes, "source_refs": self.source_refs,
            "source_level": self.source_level, "exam_priority": self.exam_priority,
        }

    def typst_card(self) -> str:
        """Render a formula card block for Typst PDF output."""
        lines = [
            f'#formula-card("{self.title}", "{self.display_formula}", "{"; ".join(self.conditions) if self.conditions else "见教材"}")',
        ]
        if self.common_variants:
            lines.append(f'变体: {"; ".join(self.common_variants[:3])}')
        if self.common_mistakes:
            lines.append(f'易错: {"; ".join(self.common_mistakes[:3])}')
        lines.append(f'来源: {"; ".join(self.source_refs[:2]) or "教材"}')
        lines.append(f'优先级: {self.exam_priority}')
        return " | ".join(lines)
