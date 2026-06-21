"""UniversalFigureGenerator — course-agnostic figure generation for PDF 5.0.

Extends FigureGenerator with digital logic figure handlers:
truth tables, K-maps, logic gate diagrams, state diagrams, timing diagrams.
All figures are programmatic SVG — no external rendering dependencies.
"""

from __future__ import annotations

from typing import Any

from core.pdf_content_v2.figures.figure_generator import FigureGenerator
from core.pdf_content_v2.figures.figure_registry import FigureCard


class UniversalFigureGenerator(FigureGenerator):
    """Course-agnostic figure generator with full digital logic support.

    PDF 5.0: All figure types declared in FigureRegistry.SUPPORTED_FIGURES
    must have actual SVG generation code.
    """

    def can_generate(self, concept_id: str, figure_type: str) -> bool:
        """Check if this figure type can be generated."""
        if super().can_generate(concept_id, figure_type):
            return True
        # Additional digital logic types
        dl_types = ["truth_table", "kmap_diagram", "logic_gate_diagram",
                    "state_diagram", "timing_diagram"]
        if self.subject_type == "digital_logic" and figure_type in dl_types:
            return True
        return False

    def generate(self, concept_id: str, figure_type: str,
                 course_id: str = "probability_ch2", chapter_id: str = "ch2",
                 params: dict | None = None) -> FigureCard | None:
        """Generate a figure, routing to the appropriate handler."""
        params = params or {}

        # Try parent handlers first
        result = super().generate(concept_id, figure_type, course_id, chapter_id, params)
        if result:
            return result

        # Digital logic handlers
        if figure_type == "truth_table":
            return self._truth_table(concept_id, course_id, chapter_id, params)
        if figure_type == "kmap_diagram":
            return self._kmap_diagram(concept_id, course_id, chapter_id, params)
        if figure_type == "logic_gate_diagram":
            return self._logic_gate_diagram(concept_id, course_id, chapter_id, params)
        if figure_type == "state_diagram":
            return self._state_diagram(concept_id, course_id, chapter_id, params)
        if figure_type == "timing_diagram":
            return self._timing_diagram(concept_id, course_id, chapter_id, params)

        return None

    # ═══════════════════════════════════════════════════════════════════════
    # Digital Logic: Truth Table
    # ═══════════════════════════════════════════════════════════════════════

    def _truth_table(self, concept_id: str, course_id: str, chapter_id: str,
                     params: dict) -> FigureCard:
        """Generate an SVG truth table for a 3-variable logic function."""
        variables = params.get("variables", ["A", "B", "C"])
        outputs = params.get("outputs", ["0", "0", "0", "1", "0", "1", "1", "1"])
        function_name = params.get("function", "F")

        rows_svg = ""
        y = 50
        for i in range(8):
            a, b, c = (i >> 2) & 1, (i >> 1) & 1, i & 1
            out = outputs[i] if i < len(outputs) else "0"
            rows_svg += f'''<text x="30" y="{y}" class="cell">{a}</text>
  <text x="90" y="{y}" class="cell">{b}</text>
  <text x="150" y="{y}" class="cell">{c}</text>
  <text x="220" y="{y}" class="cell">{out}</text>
  <line x1="15" y1="{y+5}" x2="285" y2="{y+5}" stroke="#ddd" stroke-width="0.5"/>'''
            y += 30

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 350">
  <style>.header{{font:bold 12px sans-serif;fill:#333}}.cell{{font:11px sans-serif;fill:#555}}</style>
  <rect x="5" y="5" width="290" height="340" fill="#fafafa" rx="4"/>
  <text x="110" y="25" class="header">真值表 — {function_name}</text>
  <line x1="15" y1="35" x2="285" y2="35" stroke="#333" stroke-width="1"/>
  <text x="30" y="48" class="header">A</text>
  <text x="90" y="48" class="header">B</text>
  <text x="150" y="48" class="header">C</text>
  <text x="220" y="48" class="header">{function_name}</text>
  <line x1="15" y1="52" x2="285" y2="52" stroke="#333" stroke-width="1.5"/>
{rows_svg}
</svg>'''
        return FigureCard(figure_id=f"{concept_id}_truth_table", concept_id=concept_id,
                         caption=f"三变量真值表：{function_name}({','.join(variables)})",
                         source_level="AI_GENERATED", file_path="", svg=svg)

    # ═══════════════════════════════════════════════════════════════════════
    # Digital Logic: K-Map (Karnaugh Map)
    # ═══════════════════════════════════════════════════════════════════════

    def _kmap_diagram(self, concept_id: str, course_id: str, chapter_id: str,
                      params: dict) -> FigureCard:
        """Generate an SVG 4-variable Karnaugh map."""
        cells = params.get("cells", {})  # dict: "00,00" -> "1", etc.
        groupings = params.get("groupings", [])  # list of cell groups
        variables = params.get("variables", ["A", "B", "C", "D"])
        function_name = params.get("function", "F")

        # 4x4 grid: rows=AB (00,01,11,10), cols=CD (00,01,11,10)
        row_labels = ["00", "01", "11", "10"]
        col_labels = ["00", "01", "11", "10"]
        cell_w, cell_h = 60, 45
        start_x, start_y = 60, 50

        cells_svg = ""
        for ri, rl in enumerate(row_labels):
            for ci, cl in enumerate(col_labels):
                x = start_x + ci * cell_w
                y = start_y + ri * cell_h
                key = f"{rl},{cl}"
                val = cells.get(key, "0")
                cells_svg += (f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" '
                            f'fill="#fff" stroke="#999" stroke-width="1"/>')
                cells_svg += (f'<text x="{x+cell_w/2}" y="{y+cell_h/2+4}" '
                            f'text-anchor="middle" font-size="13" fill="#333">{val}</text>')

        # Row/col headers
        headers_svg = ""
        for ci, cl in enumerate(col_labels):
            x = start_x + ci * cell_w
            headers_svg += f'<text x="{x+cell_w/2}" y="{start_y-8}" text-anchor="middle" font-size="10" fill="#666">CD={cl}</text>'
        for ri, rl in enumerate(row_labels):
            y = start_y + ri * cell_h
            headers_svg += f'<text x="{start_x-12}" y="{y+cell_h/2+3}" text-anchor="end" font-size="10" fill="#666">AB={rl}</text>'

        # Grouping highlights (simplified — just colored rectangles)
        colors = ["#ffeb3b44", "#4caf5044", "#2196f344", "#ff980044"]
        grouping_svg = ""
        for gi, group in enumerate(groupings[:4]):
            color = colors[gi % len(colors)]
            for cell_key in group:
                rl, cl = cell_key.split(",") if "," in cell_key else ("00", "00")
                try:
                    ri = row_labels.index(rl)
                    ci = col_labels.index(cl)
                    x = start_x + ci * cell_w
                    y = start_y + ri * cell_h
                    grouping_svg += (f'<rect x="{x+2}" y="{y+2}" width="{cell_w-4}" '
                                   f'height="{cell_h-4}" fill="{color}" rx="3"/>')
                except ValueError:
                    pass

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 320">
  <text x="160" y="22" font-size="13" font-weight="bold" fill="#333" text-anchor="middle">卡诺图化简 — {function_name}</text>
{headers_svg}
{grouping_svg}
{cells_svg}
  <text x="160" y="{start_y+4*cell_h+20}" font-size="10" fill="#888" text-anchor="middle">AI_GENERATED — 卡诺图</text>
</svg>'''
        return FigureCard(figure_id=f"{concept_id}_kmap", concept_id=concept_id,
                         caption=f"四变量卡诺图：{function_name}({','.join(variables)})",
                         source_level="AI_GENERATED", file_path="", svg=svg)

    # ═══════════════════════════════════════════════════════════════════════
    # Digital Logic: Logic Gate Diagram
    # ═══════════════════════════════════════════════════════════════════════

    def _logic_gate_diagram(self, concept_id: str, course_id: str, chapter_id: str,
                            params: dict) -> FigureCard:
        """Generate an SVG logic gate diagram."""
        gates = params.get("gates", [
            {"type": "AND", "x": 50, "y": 80, "label": "G1"},
            {"type": "OR", "x": 50, "y": 180, "label": "G2"},
            {"type": "NOT", "x": 250, "y": 130, "label": "G3"},
        ])

        gate_svg_parts = []
        for g in gates:
            gtype = g.get("type", "AND")
            gx, gy = g.get("x", 50), g.get("y", 80)
            glabel = g.get("label", "")
            # Draw a simplified gate rectangle
            gate_svg_parts.append(
                f'<rect x="{gx}" y="{gy}" width="80" height="40" fill="#e3f2fd" '
                f'stroke="#1565c0" stroke-width="1.5" rx="4"/>'
            )
            gate_svg_parts.append(
                f'<text x="{gx+40}" y="{gy+25}" text-anchor="middle" '
                f'font-size="11" fill="#333">{gtype}</text>'
            )

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 280">
  <text x="180" y="22" font-size="13" font-weight="bold" fill="#333" text-anchor="middle">逻辑门电路</text>
  {" ".join(gate_svg_parts)}
  <text x="180" y="260" font-size="9" fill="#888" text-anchor="middle">AI_GENERATED — 逻辑门图</text>
</svg>'''
        return FigureCard(figure_id=f"{concept_id}_logic_gate", concept_id=concept_id,
                         caption="逻辑门电路图",
                         source_level="AI_GENERATED", file_path="", svg=svg)

    # ═══════════════════════════════════════════════════════════════════════
    # Digital Logic: State Diagram
    # ═══════════════════════════════════════════════════════════════════════

    def _state_diagram(self, concept_id: str, course_id: str, chapter_id: str,
                       params: dict) -> FigureCard:
        """Generate an SVG state diagram for a finite state machine."""
        states = params.get("states", ["S0", "S1", "S2", "S3"])
        transitions = params.get("transitions", [])  # [(from, to, label), ...]

        # Place states in a circle
        import math
        cx, cy = 200, 140
        radius = 90
        state_svg = ""
        for i, state in enumerate(states):
            angle = 2 * math.pi * i / len(states) - math.pi / 2
            sx = cx + radius * math.cos(angle)
            sy = cy + radius * math.sin(angle)
            state_svg += (f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="22" '
                         f'fill="#e8f5e9" stroke="#2e7d32" stroke-width="1.5"/>')
            state_svg += (f'<text x="{sx:.0f}" y="{sy:.0f+4}" text-anchor="middle" '
                         f'font-size="11" fill="#333">{state}</text>')

        # Transition arrows (simplified lines)
        trans_svg = ""
        for from_s, to_s, label in transitions:
            # Find positions
            fi = states.index(from_s) if from_s in states else 0
            ti = states.index(to_s) if to_s in states else 1
            f_angle = 2 * math.pi * fi / len(states) - math.pi / 2
            t_angle = 2 * math.pi * ti / len(states) - math.pi / 2
            fx = cx + radius * math.cos(f_angle)
            fy = cy + radius * math.sin(f_angle)
            tx = cx + radius * math.cos(t_angle)
            ty = cy + radius * math.sin(t_angle)
            trans_svg += (f'<line x1="{fx:.0f}" y1="{fy:.0f}" x2="{tx:.0f}" '
                         f'y2="{ty:.0f}" stroke="#666" stroke-width="1" marker-end="url(#arrow)"/>')
            # Label at midpoint
            mx, my = (fx+tx)/2, (fy+ty)/2
            trans_svg += (f'<text x="{mx:.0f}" y="{my:.0f-5}" text-anchor="middle" '
                         f'font-size="9" fill="#888">{label}</text>')

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
    <path d="M0,0 L10,5 L0,10 Z" fill="#666"/></marker></defs>
  <text x="180" y="22" font-size="13" font-weight="bold" fill="#333" text-anchor="middle">状态转换图</text>
{state_svg}
{trans_svg}
  <text x="180" y="280" font-size="9" fill="#888" text-anchor="middle">AI_GENERATED — 状态图</text>
</svg>'''
        return FigureCard(figure_id=f"{concept_id}_state_diagram", concept_id=concept_id,
                         caption=f"有限状态机状态转换图 ({len(states)}个状态)",
                         source_level="AI_GENERATED", file_path="", svg=svg)

    # ═══════════════════════════════════════════════════════════════════════
    # Digital Logic: Timing Diagram
    # ═══════════════════════════════════════════════════════════════════════

    def _timing_diagram(self, concept_id: str, course_id: str, chapter_id: str,
                        params: dict) -> FigureCard:
        """Generate an SVG timing/waveform diagram."""
        signals = params.get("signals", [
            {"name": "CP", "wave": "0101010101"},
            {"name": "D", "wave": "0011001100"},
            {"name": "Q", "wave": "0001100110"},
        ])

        width, height = 500, 50 + 40 * len(signals)
        sig_svg = ""
        for si, sig in enumerate(signals):
            y = 50 + si * 40
            sig_svg += f'<text x="10" y="{y+12}" font-size="11" fill="#333">{sig["name"]}</text>'
            wave = sig.get("wave", "0" * 10)
            # Draw waveform as horizontal segments
            for ci in range(len(wave) - 1):
                x1 = 50 + ci * 40
                x2 = x1 + 40
                level = int(wave[ci])
                ly = y + (20 if level == 0 else 0)
                sig_svg += f'<line x1="{x1}" y1="{ly}" x2="{x2}" y2="{ly}" stroke="#1565c0" stroke-width="2"/>'
                # Vertical transition
                next_level = int(wave[ci+1]) if ci+1 < len(wave) else level
                if next_level != level:
                    ny = y + (20 if next_level == 0 else 0)
                    sig_svg += f'<line x1="{x2}" y1="{ly}" x2="{x2}" y2="{ny}" stroke="#1565c0" stroke-width="2"/>'

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <text x="200" y="22" font-size="13" font-weight="bold" fill="#333" text-anchor="middle">时序波形图</text>
  <line x1="50" y1="30" x2="{width-20}" y2="30" stroke="#ddd" stroke-width="0.5"/>
{sig_svg}
  <text x="200" y="{height-10}" font-size="9" fill="#888" text-anchor="middle">AI_GENERATED — 时序图</text>
</svg>'''
        return FigureCard(figure_id=f"{concept_id}_timing", concept_id=concept_id,
                         caption="触发器时序波形图",
                         source_level="AI_GENERATED", file_path="", svg=svg)


# ── Factory ─────────────────────────────────────────────────────────────

def generate_figure(concept_id: str, course_id: str, figure_type: str,
                    subject_type: str = "math",
                    params: dict | None = None) -> FigureCard | None:
    """Convenience function for universal figure generation."""
    gen = UniversalFigureGenerator(subject_type=subject_type)
    return gen.generate(concept_id, figure_type, course_id=course_id, params=params)
