"""Programmatic teaching diagrams for StudyPilot v3 PDFs.

The v3 diagram layer intentionally avoids AI image generation.  Every figure is
an explicit teaching SVG with stable labels and metadata so it can be matched to
the concept or example it explains.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


DIAGRAM_DIR = Path("assets/generated/v3")


def generate_v3_diagrams(diagrams: list[dict[str, Any]], output_dir: str | Path = DIAGRAM_DIR) -> list[dict[str, Any]]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rendered: list[dict[str, Any]] = []
    for item in diagrams:
        diagram_type = item.get("diagram_type", "")
        svg = _svg_for_type(diagram_type, item)
        if not svg:
            continue
        path = out / f"{item['id']}.svg"
        path.write_text(svg, encoding="utf-8")
        rendered.append(
            {
                "id": item["id"],
                "diagram_type": diagram_type,
                "title": item.get("title", item.get("display_name", "")),
                "labels": item.get("labels", []),
                "caption": item.get("caption", ""),
                "concept_id": (item.get("linked_concept_ids") or [""])[0],
                "linked_concept_ids": item.get("linked_concept_ids", []),
                "path": str(path.resolve()),
                "why_needed": item.get("why_needed", ""),
                "source": "programmatic_svg_v3",
            }
        )
    return rendered


def write_diagram_manifest(diagrams: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diagrams, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _svg_for_type(diagram_type: str, item: dict[str, Any]) -> str:
    return {
        "gauss_sphere": _gauss_sphere,
        "image_plane": _image_plane,
        "image_sphere": _image_sphere,
        "boundary_interface": _boundary_interface,
        "potential_gradient": _potential_gradient,
        "point_charge_field_lines": _point_charge_field_lines,
    }.get(diagram_type, lambda _: "")(item)


def _base(title: str, body: str, defs: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="920" height="560" viewBox="0 0 920 560">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6 Z" fill="#334155"/>
    </marker>
    <marker id="redArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6 Z" fill="#b45309"/>
    </marker>
    <style>
      .title{{font:700 28px 'Noto Sans CJK SC','PingFang SC',Arial,sans-serif;fill:#1f2937}}
      .label{{font:600 22px 'Noto Sans CJK SC','PingFang SC',Arial,sans-serif;fill:#1f2937}}
      .small{{font:500 18px 'Noto Sans CJK SC','PingFang SC',Arial,sans-serif;fill:#475569}}
      .math{{font:600 20px Georgia,'Times New Roman',serif;fill:#1e293b}}
      .soft{{fill:#f8fafc;stroke:#cbd5e1;stroke-width:2}}
      .blue{{stroke:#2563eb;fill:none;stroke-width:4}}
      .orange{{stroke:#f59e0b;fill:none;stroke-width:4}}
      .green{{stroke:#16a34a;fill:none;stroke-width:4}}
      .dash{{stroke-dasharray:10 8}}
    </style>
    {defs}
  </defs>
  <rect x="0" y="0" width="920" height="560" fill="#fffaf0"/>
  <text x="44" y="50" class="title">{html.escape(title)}</text>
  {body}
</svg>"""


def _gauss_sphere(item: dict[str, Any]) -> str:
    body = """
  <ellipse cx="456" cy="282" rx="190" ry="118" fill="#dbeafe" stroke="#2563eb" stroke-width="4"/>
  <ellipse cx="456" cy="282" rx="190" ry="118" fill="none" stroke="#1d4ed8" stroke-width="3" stroke-dasharray="9 8"/>
  <circle cx="456" cy="282" r="26" fill="#ef4444"/>
  <text x="433" y="291" class="label" fill="#fff">Q</text>
  <line x1="456" y1="282" x2="640" y2="282" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <text x="540" y="266" class="math">r</text>
  <line x1="640" y1="282" x2="710" y2="230" stroke="#b45309" stroke-width="4" marker-end="url(#redArrow)"/>
  <text x="720" y="224" class="math">dS</text>
  <path d="M456 92 C530 130 590 174 646 232" class="blue" marker-end="url(#arrow)"/>
  <path d="M456 472 C530 432 590 384 646 326" class="blue" marker-end="url(#arrow)"/>
  <path d="M266 282 C204 240 165 194 142 140" class="blue" marker-end="url(#arrow)"/>
  <path d="M266 282 C204 324 165 370 142 424" class="blue" marker-end="url(#arrow)"/>
  <rect x="66" y="438" width="328" height="64" rx="16" fill="#eff6ff" stroke="#93c5fd"/>
  <text x="88" y="477" class="math">∫S D·dS = Q</text>
  <text x="532" y="430" class="small">球形高斯面：面上 E 大小相同</text>
"""
    return _base(item.get("title", "球形高斯面"), body)


def _image_plane(item: dict[str, Any]) -> str:
    body = """
  <rect x="442" y="95" width="18" height="360" fill="#64748b"/>
  <text x="388" y="86" class="small">接地导体平面 V=0</text>
  <circle cx="270" cy="270" r="28" fill="#ef4444"/><text x="246" y="279" class="label" fill="#fff">+q</text>
  <circle cx="632" cy="270" r="28" fill="#2563eb"/><text x="610" y="279" class="label" fill="#fff">-q</text>
  <line x1="270" y1="315" x2="451" y2="315" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <line x1="632" y1="315" x2="451" y2="315" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <text x="344" y="346" class="math">d</text><text x="530" y="346" class="math">d</text>
  <path d="M294 230 C360 150 520 150 608 230" class="orange dash"/>
  <path d="M294 310 C360 392 520 392 608 310" class="orange dash"/>
  <text x="92" y="460" class="small">求解区域只在导体平面含真实电荷一侧</text>
  <rect x="590" y="92" width="250" height="70" rx="16" fill="#eff6ff" stroke="#93c5fd"/>
  <text x="612" y="135" class="math">镜像电荷：-q</text>
"""
    return _base(item.get("title", "接地导体平面镜像法"), body)


