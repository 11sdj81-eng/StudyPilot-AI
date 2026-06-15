"""Strict diagram requirements for v1.1 PDFs."""

from __future__ import annotations


REQUIRED_BY_KEYWORD = {
    "高斯面": ["球体半径 a", "高斯面半径 r", "r<a / r>a", "dS", "E 方向"],
    "镜像法": ["导体边界", "原电荷 Q", "镜像电荷 Q’", "距离", "求解区域", "P 点"],
    "边界条件": ["介质 1", "介质 2", "法向 n", "切向 t", "Eₜ", "Dₙ"],
    "等位线": ["等位线", "电场线", "E = -∇φ"],
    "电场线": ["电场线", "方向"],
    "坐标系": ["x", "y", "z"],
    "几何关系": ["距离", "角度", "点 P"],
    "二维积分区域": ["积分区域", "边界"],
    "概率分布图": ["分布", "均值", "方差"],
    "文科时间线": ["时间", "事件", "因果"],
}


def diagram_type_for_text(text: str) -> str:
    for key in REQUIRED_BY_KEYWORD:
        if key in str(text or ""):
            return key
    if "高斯" in str(text):
        return "高斯面"
    if "镜像" in str(text):
        return "镜像法"
    if "边界" in str(text):
        return "边界条件"
    if "电位" in str(text) or "等位" in str(text):
        return "等位线"
    return ""


def required_labels_for_diagram(diagram_type: str) -> list[str]:
    return REQUIRED_BY_KEYWORD.get(diagram_type, [])
