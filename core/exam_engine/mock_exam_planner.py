"""Mock exam planner driven by exam patterns."""

from __future__ import annotations

from core.exam_engine.exam_pattern import ExamPattern


def plan_mock_exam(patterns: list[ExamPattern]) -> list[ExamPattern]:
    by_id = {p.pattern_id: p for p in patterns}
    preferred = [
        "choice_gauss_symmetry",
        "choice_potential_component",
        "choice_boundary_surface_charge",
        "choice_image_model",
        "choice_energy_density",
        "fill_sphere_enclosed_charge",
        "fill_potential_direction",
        "fill_boundary_jump",
        "fill_image_distance",
        "fill_energy_ratio",
        "short_gauss_reason",
        "short_boundary_origin",
        "gauss_piecewise_compute",
        "image_plane_comprehensive",
    ]
    if all(item in by_id for item in preferred):
        return [by_id[item] for item in preferred]
    selected: list[ExamPattern] = []
    for qtype, count in [("choice", 5), ("fill", 5), ("short", 2), ("compute", 1), ("comprehensive", 1)]:
        pool = [p for p in patterns if p.question_type == qtype]
        pool.sort(key=lambda p: (-p.difficulty, p.pattern_id))
        selected.extend(pool[:count])
    selected.sort(key=_mock_order)
    return selected


def _mock_order(pattern: ExamPattern) -> tuple[int, str]:
    rank = {"choice": 1, "fill": 2, "short": 3, "compute": 4, "comprehensive": 5}
    return (rank.get(pattern.question_type, 9), pattern.pattern_id)
