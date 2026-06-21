"""FigureGenerator — programmatic SVG generation for course concepts.

Course-agnostic: dispatches by subject_type, not course name.
"""

from __future__ import annotations

import math as _math
from typing import Any

from core.pdf_content_v2.figures.figure_registry import FigureCard


class FigureGenerator:
    """Generate programmatic SVG figures for course concepts.

    All figures are pure Python SVG — no external rendering dependencies.
    """

    def __init__(self, subject_type: str = "math"):
        self.subject_type = subject_type

    def can_generate(self, concept_id: str, figure_type: str) -> bool:
        generators = {
            "math": ["cdf_curve", "pmf_bar", "pdf_curve", "normal_curve",
                     "exponential_curve", "uniform_rect"],
            "engineering": ["field_line", "gaussian_surface", "coordinate_system"],
            "digital_logic": ["truth_table", "kmap_diagram"],
        }
        return figure_type in generators.get(self.subject_type, [])

    def generate(self, concept_id: str, figure_type: str,
                 course_id: str = "probability_ch2", chapter_id: str = "ch2",
                 params: dict | None = None) -> FigureCard | None:
        """Generate a figure, returning a FigureCard with inline SVG."""
        params = params or {}

        if figure_type == "normal_curve":
            return self._normal_curve(concept_id, course_id, chapter_id, params)
        if figure_type == "exponential_curve":
            return self._exponential_curve(concept_id, course_id, chapter_id, params)
        if figure_type == "uniform_rect":
            return self._uniform_rect(concept_id, course_id, chapter_id, params)
        if figure_type == "pdf_curve":
            return self._generic_pdf(concept_id, course_id, chapter_id, params)
        if figure_type == "cdf_curve":
            return self._generic_cdf(concept_id, course_id, chapter_id, params)

        return None

    # ═══════════════════════════════════════════════════════════════════════
    # Normal distribution curve
    # ═══════════════════════════════════════════════════════════════════════

    def _normal_curve(self, concept_id: str, course_id: str, chapter_id: str,
                       params: dict) -> FigureCard:
        mu = params.get("mu", 0)
        sigma = params.get("sigma", 1)
        width, height = 400, 220
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="shade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#3366cc" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#3366cc" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="white"/>
  <!-- axes -->
  <line x1="40" y1="{height-30}" x2="{width-20}" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <line x1="200" y1="20" x2="200" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <!-- x-axis labels -->
  <text x="200" y="{height-10}" text-anchor="middle" font-size="12" fill="#333">μ={mu}</text>
  <text x="280" y="{height-10}" text-anchor="middle" font-size="10" fill="#666">μ+σ</text>
  <text x="120" y="{height-10}" text-anchor="middle" font-size="10" fill="#666">μ-σ</text>
  <!-- normal curve (Bezier approximation) -->
  <path d="M40,{height-30} C40,{height-30} 60,{height-30} 80,{height-35}
           C100,{height-80} 120,{height-140} 140,{height-160}
           C160,{height-175} 180,{height-178} 200,{height-178}
           C220,{height-178} 240,{height-175} 260,{height-160}
           C280,{height-140} 300,{height-80} 320,{height-35}
           C340,{height-30} 360,{height-30} 380,{height-30}"
        fill="none" stroke="#3366cc" stroke-width="2.5"/>
  <!-- shaded region μ-σ to μ+σ -->
  <path d="M120,{height-30} L120,{height-160} C140,{height-172} 160,{height-178} 180,{height-178}
           C190,{height-178} 200,{height-178} 200,{height-178}
           C220,{height-178} 240,{height-172} 260,{height-160}
           L280,{height-160} L280,{height-30} Z"
        fill="#3366cc" fill-opacity="0.12"/>
  <!-- μ line -->
  <line x1="200" y1="30" x2="200" y2="{height-178}" stroke="#cc3333" stroke-width="0.8" stroke-dasharray="4,3"/>
  <!-- label -->
  <text x="200" y="40" text-anchor="middle" font-size="13" fill="#333" font-weight="bold">N(μ,σ²)</text>
  <text x="200" y="{height-160}" text-anchor="middle" font-size="10" fill="#666">68.3%</text>