def _image_sphere(item: dict[str, Any]) -> str:
    body = """
  <circle cx="390" cy="292" r="128" fill="#e0f2fe" stroke="#0284c7" stroke-width="4"/>
  <circle cx="650" cy="292" r="26" fill="#ef4444"/><text x="629" y="301" class="label" fill="#fff">Q</text>
  <circle cx="454" cy="292" r="20" fill="#2563eb"/><text x="438" y="300" class="label" fill="#fff">Q'</text>
  <circle cx="390" cy="292" r="5" fill="#0f172a"/>
  <line x1="390" y1="292" x2="518" y2="292" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <text x="446" y="276" class="math">a</text>
  <line x1="390" y1="338" x2="650" y2="338" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <text x="515" y="370" class="math">d</text>
  <line x1="390" y1="248" x2="454" y2="248" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <text x="406" y="232" class="math">b=a²/d</text>
  <path d="M650 292 Q540 120 390 164" class="orange dash"/>
  <text x="300" y="92" class="small">接地导体球半径 a</text>
  <text x="620" y="128" class="small">点 P 与角 θ 用于场点几何关系</text>
"""
    return _base(item.get("title", "接地导体球镜像法"), body)


def _boundary_interface(item: dict[str, Any]) -> str:
    body = """
  <rect x="80" y="106" width="760" height="170" fill="#eff6ff" stroke="#bfdbfe"/>
  <rect x="80" y="276" width="760" height="170" fill="#ecfdf5" stroke="#bbf7d0"/>
  <line x1="80" y1="276" x2="840" y2="276" stroke="#334155" stroke-width="4"/>
  <text x="112" y="164" class="label">介质 1</text><text x="112" y="372" class="label">介质 2</text>
  <line x1="462" y1="382" x2="462" y2="176" stroke="#475569" stroke-width="3" marker-end="url(#arrow)"/>
  <text x="476" y="190" class="math">n</text>
  <line x1="260" y1="240" x2="640" y2="240" stroke="#2563eb" stroke-width="4" marker-end="url(#arrow)"/>
  <line x1="260" y1="316" x2="640" y2="316" stroke="#2563eb" stroke-width="4" marker-end="url(#arrow)"/>
  <text x="676" y="246" class="math">Et 连续</text>
  <text x="676" y="322" class="math">Et 连续</text>
  <line x1="520" y1="362" x2="520" y2="290" stroke="#b45309" stroke-width="4" marker-end="url(#redArrow)"/>
  <line x1="520" y1="262" x2="520" y2="190" stroke="#b45309" stroke-width="4" marker-end="url(#redArrow)"/>
  <text x="552" y="282" class="math">Dn 跳变 = ρs</text>
  <text x="112" y="492" class="small">口诀：切向看 E，法向看 D；有自由面电荷时 D 法向跳变。</text>
"""
    return _base(item.get("title", "介质分界面边界条件"), body)


def _potential_gradient(item: dict[str, Any]) -> str:
    body = """
  <path d="M170 160 C330 80 570 88 750 160" stroke="#94a3b8" stroke-width="3" fill="none"/>
  <path d="M145 260 C330 178 575 184 780 260" stroke="#94a3b8" stroke-width="3" fill="none"/>
  <path d="M170 368 C340 292 565 294 750 368" stroke="#94a3b8" stroke-width="3" fill="none"/>
  <text x="776" y="166" class="math">V₁</text><text x="806" y="266" class="math">V₂</text><text x="776" y="374" class="math">V₃</text>
  <line x1="458" y1="150" x2="458" y2="355" stroke="#2563eb" stroke-width="5" marker-end="url(#arrow)"/>
  <line x1="535" y1="154" x2="535" y2="350" stroke="#2563eb" stroke-width="5" marker-end="url(#arrow)"/>
  <line x1="380" y1="156" x2="380" y2="358" stroke="#2563eb" stroke-width="5" marker-end="url(#arrow)"/>
  <text x="562" y="248" class="math">E = -∇φ</text>
  <text x="110" y="466" class="small">电场线垂直等位线，并指向电位降低最快方向。</text>
"""
    return _base(item.get("title", "电位与电场关系"), body)


def _point_charge_field_lines(item: dict[str, Any]) -> str:
    rays = []
    for x2, y2 in [(460, 90), (460, 470), (260, 280), (660, 280), (320, 140), (600, 140), (320, 420), (600, 420)]:
        rays.append(f'<line x1="460" y1="280" x2="{x2}" y2="{y2}" stroke="#2563eb" stroke-width="4" marker-end="url(#arrow)"/>')
    body = "\n".join(rays) + """
  <circle cx="460" cy="280" r="42" fill="#ef4444"/>
  <text x="427" y="294" class="label" fill="#fff">+Q</text>
  <line x1="460" y1="280" x2="660" y2="280" stroke="#475569" stroke-width="2"/>
  <text x="550" y="262" class="math">r</text>
  <rect x="88" y="438" width="330" height="60" rx="16" fill="#eff6ff" stroke="#93c5fd"/>
  <text x="110" y="476" class="math">E ∝ 1/r²，方向径向向外</text>
"""
    return _base(item.get("title", "点电荷电场线"), body)
