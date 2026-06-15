"""High-quality SVG figure builder for PDF v4."""

from __future__ import annotations

from pathlib import Path

from core.pdf_v4.typst_asset_manager import FIGURE_DIR, V4FigureAsset


FIGURE_SPECS = [
    ("gauss_surface_charge", "高斯面与包围电荷示意图", "闭合高斯面、法向和包围电荷的关系。", "gauss_law", ["sprint", "review"]),
    ("charged_sphere_piecewise", "均匀带电球体分段求场图", "球内与球外高斯面对应不同包围电荷。", "gauss_law", ["pastpaper", "review"]),
    ("image_grounded_plane", "接地平面镜像法示意图", "真实电荷与镜像电荷关于接地平面对称。", "image_method", ["sprint", "mockexam"]),
    ("image_potential_pr1r2", "镜像法电位表达式几何图", "P 点到真实电荷和镜像电荷的距离分别为 R₁、R₂。", "image_method", ["pastpaper", "review"]),
    ("boundary_conditions", "介质分界面边界条件图", "切向电场连续，法向电位移按面电荷跳变。", "boundary_conditions", ["sprint", "pastpaper", "mockexam", "review"]),
    ("potential_gradient", "电位与电场负梯度图", "电场线垂直等位线并指向电位降低方向。", "potential_gradient", ["review"]),
    ("point_charge_lines", "点电荷电场线图", "正点电荷电场线径向向外。", "electric_field", ["review"]),
    ("energy_density", "静电能量密度示意图", "平行板间电场区域储存静电能量。", "electrostatic_energy", ["review"]),
]


def build_v4_figures(output_dir: str | Path = FIGURE_DIR) -> list[V4FigureAsset]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    assets: list[V4FigureAsset] = []
    for figure_id, title, caption, concept_id, pdf_types in FIGURE_SPECS:
        path = out / f"{figure_id}.svg"
        path.write_text(_svg(figure_id, title), encoding="utf-8")
        assets.append(
            V4FigureAsset(
                id=figure_id,
                title=title,
                caption=caption,
                concept_id=concept_id,
                source="redrawn_svg",
                path=str(path.resolve()),
                pdf_types=pdf_types,
            )
        )
    return assets