</svg>'''
        return FigureCard(
            figure_id=f"{concept_id}_normal", course_id=course_id, chapter_id=chapter_id,
            concept_id=concept_id, figure_type="normal_curve",
            title="正态分布曲线", caption=f"图 正态分布 N({mu},{sigma}²) 密度曲线及 ±σ 区间",
            svg_content=svg, generated_by="FigureGenerator::_normal_curve",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Exponential distribution curve
    # ═══════════════════════════════════════════════════════════════════════

    def _exponential_curve(self, concept_id: str, course_id: str, chapter_id: str,
                            params: dict) -> FigureCard:
        lam = params.get("lam", 1.0)
        width, height = 380, 220
        # Exponential decay: f(x)=λe^{-λx}, max at x=0 is λ
        max_y = min(lam * 1.2, 2.0)
        scale_x = (width - 70) / 5.0  # show x from 0 to 5
        scale_y = (height - 60) / max_y
        points = []
        for i in range(71):
            x = i * 5.0 / 70
            y = lam * _math.exp(-lam * x)
            px = 50 + x * scale_x
            py = height - 30 - y * scale_y
            points.append(f"{px:.1f},{py:.1f}")
        path = " L".join(points)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="white"/>
  <line x1="50" y1="{height-30}" x2="{width-20}" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <line x1="50" y1="20" x2="50" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <text x="{width/2}" y="{height-10}" text-anchor="middle" font-size="12" fill="#333">x</text>
  <text x="60" y="{height-30-int(lam*scale_y)}" font-size="11" fill="#cc3333">λ={lam}</text>
  <path d="M50,{height-30} {path}" fill="none" stroke="#3366cc" stroke-width="2.5"/>
  <text x="60" y="25" font-size="13" fill="#333" font-weight="bold">Exp(λ)</text>
  <text x="{width-30}" y="{height-40}" font-size="10" fill="#666">f(x) = λ e^(-λ x)</text>
</svg>'''
        return FigureCard(
            figure_id=f"{concept_id}_exponential", course_id=course_id, chapter_id=chapter_id,
            concept_id=concept_id, figure_type="exponential_curve",
            title="指数分布曲线", caption=f"图 指数分布 Exp({lam}) 密度曲线",
            svg_content=svg, generated_by="FigureGenerator::_exponential_curve",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Uniform distribution rectangle
    # ═══════════════════════════════════════════════════════════════════════

    def _uniform_rect(self, concept_id: str, course_id: str, chapter_id: str,
                       params: dict) -> FigureCard:
        a = params.get("a", 0)
        b = params.get("b", 1)
        width, height = 380, 200
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="white"/>
  <line x1="50" y1="{height-30}" x2="{width-20}" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <line x1="50" y1="20" x2="50" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <!-- Rectangle U(a,b) -->
  <rect x="100" y="{height-100}" width="180" height="70" fill="#3366cc" fill-opacity="0.15" stroke="#3366cc" stroke-width="2"/>
  <!-- Labels -->
  <text x="100" y="{height-15}" text-anchor="middle" font-size="12" fill="#333">a={a}</text>
  <text x="280" y="{height-15}" text-anchor="middle" font-size="12" fill="#333">b={b}</text>
  <text x="190" y="{height-110}" text-anchor="middle" font-size="11" fill="#3366cc">1/(b-a)</text>
  <text x="60" y="25" font-size="12" fill="#333" font-weight="bold">U({a},{b})</text>
  <text x="{width-60}" y="{height-40}" font-size="10" fill="#666">f(x)=1/(b-a)</text>
</svg>'''
        return FigureCard(
            figure_id=f"{concept_id}_uniform", course_id=course_id, chapter_id=chapter_id,
            concept_id=concept_id, figure_type="uniform_rect",
            title="均匀分布", caption=f"图 均匀分布 U({a},{b}) 密度函数",
            svg_content=svg, generated_by="FigureGenerator::_uniform_rect",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Generic PDF curve placeholder
    # ═══════════════════════════════════════════════════════════════════════

    def _generic_pdf(self, concept_id: str, course_id: str, chapter_id: str,
                      params: dict) -> FigureCard:
        width, height = 380, 200
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="white"/>
  <line x1="50" y1="{height-30}" x2="{width-20}" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <line x1="50" y1="20" x2="50" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <path d="M50,{height-30} C80,{height-30} 120,{height-140} 190,{height-140} C260,{height-140} 300,{height-60} 350,{height-35}"
        fill="none" stroke="#3366cc" stroke-width="2.5"/>
  <text x="60" y="25" font-size="13" fill="#333" font-weight="bold">概率密度函数 f(x)</text>
  <text x="200" y="{height-150}" text-anchor="middle" font-size="10" fill="#666">曲线下面积 = 概率</text>
  <text x="{width/2}" y="{height-10}" text-anchor="middle" font-size="12" fill="#333">x</text>
</svg>'''
        return FigureCard(
            figure_id=f"{concept_id}_pdf", course_id=course_id, chapter_id=chapter_id,
            concept_id=concept_id, figure_type="pdf_curve",
            title="概率密度函数", caption=f"图 连续型随机变量的概率密度函数示意图",
            svg_content=svg, generated_by="FigureGenerator::_generic_pdf",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Generic CDF curve placeholder
    # ═══════════════════════════════════════════════════════════════════════

    def _generic_cdf(self, concept_id: str, course_id: str, chapter_id: str,
                      params: dict) -> FigureCard:
        width, height = 380, 200
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="white"/>
  <line x1="50" y1="{height-30}" x2="{width-20}" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <line x1="50" y1="20" x2="50" y2="{height-30}" stroke="#333" stroke-width="1.2"/>
  <text x="40" y="15" font-size="10" fill="#666">F(x)</text>
  <text x="40" y="{height-35}" font-size="10" fill="#666">1</text>
  <text x="40" y="{height/2+20}" font-size="10" fill="#666">0.5</text>
  <text x="40" y="{height/2+30}" font-size="10" fill="#666">0</text>
  <path d="M50,{height-30} C120,{height-30} 160,{height-30} 190,{height-130} C220,{height-50} 280,{height-35} 350,{height-32}"
        fill="none" stroke="#3366cc" stroke-width="2.5"/>
  <text x="200" y="{height/2+10}" text-anchor="middle" font-size="10" fill="#666">单调不减 · 右连续</text>
  <text x="{width/2}" y="{height-10}" text-anchor="middle" font-size="12" fill="#333">x</text>
</svg>'''
        return FigureCard(
            figure_id=f"{concept_id}_cdf", course_id=course_id, chapter_id=chapter_id,
            concept_id=concept_id, figure_type="cdf_curve",
            title="分布函数曲线", caption="图 分布函数 F(x) 示意图（单调不减、右连续、F(-∞)=0、F(+∞)=1）",
            svg_content=svg, generated_by="FigureGenerator::_generic_cdf",
        )
