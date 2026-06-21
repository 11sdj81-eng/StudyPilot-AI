"""FigureSelector — choose the right figure type for each concept."""

from __future__ import annotations

from core.pdf_content_v2.figures.figure_registry import SUPPORTED_FIGURES


CONCEPT_FIGURE_MAP: dict[str, list[str]] = {
    # Probability Ch2
    "distribution_function": ["cdf_curve"],
    "continuous_random_variable": ["pdf_curve"],
    "common_continuous_distributions": ["normal_curve", "exponential_curve", "uniform_rect"],
    "normal": ["normal_curve"],
    "exponential": ["exponential_curve"],
    "uniform": ["uniform_rect"],
    # Field wave Ch1
    "electric_field": ["field_line", "coordinate_system"],
    "gauss_law": ["gaussian_surface"],
    "boundary_conditions": ["boundary_diagram"],
    "image_method": ["mirror_diagram"],
    # Digital logic Ch3
    "boolean_algebra": ["truth_table"],
    "karnaugh_map": ["kmap_diagram"],
    "combinational_logic": ["logic_gate_diagram"],
}


class FigureSelector:
    """Select appropriate figure types for a concept."""

    def select(self, concept_id: str, subject_type: str = "math") -> list[str]:
        """Return recommended figure types for a concept."""
        # 1. Check explicit mapping
        if concept_id in CONCEPT_FIGURE_MAP:
            return CONCEPT_FIGURE_MAP[concept_id]
        # 2. Check partial match
        for key, types in CONCEPT_FIGURE_MAP.items():
            if key in concept_id or concept_id in key:
                return types
        # 3. Default based on subject_type
        defaults = {
            "math": ["pdf_curve"],
            "engineering": ["coordinate_system"],
            "digital_logic": ["truth_table"],
        }
        return defaults.get(subject_type, ["generic_diagram"])

    def priority_concepts(self, concepts: list[dict]) -> list[str]:
        """Return concept_ids that most need figures (priority 4+)."""
        return [
            c.get("id", c.get("concept_id", ""))
            for c in concepts
            if c.get("exam_frequency", c.get("priority", 3)) >= 4
        ]
