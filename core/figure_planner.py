"""Plan textbook-style figures and bind them to Markdown sections."""

from __future__ import annotations

import json
import re

from core.deepseek_client import call_deepseek


TEMPLATES = {
    "gauss_sphere",
    "gauss_cylinder",
    "image_plane",
    "image_sphere",
    "boundary",
    "potential_field",
    "knowledge_map",
}


def fallback_figure_plan(markdown_content: str) -> list[dict]:
    headings = _headings(markdown_content)
    candidates: list[dict] = []

    def add(template: str, title: str, caption: str, target: str) -> None:
        if template not in [item["template"] for item in candidates]:
            candidates.append(
                {
                    "title": title,
                    "caption": caption,
                    "prompt": f"textbook physics diagram: {title}, clear Chinese labels",
                    "template": template,
                    "target_section": target,
                }
            )

    for heading in headings:
        key = heading.lower()
        if any(word in key for word in ["高斯", "通量", "gauss"]):
            if any(word in key for word in ["圆柱", "线电荷", "柱"]):
                add("gauss_cylinder", "高斯定理：圆柱高斯面", "用圆柱高斯面分析无限长线电荷的电场分布。", heading)
            else:
                add("gauss_sphere", "高斯定理：球形高斯面", "球形高斯面、电场线和包围电荷之间的关系。", heading)
        if any(word in key for word in ["镜像", "导体平面", "接地平面"]):
            add("image_plane", "镜像法：接地导体平面", "用等效镜像电荷替代接地平面对求解区域的影响。", heading)
        if any(word in key for word in ["导体球", "接地球"]):
            add("image_sphere", "镜像法：接地导体球", "接地导体球外点电荷的镜像电荷位置与大小。", heading)
        if any(word in key for word in ["边界", "介质", "分界"]):
            add("boundary", "静电场边界条件", "介质分界面处切向电场与法向电位移的连续/跳变规律。", heading)
        if any(word in key for word in ["电位", "等位", "梯度"]):
            add("potential_field", "电位与电场关系", "等位线与电场线垂直，电场沿电位下降最快方向。", heading)

    if len(candidates) < 3:
        add("knowledge_map", "静电场知识地图", "电荷、电场、电通量、电位、高斯定理与边界条件的关系。", "知识地图")
    if len(candidates) < 3:
        add("gauss_sphere", "高斯定理：球形高斯面", "球形高斯面、电场线和包围电荷之间的关系。", "核心知识精讲")
    if len(candidates) < 3:
        add("potential_field", "电位与电场关系", "等位线与电场线垂直，电场沿电位下降最快方向。", "核心知识精讲")
    if len(candidates) < 3:
        add("boundary", "静电场边界条件", "介质分界面处切向电场与法向电位移的连续/跳变规律。", "核心知识精讲")

    return candidates[:6]


def plan_figures(markdown_content: str, prompt: str) -> list[dict]:
    fallback = fallback_figure_plan(markdown_content)
    try:
        raw = call_deepseek(prompt, temperature=0.2)
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("未返回 JSON 数组")
        parsed = json.loads(raw[start : end + 1])
        normalized = [_normalize_item(item) for item in parsed if isinstance(item, dict)]
        normalized = [item for item in normalized if item]
        return _merge_plans(normalized, fallback)[:6]
    except Exception:
        return fallback


def _normalize_item(item: dict) -> dict | None:
    title = str(item.get("title", "")).strip()
    caption = str(item.get("caption", "")).strip()
    if not title or not caption:
        return None
    template = str(item.get("template", "")).strip()
    if template not in TEMPLATES:
        template = _template_from_title(title)
    return {
        "title": title,
        "caption": caption,
        "prompt": str(item.get("prompt", "")).strip() or f"textbook physics diagram: {title}",
        "template": template,
        "target_section": str(item.get("target_section", "")).strip() or _target_from_title(title),
    }


def _merge_plans(primary: list[dict], fallback: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for item in primary + fallback:
        key = item.get("template", "") or item.get("title", "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _template_from_title(title: str) -> str:
    text = title.lower()
    if any(word in text for word in ["圆柱", "线电荷", "cylinder", "λ"]):
        return "gauss_cylinder"
    if any(word in text for word in ["高斯", "通量", "gauss"]):
        return "gauss_sphere"
    if any(word in text for word in ["导体球"]):
        return "image_sphere"
    if any(word in text for word in ["镜像", "平面"]):
        return "image_plane"
    if any(word in text for word in ["边界", "介质"]):
        return "boundary"
    if any(word in text for word in ["电位", "等位", "梯度"]):
        return "potential_field"
    return "knowledge_map"


def _target_from_title(title: str) -> str:
    template = _template_from_title(title)
    if template.startswith("gauss"):
        return "高斯定理"
    if template.startswith("image"):
        return "镜像法"
    if template == "boundary":
        return "边界条件"
    if template == "potential_field":
        return "电位与电场关系"
    return "知识地图"


def _headings(markdown_content: str) -> list[str]:
    return [match.group(2).strip() for match in re.finditer(r"^(#{1,3})\s+(.+)$", markdown_content, flags=re.M)]