def _svg(figure_id: str, title: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="980" height="560" viewBox="0 0 980 560">
<defs>
<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#4f6f52"/></marker>
<marker id="orangeArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#bd7d31"/></marker>
<style>
.title{{font:700 27px 'Noto Sans CJK SC','PingFang SC','Arial';fill:#2f332d}}
.label{{font:600 20px 'Noto Sans CJK SC','PingFang SC','Arial';fill:#2f332d}}
.small{{font:500 16px 'Noto Sans CJK SC','PingFang SC','Arial';fill:#666}}
.math{{font:600 19px Georgia,'Times New Roman',serif;fill:#2f332d}}
.surface{{fill:#eef5ea;stroke:#7fa87a;stroke-width:3}}
.region{{fill:#fff9ee;stroke:#d6a85c;stroke-width:3}}
.line{{stroke:#4f6f52;stroke-width:3;fill:none}}
.thin{{stroke:#7fa87a;stroke-width:2;fill:none}}
.dash{{stroke-dasharray:9 7}}
</style>
</defs>
<rect width="980" height="560" fill="#fffdf8"/>
<text x="46" y="48" class="title">{title}</text>
{_body(figure_id)}
</svg>"""


def _body(figure_id: str) -> str:
    return {
        "gauss_surface_charge": """
<ellipse cx="480" cy="286" rx="178" ry="125" class="surface"/>
<ellipse cx="480" cy="286" rx="118" ry="82" class="region dash"/>
<circle cx="480" cy="286" r="22" fill="#c56c6c"/><text x="462" y="293" class="label" fill="#fff">Q</text>
<line x1="480" y1="286" x2="655" y2="286" class="line" marker-end="url(#arrow)"/><text x="555" y="268" class="math">r</text>
<line x1="640" y1="228" x2="710" y2="182" stroke="#bd7d31" stroke-width="3" marker-end="url(#orangeArrow)"/><text x="720" y="178" class="math">dS</text>
<path d="M480 156 C545 175 610 210 660 260" class="thin" marker-end="url(#arrow)"/><path d="M480 416 C545 395 610 360 660 312" class="thin" marker-end="url(#arrow)"/>
<text x="90" y="462" class="small">闭合曲面 S 上统计电位移通量；只计算曲面内部包围的自由电荷。</text>
""",
        "charged_sphere_piecewise": """
<circle cx="360" cy="292" r="135" class="region"/><circle cx="360" cy="292" r="76" class="surface dash"/>
<circle cx="360" cy="292" r="5" fill="#333"/><line x1="360" y1="292" x2="436" y2="292" class="line" marker-end="url(#arrow)"/><text x="392" y="276" class="math">r</text>
<line x1="360" y1="292" x2="495" y2="292" class="thin" marker-end="url(#arrow)"/><text x="438" y="326" class="math">a</text>
<rect x="575" y="150" width="300" height="90" rx="14" class="surface"/><text x="600" y="184" class="label">r &lt; a：包围部分电荷</text><text x="600" y="215" class="math">Qᵣ = Q r³ / a³</text>
<rect x="575" y="275" width="300" height="90" rx="14" class="region"/><text x="600" y="309" class="label">r ≥ a：包围全部电荷</text><text x="600" y="340" class="math">Qᵣ = Q</text>
""",
        "image_grounded_plane": """
<rect x="475" y="105" width="14" height="340" fill="#7fa87a"/><text x="430" y="88" class="label">接地平面 V=0</text>
<circle cx="285" cy="270" r="27" fill="#c56c6c"/><text x="262" y="278" class="label" fill="#fff">+q</text>
<circle cx="675" cy="270" r="27" fill="#4f6f52"/><text x="654" y="278" class="label" fill="#fff">-q</text>
<line x1="285" y1="322" x2="482" y2="322" class="thin"/><line x1="675" y1="322" x2="482" y2="322" class="thin"/>
<text x="370" y="350" class="math">d</text><text x="570" y="350" class="math">d</text>
<text x="150" y="450" class="small">真实求解区域</text><text x="625" y="450" class="small">镜像区域</text>
""",
        "image_potential_pr1r2": """
<rect x="475" y="92" width="14" height="380" fill="#7fa87a"/>
<circle cx="265" cy="170" r="24" fill="#c56c6c"/><text x="238" y="158" class="label">+q</text>
<circle cx="695" cy="170" r="24" fill="#4f6f52"/><text x="722" y="158" class="label">-q</text>
<circle cx="285" cy="365" r="9" fill="#333"/><text x="260" y="397" class="label">P</text>
<line x1="285" y1="365" x2="265" y2="170" class="thin"/><line x1="285" y1="365" x2="695" y2="170" class="thin"/>
<text x="230" y="270" class="math">R₁</text><text x="500" y="285" class="math">R₂</text>
<text x="525" y="112" class="small">平面上两项电位相消</text>
""",
        "boundary_conditions": """
<rect x="95" y="112" width="790" height="160" fill="#eef5ea"/><rect x="95" y="272" width="790" height="160" fill="#fff9ee"/>
<line x1="95" y1="272" x2="885" y2="272" stroke="#7fa87a" stroke-width="4"/>
<text x="125" y="178" class="label">介质 1，ε₁</text><text x="125" y="365" class="label">介质 2，ε₂</text>
<line x1="285" y1="228" x2="665" y2="228" class="line" marker-end="url(#arrow)"/><line x1="285" y1="318" x2="665" y2="318" class="line" marker-end="url(#arrow)"/>
<text x="690" y="234" class="math">E₁t</text><text x="690" y="324" class="math">E₂t</text>
<line x1="492" y1="392" x2="492" y2="152" stroke="#bd7d31" stroke-width="3" marker-end="url(#orangeArrow)"/>
<text x="515" y="162" class="math">n</text><text x="515" y="265" class="math">D₁n - D₂n = ρₛ</text><text x="395" y="455" class="small">切向连续；法向按自由面电荷跳变。</text>
""",
        "potential_gradient": """
<path d="M165 150 C340 88 620 88 805 150" class="thin"/><path d="M135 270 C335 190 625 190 835 270" class="thin"/><path d="M165 390 C340 315 620 315 805 390" class="thin"/>
<line x1="460" y1="148" x2="460" y2="376" class="line" marker-end="url(#arrow)"/><line x1="550" y1="150" x2="550" y2="370" class="line" marker-end="url(#arrow)"/>
<text x="815" y="154" class="math">V₁</text><text x="845" y="275" class="math">V₂</text><text x="815" y="395" class="math">V₃</text>
<text x="590" y="278" class="math">E = -∇φ</text><text x="120" y="465" class="small">V₁ &gt; V₂ &gt; V₃，电场指向电位降低最快方向。</text>
""",
        "point_charge_lines": """
<circle cx="490" cy="285" r="35" fill="#c56c6c"/><text x="463" y="294" class="label" fill="#fff">+Q</text>
<line x1="490" y1="285" x2="490" y2="92" class="line" marker-end="url(#arrow)"/><line x1="490" y1="285" x2="490" y2="475" class="line" marker-end="url(#arrow)"/><line x1="490" y1="285" x2="260" y2="285" class="line" marker-end="url(#arrow)"/><line x1="490" y1="285" x2="720" y2="285" class="line" marker-end="url(#arrow)"/>
<line x1="490" y1="285" x2="320" y2="120" class="thin" marker-end="url(#arrow)"/><line x1="490" y1="285" x2="660" y2="120" class="thin" marker-end="url(#arrow)"/><line x1="490" y1="285" x2="320" y2="450" class="thin" marker-end="url(#arrow)"/><line x1="490" y1="285" x2="660" y2="450" class="thin" marker-end="url(#arrow)"/>
<text x="745" y="274" class="math">E</text>
""",
        "energy_density": """
<rect x="270" y="145" width="30" height="260" fill="#7fa87a"/><rect x="680" y="145" width="30" height="260" fill="#7fa87a"/>
<text x="242" y="135" class="label">+</text><text x="712" y="135" class="label">-</text>
<line x1="330" y1="190" x2="645" y2="190" class="line" marker-end="url(#arrow)"/><line x1="330" y1="250" x2="645" y2="250" class="line" marker-end="url(#arrow)"/><line x1="330" y1="310" x2="645" y2="310" class="line" marker-end="url(#arrow)"/><line x1="330" y1="370" x2="645" y2="370" class="line" marker-end="url(#arrow)"/>
<rect x="382" y="430" width="250" height="58" rx="14" class="region"/><text x="410" y="466" class="math">wₑ = 1/2 D·E</text>
""",
    }[figure_id]
