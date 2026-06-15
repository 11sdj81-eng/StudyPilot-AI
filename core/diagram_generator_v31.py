"""Redrawn programmatic diagrams for StudyPilot PDF v3.1."""

from __future__ import annotations

import json
from pathlib import Path

from core.teaching_asset import TeachingAsset
from core.teaching_asset_manager import ASSET_ROOT, ensure_asset_dirs


PROGRAMMATIC_DIR = ASSET_ROOT / "programmatic"


DIAGRAM_SPECS = [
    ("gauss_quick_memory", "gauss_law", ["sprint"], "quick_memory", "高斯定理速记图", "闭合面、包围电荷、对称性三件事一眼看清。"),
    ("gauss_sphere_piecewise", "gauss_law", ["pastpaper"], "exam_case", "均匀带电球体分段求场图", "突出 r<a 与 r>a 的包围电荷差异。"),
    ("gauss_exam_problem", "gauss_law", ["mockexam"], "problem_statement", "高斯面试卷题图", "只给必要几何关系，不泄露完整解法。"),
    ("image_plane_quick", "image_method", ["sprint"], "quick_memory", "镜像法速记图", "记住真电荷、镜像电荷、求解区域。"),
    ("image_plane_potential_case", "image_method", ["pastpaper"], "exam_case", "接地平面电位讲题图", "显示 R1、R2、P 点和边界验证路径。"),
    ("image_plane_problem", "image_method", ["mockexam"], "problem_statement", "镜像法试卷题图", "只保留 q、d、接地平面。"),
    ("boundary_quick", "boundary_conditions", ["sprint"], "quick_memory", "边界条件口诀图", "切向看 E，法向看 D。"),
    ("boundary_interface_case", "boundary_conditions", ["pastpaper", "mockexam"], "exam_case", "介质分界面题图", "用于边界条件讲题和试卷判断。"),
    ("potential_gradient_teaching", "potential_gradient", ["review"], "full_explanation", "电位与电场完整教学图", "用等位线和电场线解释负梯度。"),
    ("point_charge_field_teaching", "electric_field", ["review"], "full_explanation", "点电荷电场线教学图", "为场强方向和叠加建立图像基础。"),
    ("electrostatic_energy_memory", "electrostatic_energy", ["review"], "full_explanation", "静电能量速记图", "用平行板电容器场能说明能量密度。"),
]


def generate_v31_teaching_assets(output_dir: str | Path = PROGRAMMATIC_DIR) -> list[TeachingAsset]:
    ensure_asset_dirs()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    assets: list[TeachingAsset] = []
    for spec in DIAGRAM_SPECS:
        asset_id, concept_id, pdf_types, usage_context, title, caption = spec
        path = out / f"{asset_id}.svg"
        path.write_text(_svg(asset_id, title), encoding="utf-8")
        assets.append(
            TeachingAsset(
                id=asset_id,
                concept_id=concept_id,
                asset_type="diagram",
                source="programmatic",
                pdf_types=pdf_types,
                difficulty=_difficulty(asset_id),
                usage_context=usage_context,
                path=str(path.resolve()),
                caption=caption,
                why_needed=_why(asset_id),
                visual_style="v3.1 sage-green textbook SVG",
                max_usage_per_run=1,
                title=title,
                confidence=0.88,
            )
        )
    return assets


def write_v31_diagram_catalog(assets: list[TeachingAsset], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asset.to_dict() for asset in assets], ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _difficulty(asset_id: str) -> str:
    if "problem" in asset_id:
        return "typical"
    if "case" in asset_id or "piecewise" in asset_id:
        return "advanced"
    return "basic"


def _why(asset_id: str) -> str:
    return {
        "gauss_quick_memory": "考前快速回忆高斯面必须闭合、必须看包围电荷和对称性。",
        "gauss_sphere_piecewise": "帮助讲清球内球外分段的根本原因。",
        "gauss_exam_problem": "作为试卷图，只提供建模所需几何信息。",
        "image_plane_quick": "考前把镜像法三要素压缩成一张图。",
        "image_plane_potential_case": "老师讲题时需要同时看到 R1、R2 和 P 点。",
        "image_plane_problem": "避免题目图泄露完整解法。",
        "boundary_quick": "用口诀图降低边界条件混淆率。",
        "boundary_interface_case": "让题目中的切向、法向分量可视化。",
        "potential_gradient_teaching": "Review 中解释电场方向和等位线关系。",
        "point_charge_field_teaching": "Review 中建立电场线与径向方向的基础图像。",
        "electrostatic_energy_memory": "把能量密度与高场区域风险联系起来。",
    }.get(asset_id, "辅助知识点理解。")


