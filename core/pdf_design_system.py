"""StudyPilot PDF v3.1 visual design tokens."""

from __future__ import annotations


DESIGN_TOKENS = {
    "colors": {
        "background": "#F8F5EF",
        "paper": "#FFFDF8",
        "primary": "#7FA87A",
        "accent_green": "#A7C4A0",
        "border": "#E6E0D6",
        "text": "#333333",
        "subtext": "#6F6F6F",
        "warning": "#D6A85C",
        "error": "#C56C6C",
        "formula_bg": "#F6F1E8",
        "example_bg": "#FFF9EE",
        "tip_bg": "#EEF5EA",
        "mistake_bg": "#FFF1EF",
    },
    "type": {
        "cover_title": "36px",
        "h1": "26px",
        "h2": "20px",
        "body": "14px",
        "caption": "11.5px",
        "formula": "17px",
        "table": "12.5px",
    },
    "layout": {
        "card_radius": "14px",
        "page_min_content_ratio": 0.40,
        "page_target_min_ratio": 0.55,
        "page_target_max_ratio": 0.85,
        "page_overcrowded_ratio": 0.90,
    },
}


def css_variables() -> str:
    colors = DESIGN_TOKENS["colors"]
    type_tokens = DESIGN_TOKENS["type"]
    lines = [":root {"]
    for key, value in colors.items():
        lines.append(f"  --{key.replace('_', '-')}: {value};")
    for key, value in type_tokens.items():
        lines.append(f"  --font-{key.replace('_', '-')}: {value};")
    lines.append("}")
    return "\n".join(lines)
