"""FigureMatcher —— Match extracted figures to concepts via keyword analysis.

Uses OCR text, filename, page context, nearby text, and tags to assign
concept_id and match_score to each FigureObject.
"""

from __future__ import annotations

from typing import Any

from core.figure_engine.figure_objects import FigureObject, ConceptId


# Keyword database per concept (Chinese + English)
CONCEPT_KEYWORDS: dict[str, list[str]] = {
    ConceptId.GAUSS_LAW: [
        # Chinese
        "高斯", "通量", "闭合面", "包围电荷", "球对称", "电位移",
        "高斯面", "高斯定理", "对称性", "均匀带电", "球体", "圆柱",
        "线电荷", "面电荷", "D·dS", "自由电荷", "介电常数", "ε",
        # English
        "gauss", "flux", "closed surface", "enclosed charge",
        "Gaussian surface", "D·dS", "spherical symmetry", "εr",
    ],
    ConceptId.MIRROR_METHOD: [
        # Chinese
        "镜像", "接地", "导体平面", "像电荷", "V=0", "导体",
        "接地平面", "接地球", "镜像法", "等效电荷", "镜像电荷",
        "real charge", "image charge", "对称平面",
        # English
        "image charge", "grounded", "mirror", "conductor plane",
        "V=0", "boundary V=0",
    ],
    ConceptId.BOUNDARY_CONDITION: [
        # Chinese
        "边界条件", "介质", "法向", "切向", "ρs", "Dn", "Et",
        "分界面", "跳变", "连续", "边界", "面电荷密度",
        "边值关系", "衔接条件", "电位移矢量",
        # English
        "boundary condition", "interface", "normal", "tangential",
        "dielectric", "continuity", "jump",
    ],
    ConceptId.POTENTIAL_GRADIENT: [
        # Chinese
        "电位", "梯度", "等位线", "负梯度", "∇φ", "电势",
        "电位函数", "偏导", "等位面", "电场线", "E=-∇φ",
        # English
        "potential", "gradient", "equipotential", "∇φ",
        "E=-∇φ", "voltage",
    ],
    ConceptId.ELECTRIC_FIELD: [
        # Chinese
        "电场强度", "场线", "点电荷", "试验电荷", "电场",
        "电场力", "E线", "库仑力", "场强", "电力线",
        # English
        "electric field", "field lines", "point charge",
        "coulomb", "field intensity", "force",
    ],
    ConceptId.ELECTROSTATIC_ENERGY: [
        # Chinese
        "静电能量", "能量密度", "电容器", "D·E", "场能",
        "能量", "储能", "电容", "1/2", "wₑ",
        # English
        "energy", "energy density", "capacitor",
        "electrostatic energy", "stored energy",
    ],
}

# Source type weighting for match confidence
SOURCE_TYPE_MATCH_BONUS: dict[str, float] = {
    "textbook": 0.10,
    "ppt": 0.08,
    "past_paper": 0.05,
    "note": 0.02,
}


class FigureMatcher:
    """Match figures to concepts via keyword-based text analysis."""

    def __init__(self):
        self._match_log: list[dict[str, Any]] = []

    def match_figure(self, figure: FigureObject) -> FigureObject:
        """Assign concept_id and match_score to a single figure."""
        scores: dict[str, float] = {}

        for concept_id, keywords in CONCEPT_KEYWORDS.items():
            score = self._compute_match_score(figure, keywords)
            if score > 0:
                bonus = SOURCE_TYPE_MATCH_BONUS.get(figure.source_type, 0.0)
                scores[concept_id] = score + bonus

        if scores:
            best_concept = max(scores, key=scores.get)
            best_score = round(min(scores[best_concept], 1.0), 4)
            figure.concept_id = best_concept
            figure.match_score = best_score

            self._match_log.append({
                "figure_id": figure.figure_id,
                "concept_id": best_concept,
                "match_score": best_score,
                "all_scores": scores,
            })

        return figure

    def match_all(self, figures: list[FigureObject]) -> list[FigureObject]:
        """Match all figures to concepts."""
        self._match_log = []
        return [self.match_figure(f) for f in figures]

    def _compute_match_score(self, figure: FigureObject, keywords: list[str]) -> float:
        """Compute keyword match score for a figure against a concept's keywords."""
        search_text = self._build_search_text(figure)
        if not search_text:
            return 0.0

        hits = 0
        total_weight = len(keywords)
        for kw in keywords:
            if kw.lower() in search_text:
                hits += 1

        if hits == 0:
            return 0.0

        # Score = hit ratio, boosted by tag overlap
        score = hits / total_weight

        # Boost if tags already contain related keywords
        tag_hits = sum(1 for kw in keywords if kw.lower() in [t.lower() for t in figure.tags])
        score += tag_hits * 0.05

        return min(score, 0.95)

    def _build_search_text(self, figure: FigureObject) -> str:
        """Build a combined searchable text from all figure metadata."""
        parts: list[str] = []

        if figure.caption:
            parts.append(figure.caption)
        if figure.ocr_text:
            parts.append(figure.ocr_text)
        parts.append(figure.source_file)
        parts.extend(figure.tags)
        if figure.metadata.get("slide_title"):
            parts.append(figure.metadata["slide_title"])

        return " ".join(parts).lower()

    def get_match_log(self) -> list[dict[str, Any]]:
        """Return the match log from the last match_all call."""
        return self._match_log


def build_concept_filename_map() -> dict[str, list[str]]:
    """Build a mapping from concept_id to filename patterns (for reference)."""
    return {
        ConceptId.GAUSS_LAW: ["gauss", "高斯", "通量"],
        ConceptId.MIRROR_METHOD: ["mirror", "image_", "镜像", "接地"],
        ConceptId.BOUNDARY_CONDITION: ["boundary", "边界", "介质"],
        ConceptId.POTENTIAL_GRADIENT: ["potential", "gradient", "电位", "梯度"],
        ConceptId.ELECTRIC_FIELD: ["electric_field", "电场", "field_line", "场线"],
        ConceptId.ELECTROSTATIC_ENERGY: ["energy", "能量", "电容"],
    }
