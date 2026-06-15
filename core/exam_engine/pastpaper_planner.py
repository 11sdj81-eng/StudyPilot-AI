"""Past paper case planner for v4.1."""

from __future__ import annotations

from core.exam_engine.exam_pattern import ExamPattern


def plan_pastpaper_cases(patterns: list[ExamPattern]) -> list[ExamPattern]:
    wanted = ["gauss_piecewise_compute", "potential_function_field", "boundary_surface_charge", "image_plane_comprehensive"]
    by_id = {p.pattern_id: p for p in patterns}
    return [by_id[item] for item in wanted if item in by_id]
