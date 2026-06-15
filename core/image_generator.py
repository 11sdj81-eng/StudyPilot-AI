"""v2.1 textbook-style physics illustration generator."""

from __future__ import annotations

import math
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1400, 900


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _pick_template(title: str, template: str = "") -> str:
    if template:
        return template
    text = title.lower()
    if any(key in text for key in ["圆柱", "线电荷", "cylinder", "lambda", "λ"]):
        return "gauss_cylinder"
    if any(key in text for key in ["高斯", "通量", "gauss", "球形高斯面", "球面"]):
        return "gauss_sphere"
    if any(key in text for key in ["接地导体球", "导体球", "image sphere"]):
        return "image_sphere"
    if any(key in text for key in ["镜像", "导体平面", "接地平面", "image method"]):
        return "image_plane"
    if any(key in text for key in ["边界", "介质", "d_n", "e_t", "ρₛ", "rho_s"]):
        return "boundary"
    if any(key in text for key in ["电位", "等位", "梯度", "∇φ", "potential"]):
        return "potential_field"
    return "knowledge_map"


def generate_placeholder_image(title: str, caption: str, output_path: str | Path, template: str = "") -> Path:
    """Create a finished local teaching illustration.

    The historical function name is kept for compatibility; the generated
    image is no longer a placeholder.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (WIDTH, HEIGHT), "#fffdf8")
    draw = ImageDraw.Draw(img)
    fonts = {
        "title": _font(42),
        "body": _font(30),
        "small": _font(24),
        "mini": _font(20),
    }
    _draw_frame(draw, title, caption, fonts)
    drawers = {
        "gauss_sphere": _draw_gauss_sphere,
        "gauss_cylinder": _draw_gauss_cylinder,
        "image_plane": _draw_image_plane,
        "image_sphere": _draw_image_sphere,
        "boundary": _draw_boundary,
        "potential_field": _draw_potential_field,
        "knowledge_map": _draw_knowledge_map,
    }
    drawer = drawers.get(_pick_template(title, template), _draw_knowledge_map)
    drawer(draw, fonts)
    img.save(output)
    return output


def generate_image_with_api(prompt: str, output_path: str | Path) -> Path:
    if not os.getenv("IMAGE_API_KEY", "").strip():
        raise RuntimeError("未配置 IMAGE_API_KEY，使用本地专业教学图。")
    raise NotImplementedError("图片 API 接入点已预留，当前默认生成本地专业教学图。")


def safe_generate_figure(figure: dict, output_path: str | Path) -> Path | None:
    try:
        if os.getenv("IMAGE_API_KEY", "").strip():
            return generate_image_with_api(figure.get("prompt", ""), output_path)
        return generate_placeholder_image(
            figure.get("title", "教学示意图"),
            figure.get("caption", ""),
            output_path,
            template=figure.get("template", ""),
        )
    except Exception:
        return None


def _draw_frame(draw: ImageDraw.ImageDraw, title: str, caption: str, fonts: dict) -> None:
    draw.rounded_rectangle((36, 32, WIDTH - 36, HEIGHT - 34), radius=28, outline="#d7c6a9", width=3, fill="#fffdf8")
    draw.rectangle((60, 118, WIDTH - 60, 122), fill="#dfcfb4")
    title = title[:36]
    tw = _text_size(title, fonts["title"])[0]
    draw.text(((WIDTH - tw) // 2, 56), title, fill="#243744", font=fonts["title"])
    if caption:
        y = HEIGHT - 104
        for line in textwrap.wrap(caption, width=62)[:2]:
            lw = _text_size(line, fonts["mini"])[0]
            draw.text(((WIDTH - lw) // 2, y), line, fill="#695f50", font=fonts["mini"])
            y += 28


def _draw_gauss_sphere(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    cx, cy = 700, 430
    draw.ellipse((cx - 190, cy - 190, cx + 190, cy + 190), outline="#336f8f", width=5)
    _draw_dashed_ellipse(draw, (cx - 250, cy - 250, cx + 250, cy + 250), "#7ba7bd", width=3)
    draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill="#c9473a")
    draw.text((cx + 28, cy - 44), "+Q", fill="#c9473a", font=fonts["body"])
    draw.text((cx - 118, cy - 290), "球形高斯面 S", fill="#336f8f", font=fonts["small"])
    draw.text((cx + 116, cy + 96), "包围电荷 Q", fill="#8b4a32", font=fonts["small"])
    _arrow(draw, (cx, cy), (cx + 260, cy - 118), "#315a73", 4)
    draw.text((cx + 270, cy - 160), "E", fill="#315a73", font=fonts["body"])
    _arrow(draw, (cx + 168, cy - 168), (cx + 224, cy - 224), "#6d7e4f", 4)
    draw.text((cx + 228, cy - 244), "dS", fill="#6d7e4f", font=fonts["small"])
    draw.line((cx, cy, cx + 250, cy), fill="#9b7a48", width=3)
    draw.text((cx + 92, cy + 14), "r", fill="#9b7a48", font=fonts["small"])
    _formula_label(draw, "∫ₛ E·dS = Q / ε₀", 500, 720, fonts["body"])
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        start = (cx + int(205 * math.cos(rad)), cy + int(205 * math.sin(rad)))
        end = (cx + int(285 * math.cos(rad)), cy + int(285 * math.sin(rad)))
        _arrow(draw, start, end, "#7998b1", 2)


def _draw_gauss_cylinder(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    x1, x2, cy = 360, 1030, 430
    draw.line((x1, cy, x2, cy), fill="#b13e35", width=6)
    draw.text((x2 + 24, cy - 34), "无限长线电荷 λ", fill="#b13e35", font=fonts["small"])
    draw.ellipse((x1 - 80, cy - 150, x1 + 80, cy + 150), outline="#336f8f", width=4)
    draw.ellipse((x2 - 80, cy - 150, x2 + 80, cy + 150), outline="#336f8f", width=4)
    draw.line((x1, cy - 150, x2, cy - 150), fill="#336f8f", width=4)
    draw.line((x1, cy + 150, x2, cy + 150), fill="#336f8f", width=4)
    draw.text((585, 228), "圆柱高斯面", fill="#336f8f", font=fonts["small"])
    draw.line((x1, cy + 204, x2, cy + 204), fill="#9b7a48", width=3)
    _arrow_head(draw, (x2, cy + 204), "#9b7a48", 0)
    draw.text((660, cy + 220), "长度 L", fill="#9b7a48", font=fonts["small"])
    draw.line((x1 - 120, cy, x1 - 120, cy - 150), fill="#9b7a48", width=3)
    draw.text((x1 - 170, cy - 94), "r", fill="#9b7a48", font=fonts["small"])
    for x in [430, 560, 690, 820, 950]:
        _arrow(draw, (x, cy + 6), (x, cy + 116), "#315a73", 3)
        _arrow(draw, (x, cy - 6), (x, cy - 116), "#315a73", 3)
    _formula_label(draw, "侧面积 2πrL，E·2πrL = λL / ε₀", 390, 720, fonts["body"])


def _draw_image_plane(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    plane_y = 485
    draw.rectangle((155, plane_y, 1245, plane_y + 16), fill="#70634f")
    for x in range(170, 1230, 38):
        draw.line((x, plane_y + 16, x - 22, plane_y + 44), fill="#aa9a7d", width=2)
    draw.text((930, plane_y + 52), "接地导体平面 V=0", fill="#5e523f", font=fonts["small"])
    qx, qy = 700, 250
    iqy = 720
    draw.ellipse((qx - 25, qy - 25, qx + 25, qy + 25), fill="#c9473a")
    draw.text((qx + 40, qy - 42), "+q", fill="#c9473a", font=fonts["body"])
    draw.ellipse((qx - 25, iqy - 25, qx + 25, iqy + 25), outline="#336f8f", width=5)
    draw.text((qx + 40, iqy - 8), "-q 镜像电荷", fill="#336f8f", font=fonts["small"])
    _dashed_line(draw, (qx, qy + 30), (qx, iqy - 30), "#99917f", 3)
    draw.text((qx + 30, 350), "d", fill="#9b7a48", font=fonts["small"])
    draw.text((qx + 30, 600), "d", fill="#9b7a48", font=fonts["small"])
    draw.text((210, 210), "求解区域", fill="#315a73", font=fonts["small"])
    for dx in [-240, -150, -70, 70, 150, 240]:
        _quadratic_curve(draw, (qx, qy + 28), (qx + dx, plane_y - 4), (qx + dx // 2, qy + 125), "#8798b5", 3)
    _formula_label(draw, "用 -q 替代接地平面影响，实际区域只取平面上方", 340, 782, fonts["small"])


def _draw_image_sphere(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    cx, cy, r = 560, 460, 150
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#eef4f6", outline="#336f8f", width=5)
    draw.text((cx - 74, cy - 24), "接地导体球", fill="#336f8f", font=fonts["small"])
    draw.line((cx, cy, cx + r, cy), fill="#9b7a48", width=3)
    draw.text((cx + 58, cy + 16), "a", fill="#9b7a48", font=fonts["small"])
    qx, qy = 1010, cy
    b_x = cx + int(r * r / (qx - cx))
    draw.ellipse((qx - 25, qy - 25, qx + 25, qy + 25), fill="#c9473a")
    draw.text((qx + 38, qy - 40), "源电荷 Q", fill="#c9473a", font=fonts["small"])
    draw.ellipse((b_x - 18, cy - 18, b_x + 18, cy + 18), fill="#336f8f")
    draw.text((b_x - 60, cy + 34), "Q'", fill="#336f8f", font=fonts["small"])
    draw.line((cx, cy, qx, cy), fill="#9b7a48", width=2)
    draw.text((770, cy + 18), "d", fill="#9b7a48", font=fonts["small"])
    draw.text((cx + 92, cy - 34), "b = a²/d", fill="#6d7e4f", font=fonts["small"])
    px, py = cx + 250, cy - 175
    draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill="#222222")
    draw.text((px + 16, py - 26), "P", fill="#222222", font=fonts["small"])
    draw.arc((cx - 64, cy - 64, cx + 64, cy + 64), 315, 360, fill="#9b7a48", width=3)
    draw.text((cx + 62, cy - 50), "θ", fill="#9b7a48", font=fonts["small"])
    _formula_label(draw, "镜像位置 b = a²/d，镜像电荷 Q' = -aQ/d", 360, 732, fonts["small"])


def _draw_boundary(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    y = 450
    draw.rectangle((90, 145, 1310, y), fill="#eef7fb")
    draw.rectangle((90, y, 1310, 750), fill="#fbf1e8")
    draw.line((90, y, 1310, y), fill="#514a43", width=5)
    draw.text((150, 205), "介质 1", fill="#315a73", font=fonts["body"])
    draw.text((150, 635), "介质 2", fill="#9b5a33", font=fonts["body"])
    _arrow(draw, (700, y + 120), (700, y - 120), "#222222", 4)
    draw.text((720, y - 110), "法向 n", fill="#222222", font=fonts["small"])
    _arrow(draw, (455, y - 62), (705, y - 62), "#336f8f", 4)
    _arrow(draw, (455, y + 62), (705, y + 62), "#336f8f", 4)
    draw.text((735, y - 82), "E₁t = E₂t", fill="#336f8f", font=fonts["small"])
    _arrow(draw, (980, y + 108), (980, y + 18), "#c9473a", 4)
    _arrow(draw, (980, y - 108), (980, y - 18), "#c9473a", 4)
    draw.text((1010, y - 20), "D₂n - D₁n = ρₛ", fill="#c9473a", font=fonts["small"])
    _formula_label(draw, "切向 E 连续；法向 D 的跳变量等于自由面电荷密度 ρₛ", 270, 790, fonts["small"])


def _draw_potential_field(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    cx, cy = 700, 460
    for r, color in [(80, "#d7c36c"), (150, "#c9b35b"), (220, "#bca54c"), (290, "#ad9640")]:
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=3)
    draw.text((170, 210), "等位线 φ = 常数", fill="#8c7a32", font=fonts["small"])
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        _arrow(draw, (cx + int(86 * math.cos(rad)), cy + int(86 * math.sin(rad))), (cx + int(320 * math.cos(rad)), cy + int(320 * math.sin(rad))), "#336f8f", 3)
    draw.text((965, 245), "电场线垂直等位线", fill="#336f8f", font=fonts["small"])
    draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill="#c9473a")
    draw.text((cx + 28, cy - 42), "+q", fill="#c9473a", font=fonts["body"])
    _formula_label(draw, "E = -∇φ：电场沿电位下降最快方向", 420, 770, fonts["body"])


def _draw_knowledge_map(draw: ImageDraw.ImageDraw, fonts: dict) -> None:
    nodes = [
        (700, 220, "电荷与库仑定律", "#336f8f"),
        (420, 390, "电场强度 E", "#547ca0"),
        (980, 390, "电通量 Φ", "#547ca0"),
        (420, 585, "电位 φ", "#7c68a8"),
        (980, 585, "高斯定理", "#6a9b58"),
        (700, 710, "边界条件 / 典型题", "#c6813f"),
    ]
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if abs(a[1] - b[1]) < 260:
                draw.line((a[0], a[1], b[0], b[1]), fill="#d0c3ad", width=2)
    for x, y, label, color in nodes:
        draw.rounded_rectangle((x - 135, y - 46, x + 135, y + 46), radius=22, fill="#ffffff", outline=color, width=3)
        for idx, line in enumerate(label.split("/")):
            text = line.strip()
            tw = _text_size(text, fonts["small"])[0]
            draw.text((x - tw // 2, y - 18 + idx * 28), text, fill=color, font=fonts["small"])


def _formula_label(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font) -> None:
    bbox = draw.textbbox((x, y), text, font=font)
    draw.rounded_rectangle((x - 20, y - 14, bbox[2] + 20, bbox[3] + 16), radius=18, fill="#fbf8ff", outline="#cbbbe8", width=2)
    draw.text((x, y), text, fill="#4b3f68", font=font)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, width: int) -> None:
    draw.line((start[0], start[1], end[0], end[1]), fill=color, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    _arrow_head(draw, end, color, angle)


def _arrow_head(draw: ImageDraw.ImageDraw, point: tuple[int, int], color: str, angle: float) -> None:
    x, y = point
    size = 14
    pts = [
        (x, y),
        (x - size * math.cos(angle - 0.42), y - size * math.sin(angle - 0.42)),
        (x - size * math.cos(angle + 0.42), y - size * math.sin(angle + 0.42)),
    ]
    draw.polygon(pts, fill=color)


def _dashed_line(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str, width: int) -> None:
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    steps = int(length // 18)
    for i in range(steps):
        if i % 2 == 0:
            t1, t2 = i / steps, (i + 1) / steps
            draw.line((x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1, x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2), fill=color, width=width)


def _draw_dashed_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str, width: int) -> None:
    for angle in range(0, 360, 12):
        draw.arc(box, angle, angle + 7, fill=color, width=width)


def _quadratic_curve(draw: ImageDraw.ImageDraw, start, end, control, color: str, width: int) -> None:
    prev = start
    for step in range(1, 28):
        t = step / 27
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1]
        draw.line((prev[0], prev[1], x, y), fill=color, width=width)
        prev = (x, y)


def _text_size(text: str, font) -> tuple[int, int]:
    bbox = font.getbbox(text) if hasattr(font, "getbbox") else (0, 0, 0, 0)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]
