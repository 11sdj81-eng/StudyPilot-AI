"""Question-first diagram binding for PDF v1.1 rebuild."""

from __future__ import annotations

from pathlib import Path

from core.config import ROOT_DIR
from core.diagram_policy_v2 import diagram_type_for_text, required_labels_for_diagram
from core.symbol_normalizer_v2 import normalize_figure_metadata_v2, scan_forbidden_visible_tokens


FIGURE_PATHS = {
    "高斯面": ROOT_DIR / "assets" / "generated" / "rc2_examples" / "gauss_ball.png",
    "镜像法": ROOT_DIR / "assets" / "generated" / "rc2_examples" / "image_sphere_q.png",
    "等位线": ROOT_DIR / "assets" / "generated" / "rc2_examples" / "potential_ab.png",
    "边界条件": ROOT_DIR / "assets" / "generated" / "selfcheck_boundary.png",
}


def bind_diagrams_to_questions(questions: list[dict]) -> tuple[list[dict], list[dict]]:
    figures: list[dict] = []
    results: list[dict] = []
    for index, question in enumerate(questions, start=1):
        diagram_type = question.get("needs_diagram") or diagram_type_for_text(question.get("title", ""))
        if not diagram_type:
            results.append({"question_id": question.get("id", f"Q{index}"), "passed": True, "reason": "no diagram required"})
            continue
        path = FIGURE_PATHS.get(diagram_type)
        exists = bool(path and Path(path).exists())
        fig = {
            "path": str(path) if exists else "",
            "title": f"{question.get('id', f'题 {index}')} {diagram_type}配图",
            "caption": f"配合“{question.get('title', '题目')}”理解关键几何关系与解题步骤。",
            "target_section": question.get("target_section") or question.get("id", f"题 {index}"),
            "source": "程序化教学矢量图",
            "linked_question_id": question.get("id", f"Q{index}"),
            "linked_knowledge_point": question.get("metadata", {}).get("knowledge_point", ""),
            "why_needed": f"{diagram_type}题无图容易丢失几何关系和方向判断。",
            "diagram_type": diagram_type,
            "contains_required_labels": required_labels_for_diagram(diagram_type),
            "generated": True,
        }
        forbidden = scan_forbidden_visible_tokens(" ".join(str(fig.get(k, "")) for k in fig))
        fig["symbol_check_passed"] = not forbidden
        if exists:
            figures.append(fig)
        results.append({
            "question_id": fig["linked_question_id"],
            "diagram_type": diagram_type,
            "passed": exists and fig["symbol_check_passed"],
            "path": str(path) if path else "",
            "contains_required_labels": fig["contains_required_labels"],
            "symbol_forbidden_hits": forbidden,
        })
    return normalize_figure_metadata_v2(figures), results