def _svg(asset_id: str, title: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="920" height="500" viewBox="0 0 920 500">
<defs>
<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#5f7f5b"/></marker>
<style>
.t{{font:700 25px 'Noto Sans CJK SC','PingFang SC',Arial,sans-serif;fill:#333}}
.l{{font:600 18px 'Noto Sans CJK SC','PingFang SC',Arial,sans-serif;fill:#333}}
.s{{font:500 15px 'Noto Sans CJK SC','PingFang SC',Arial,sans-serif;fill:#6F6F6F}}
.m{{font:600 18px Georgia,'Times New Roman',serif;fill:#333}}
.line{{stroke:#5f7f5b;stroke-width:3;fill:none}}
.thin{{stroke:#7FA87A;stroke-width:2;fill:none}}
.dash{{stroke-dasharray:8 7}}
.paper{{fill:#FFFDF8;stroke:#E6E0D6;stroke-width:2}}
.soft{{fill:#EEF5EA;stroke:#A7C4A0;stroke-width:2}}
.warn{{fill:#FFF9EE;stroke:#D6A85C;stroke-width:2}}
</style>
</defs>
<rect width="920" height="500" fill="#FFFDF8"/>
<text x="42" y="46" class="t">{title}</text>
{_body(asset_id)}
</svg>"""


def _body(asset_id: str) -> str:
    bodies = {
        "gauss_quick_memory": """
<circle cx="430" cy="245" r="115" class="soft"/><circle cx="430" cy="245" r="14" fill="#C56C6C"/>
<path d="M430 130 L430 75" class="line" marker-end="url(#arrow)"/><path d="M545 245 L610 245" class="line" marker-end="url(#arrow)"/>
<path d="M430 360 L430 420" class="line" marker-end="url(#arrow)"/><path d="M315 245 L250 245" class="line" marker-end="url(#arrow)"/>
<text x="392" y="251" class="m">Q</text><text x="560" y="232" class="m">E</text><text x="460" y="322" class="m">闭合 S</text>
<rect x="80" y="370" width="260" height="72" rx="14" class="warn"/><text x="105" y="400" class="l">三步：看对称性</text><text x="105" y="426" class="s">选闭合面 → 算包围电荷</text>
<rect x="600" y="370" width="240" height="72" rx="14" class="soft"/><text x="625" y="413" class="m">∫S D·dS = Q</text>
""",
        "gauss_sphere_piecewise": """
<circle cx="360" cy="250" r="135" fill="#F6F1E8" stroke="#7FA87A" stroke-width="3"/>
<circle cx="360" cy="250" r="78" class="thin dash"/><circle cx="360" cy="250" r="5" fill="#333"/>
<line x1="360" y1="250" x2="438" y2="250" class="line" marker-end="url(#arrow)"/><text x="392" y="238" class="m">r<a</text>
<line x1="360" y1="250" x2="495" y2="250" class="thin" marker-end="url(#arrow)"/><text x="452" y="278" class="m">a</text>
<rect x="565" y="150" width="275" height="82" rx="14" class="soft"/><text x="590" y="184" class="l">球内：只包围部分电荷</text><text x="590" y="211" class="m">Q(r³/a³)</text>
<rect x="565" y="260" width="275" height="82" rx="14" class="warn"/><text x="590" y="294" class="l">球外：包围全部电荷</text><text x="590" y="321" class="m">Q</text>
""",
        "gauss_exam_problem": """
<circle cx="430" cy="255" r="128" fill="#F6F1E8" stroke="#7FA87A" stroke-width="3"/>
<circle cx="430" cy="255" r="72" class="thin dash"/><line x1="430" y1="255" x2="502" y2="255" class="line" marker-end="url(#arrow)"/>
<text x="457" y="238" class="m">r</text><text x="535" y="260" class="m">a</text>
<text x="305" y="420" class="s">均匀带电球体，总电荷 Q。求 r 处电场。</text>
""",
        "image_plane_quick": """
<rect x="445" y="105" width="14" height="300" fill="#7FA87A"/><text x="405" y="92" class="l">接地面 V=0</text>
<circle cx="280" cy="250" r="26" fill="#C56C6C"/><text x="258" y="258" class="l" fill="#fff">+q</text>
<circle cx="625" cy="250" r="26" fill="#6F8F68"/><text x="604" y="258" class="l" fill="#fff">-q</text>
<line x1="280" y1="300" x2="452" y2="300" class="thin"/><line x1="625" y1="300" x2="452" y2="300" class="thin"/>
<text x="350" y="326" class="m">d</text><text x="530" y="326" class="m">d</text>
<rect x="90" y="390" width="300" height="55" rx="14" class="warn"/><text x="112" y="424" class="l">真电荷一侧才是求解区域</text>
""",
        "image_plane_potential_case": """
<rect x="455" y="80" width="12" height="350" fill="#7FA87A"/><circle cx="250" cy="175" r="23" fill="#C56C6C"/><circle cx="250" cy="335" r="18" fill="#333"/>
<circle cx="665" cy="175" r="23" fill="#6F8F68"/><text x="226" y="164" class="l">+q</text><text x="690" y="164" class="l">-q</text><text x="225" y="365" class="l">P</text>
<line x1="250" y1="335" x2="250" y2="175" class="thin"/><line x1="250" y1="335" x2="665" y2="175" class="thin"/>
<text x="215" y="260" class="m">R1</text><text x="485" y="270" class="m">R2</text><text x="520" y="105" class="s">平面上 V=0 用来验证答案</text>
""",
        "image_plane_problem": """
<rect x="455" y="100" width="12" height="300" fill="#7FA87A"/><circle cx="300" cy="235" r="25" fill="#C56C6C"/><text x="276" y="226" class="l">+q</text>
<line x1="300" y1="285" x2="462" y2="285" class="thin"/><text x="365" y="313" class="m">d</text><text x="500" y="238" class="s">接地导体平面</text>
""",
        "boundary_quick": """
<line x1="90" y1="250" x2="830" y2="250" stroke="#7FA87A" stroke-width="4"/><text x="100" y="180" class="l">介质 1</text><text x="100" y="335" class="l">介质 2</text>
<line x1="250" y1="210" x2="650" y2="210" class="line" marker-end="url(#arrow)"/><text x="680" y="216" class="m">Et 连续</text>
<line x1="430" y1="365" x2="430" y2="135" class="line" marker-end="url(#arrow)"/><text x="455" y="250" class="m">Dn 看 ρs</text>
<rect x="255" y="400" width="390" height="54" rx="14" class="warn"/><text x="280" y="434" class="l">口诀：切向看 E，法向看 D</text>
""",
        "boundary_interface_case": """
<rect x="80" y="110" width="760" height="140" fill="#EEF5EA"/><rect x="80" y="250" width="760" height="140" fill="#FFF9EE"/>
<line x1="80" y1="250" x2="840" y2="250" stroke="#7FA87A" stroke-width="4"/>
<line x1="260" y1="210" x2="620" y2="210" class="line" marker-end="url(#arrow)"/><line x1="275" y1="292" x2="620" y2="292" class="line" marker-end="url(#arrow)"/>
<line x1="460" y1="350" x2="460" y2="150" class="thin" marker-end="url(#arrow)"/><text x="482" y="165" class="m">n</text>
<text x="650" y="215" class="m">E1t</text><text x="650" y="298" class="m">E2t</text><text x="500" y="256" class="m">ρs</text>
""",
        "potential_gradient_teaching": """
<path d="M150 150 C320 90 565 90 760 150" class="thin"/><path d="M130 250 C330 180 585 180 790 250" class="thin"/><path d="M150 355 C330 295 565 295 760 355" class="thin"/>
<line x1="430" y1="145" x2="430" y2="348" class="line" marker-end="url(#arrow)"/><line x1="515" y1="145" x2="515" y2="348" class="line" marker-end="url(#arrow)"/>
<text x="775" y="155" class="m">V高</text><text x="800" y="358" class="m">V低</text><text x="548" y="250" class="m">E = -∇φ</text>
<text x="120" y="430" class="s">电场线垂直等位线，指向电位降低最快方向。</text>
""",
        "point_charge_field_teaching": """
<circle cx="455" cy="250" r="32" fill="#C56C6C"/><text x="430" y="258" class="l" fill="#fff">+Q</text>
<line x1="455" y1="250" x2="455" y2="90" class="line" marker-end="url(#arrow)"/><line x1="455" y1="250" x2="455" y2="415" class="line" marker-end="url(#arrow)"/>
<line x1="455" y1="250" x2="260" y2="250" class="line" marker-end="url(#arrow)"/><line x1="455" y1="250" x2="650" y2="250" class="line" marker-end="url(#arrow)"/>
<line x1="455" y1="250" x2="315" y2="110" class="thin" marker-end="url(#arrow)"/><line x1="455" y1="250" x2="600" y2="110" class="thin" marker-end="url(#arrow)"/><line x1="455" y1="250" x2="315" y2="390" class="thin" marker-end="url(#arrow)"/><line x1="455" y1="250" x2="600" y2="390" class="thin" marker-end="url(#arrow)"/>
<text x="630" y="230" class="m">E</text><text x="120" y="430" class="s">正点电荷电场线径向向外，距离越远越稀疏。</text>
""",
        "electrostatic_energy_memory": """
<rect x="260" y="135" width="28" height="230" fill="#7FA87A"/><rect x="620" y="135" width="28" height="230" fill="#7FA87A"/>
<line x1="320" y1="170" x2="585" y2="170" class="line" marker-end="url(#arrow)"/><line x1="320" y1="230" x2="585" y2="230" class="line" marker-end="url(#arrow)"/><line x1="320" y1="290" x2="585" y2="290" class="line" marker-end="url(#arrow)"/><line x1="320" y1="350" x2="585" y2="350" class="line" marker-end="url(#arrow)"/>
<text x="395" y="115" class="l">均匀电场区域</text><rect x="342" y="390" width="245" height="54" rx="14" class="warn"/><text x="365" y="424" class="m">we = 1/2 D·E</text>
""",
    }
    return bodies.get(asset_id, "")
