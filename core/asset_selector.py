"""v4.2: Confidence-gated textbook asset selection.

Assets are classified as high / medium / low confidence.
Only high-confidence assets are auto-inserted into the lecture body.
Medium-confidence assets go to an appendix section.
Low-confidence assets are discarded entirely.

For scanned PDFs without OCR text, the default ceiling is MEDIUM
unless a RAG chunk hits the exact same page.
"""

from __future__ import annotations

import re
from collections import defaultdict


def select_assets_for_lecture(
    course_assets: list[dict],
    content: str,
    chunks: list[dict] | None = None,
    max_figures: int = 4,
    max_formulas: int = 4,
    max_examples: int = 2,
) -> dict:
    """Select assets with confidence gating.

    Returns a dict with keys:
        high:      list of high-confidence assets (→ auto-insert into body)
        medium:    list of medium-confidence assets (→ appendix only)
        low:       list of low-confidence assets (→ discarded, for logging)
        all_scored: all scored assets (for diagnostics)
    """
    chunks = chunks or []
    if not course_assets:
        return {"high": [], "medium": [], "low": [], "all_scored": []}

    # ---- 1. Build page relevance from RAG chunks ---------------------------
    rag_pages: set[int] = set()
    for chunk in chunks:
        page = int(chunk.get("page", 0)) if str(chunk.get("page", "0")).isdigit() else 0
        if page > 0:
            rag_pages.add(page)

    # ---- 2. Parse knowledge points from content ----------------------------
    knowledge_points = _parse_knowledge_points(content)

    # ---- 3. Score and classify each asset ----------------------------------
    scored: list[dict] = []
    for asset in course_assets:
        asset_page = asset.get("page", 0)
        asset_type = asset.get("asset_type", "")
        is_scanned = asset.get("is_scanned_page", False)
        has_keywords = bool(asset.get("related_keywords"))

        best_score = 0.0
        best_kp = ""
        best_why_parts: list[str] = []
        best_page_dist = 999

        for kp in knowledge_points:
            score = 0.0
            why_parts: list[str] = []
            min_dist = 999

            # ---- Page proximity (strongest signal) ----
            for kp_page in kp["pages"]:
                if asset_page > 0 and kp_page > 0:
                    dist = abs(asset_page - kp_page)
                    min_dist = min(min_dist, dist)
                    if dist == 0:
                        score += 15.0
                        why_parts.append(f"教材第{asset_page}页，与「{kp['title']}」同页")
                    elif dist <= 2:
                        score += 6.0
                        why_parts.append(f"教材第{asset_page}页，紧邻「{kp['title']}」（第{kp_page}页，距{dist}页）")
                    elif dist <= 10:
                        score += 2.0
                        why_parts.append(f"教材第{asset_page}页，靠近「{kp['title']}」（距{dist}页）")

            # ---- Keyword match ----
            title_lower = kp["title"].lower()
            asset_keywords = [k.lower() for k in asset.get("related_keywords", [])]
            kw_matches = [kw for kw in asset_keywords if kw in title_lower]
            if kw_matches:
                score += len(kw_matches) * 10.0
                why_parts.append(f"关键词匹配「{'、'.join(kw_matches[:3])}」")

            # ---- Type relevance ----
            type_bonus = _type_match_bonus(asset_type, kp["title"])
            if type_bonus > 0:
                score += type_bonus
                why_parts.append(f"类型适合「{kp['title']}」")

            if score > best_score:
                best_score = score
                best_kp = kp["title"]
                best_why_parts = why_parts
                best_page_dist = min_dist

        # ---- Determine confidence level ----
        confidence = _classify_confidence(
            best_score, best_page_dist, asset_page, rag_pages,
            is_scanned, has_keywords,
        )

        best_why = "；".join(best_why_parts[:3]) if best_why_parts else (
            f"教材第{asset_page}页（无明确知识点匹配）"
        )

        scored.append({
            **asset,
            "match_score": round(best_score, 1),
            "matched_kp": best_kp,
            "page_dist": best_page_dist,
            "confidence": confidence,
            "why": best_why,
        })

    # ---- 4. Split by confidence -------------------------------------------
    high = [s for s in scored if s["confidence"] == "high"]
    medium = [s for s in scored if s["confidence"] == "medium"]
    low = [s for s in scored if s["confidence"] == "low"]

    # Sort within each group by score descending
    for group in [high, medium, low]:
        group.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # ---- 5. Per-type caps, dedup by page ----------------------------------
    high_selected = _apply_caps(high, max_figures, max_formulas, max_examples)
    medium_selected = _apply_caps(medium, max_figures, max_formulas, max_examples)

    return {
        "high": high_selected,
        "medium": medium_selected,
        "low": low,
        "all_scored": scored,
    }


def embed_selected_assets(content: str, selection: dict) -> tuple[str, dict]:
    """Embed high-confidence assets into lecture body, medium into appendix.

    Returns (updated_content, stats_dict).
    """
    high = selection.get("high", [])
    medium = selection.get("medium", [])
    all_scored = selection.get("all_scored", [])

    stats = {
        "candidates": len(all_scored),
        "high_count": len(high),
        "medium_count": len(medium),
        "low_count": len(selection.get("low", [])),
        "inserted_body": 0,
        "inserted_appendix": 0,
        "skipped_reasons": [],
    }

    if not high and not medium:
        stats["skipped_reasons"].append("无高/中置信度资产匹配，未插入任何教材截图。")
        return content, stats

    # ---- Insert high-confidence assets near matched KPs -------------------
    kp_positions = _find_kp_positions(content)
    insertions: list[tuple[int, str]] = []
    inserted_pages: set[int] = set()

    for asset in high:
        page = asset.get("page", 0)
        if page in inserted_pages:
            continue  # one asset per page max for body
        inserted_pages.add(page)

        kp = asset.get("matched_kp", "")
        pos = kp_positions.get(kp, 0)
        markup = _asset_markup(asset)
        if pos > 0:
            insertions.append((pos, markup))
            stats["inserted_body"] += 1
        else:
            # KP not found in content → fallback to appendix
            medium_extra = dict(asset)
            medium_extra["confidence"] = "medium"
            medium_extra["why"] = asset.get("why", "") + "（知识点未在正文中找到对应位置，移至附录）"
            medium.append(medium_extra)

    # Apply insertions (bottom-to-top to preserve positions)
    insertions.sort(key=lambda x: x[0], reverse=True)
    result = content
    for pos, markup in insertions:
        result = result[:pos] + "\n\n" + markup + "\n" + result[pos:]

    # ---- Medium assets → appendix section ----------------------------------
    if medium:
        appendix_pos = len(result)
        section = "\n\n# 教材参考素材\n\n"
        section += (
            "*以下教材资产匹配置信度为 medium，"
            "未自动插入正文。如需使用，请核对教材原文。*\n\n"
        )
        for asset in medium[:8]:
            section += _asset_markup(asset) + "\n\n"
            stats["inserted_appendix"] += 1
        result = result + section

    # ---- Diagnostic notes --------------------------------------------------
    if stats["inserted_body"] == 0 and high:
        stats["skipped_reasons"].append(
            f"有{len(high)}个高置信资产但未能定位正文插入点，已移至附录。"
        )
    if not high:
        stats["skipped_reasons"].append(
            "没有 high-confidence 资产，正文不插入教材截图。"
            "建议上传可检索文本的教材 PDF 以提高匹配置信度。"
        )

    return result, stats


# ---- confidence classification --------------------------------------------

def _classify_confidence(
    score: float,
    page_dist: int,
    asset_page: int,
    rag_pages: set[int],
    is_scanned: bool,
    has_keywords: bool,
) -> str:
    """Classify an asset as high / medium / low confidence."""

    # HIGH: same-page RAG hit
    if asset_page in rag_pages and page_dist == 0:
        return "high"

    # HIGH: strong keyword match + close proximity (text-based PDFs)
    if has_keywords and score >= 12 and page_dist <= 3:
        return "high"

    # For scanned PDFs without text: max MEDIUM unless same-page
    if is_scanned and not has_keywords:
        if asset_page in rag_pages:
            # Adjacent pages in scanned PDF — still only medium
            # (we can't verify page content without OCR)
            if page_dist <= 2:
                return "medium"
        # Distant scanned pages with no keywords → LOW
        if page_dist > 10 or score < 4:
            return "low"
        return "medium"

    # MEDIUM: reasonable proximity or type match
    if page_dist <= 5 and score >= 4:
        return "medium"
    if has_keywords and score >= 6:
        return "medium"

    # LOW: everything else
    return "low"


def _apply_caps(
    assets: list[dict],
    max_figures: int,
    max_formulas: int,
    max_examples: int,
) -> list[dict]:
    """Apply per-type caps and page dedup."""
    result: list[dict] = []
    seen_pages: set[int] = set()
    counts: dict[str, int] = defaultdict(int)

    type_buckets = {
        "figure": max_figures, "figure_page": max_figures,
        "formula": max_formulas, "formula_page": max_formulas,
        "example": max_examples, "example_page": max_examples,
    }

    for asset in assets:
        atype = asset.get("asset_type", "")
        cap = type_buckets.get(atype, 2)
        page = asset.get("page", 0)

        if counts[atype] >= cap:
            continue
        if page in seen_pages:
            continue

        seen_pages.add(page)
        counts[atype] += 1
        result.append(asset)

    return result


# ---- helpers (unchanged from v4.1) -----------------------------------------

def _parse_knowledge_points(content: str) -> list[dict]:
    kps: list[dict] = []
    current_kp: dict | None = None
    skip_titles = [
        "学习目标", "知识地图", "公式总结", "典型例题", "高频考点",
        "考前速记", "自测题", "教材资产", "参考来源", "教材参考素材",
        "教材原意", "为什么重要", "公式推导链", "老师讲法",
        "考试考法", "易错点", "本章定位", "本章在课程中的位置",
    ]

    for line in content.splitlines():
        # Only ## (level-2) headings can be knowledge points;
        # ### (level-3) sub-headings like "教材原意" are ignored.
        kp_match = re.match(r"^##\s+(?:知识点\s*\d+[：:]\s*)?(.+)$", line)
        if kp_match and len(line.strip()) > 4:
            title = kp_match.group(1).strip()
            if any(skip in title for skip in skip_titles) or len(title) < 3:
                current_kp = None
                continue
            current_kp = {"title": title, "pages": []}
            kps.append(current_kp)
            continue

        # Also capture page refs on the heading line itself (before continue)
        if current_kp is not None:
            for m in re.finditer(
                r"(?:教材|来源).*?[pP]\.?\s*(\d+)|第\s*(\d+)\s*页",
                line,
            ):
                page_str = m.group(1) or m.group(2)
                if page_str and page_str.isdigit():
                    current_kp["pages"].append(int(page_str))

    return kps


def _find_kp_positions(content: str) -> dict[str, int]:
    """Find character positions of knowledge point headings, normalised the
    same way ``_parse_knowledge_points`` strips titles."""
    positions: dict[str, int] = {}
    for m in re.finditer(r"^##\s+(?:知识点\s*\d+[：:]\s*)?(.+)$", content, flags=re.M):
        title = m.group(1).strip()
        if len(title) >= 3:
            positions[title] = m.start()
    return positions


def _type_match_bonus(asset_type: str, kp_title: str) -> float:
    t = kp_title.lower()
    at = asset_type
    if any(kw in t for kw in ["高斯", "gauss", "通量"]):
        if at in ("figure_page", "figure", "formula_page", "formula"):
            return 4.0
    if any(kw in t for kw in ["镜像", "image"]):
        if at in ("figure_page", "figure", "example_page", "example"):
            return 4.0
    if any(kw in t for kw in ["电位", "电容", "边界", "能量"]):
        if at in ("formula_page", "formula", "figure_page", "figure"):
            return 3.0
    if any(kw in t for kw in ["库仑", "电场强度"]):
        if at in ("formula_page", "formula"):
            return 3.0
    return 0.0


def _asset_markup(asset: dict) -> str:
    path = asset.get("image_path", "")
    title = asset.get("title_guess", "教材资产")
    page = asset.get("page", "?")
    source = asset.get("source_pdf", "教材")
    why = asset.get("why", "")
    atype_cn = {
        "figure": "教材原图", "figure_page": "教材插图",
        "formula": "教材公式", "formula_page": "教材公式",
        "example": "教材例题", "example_page": "教材例题",
        "textbook_page": "教材原页",
    }.get(asset.get("asset_type", ""), "教材资产")
    confidence = asset.get("confidence", "")

    parts = [f"![{atype_cn}：{title}]({path})"]
    caption = f"*{atype_cn}，来源：{source} 第{page}页"
    if confidence:
        caption += f" [置信度: {confidence}]"
    if asset.get("asset_type", "").endswith("_page") or asset.get("is_scanned_page"):
        caption += "。教材页级参考，非精确子图裁剪"
    if why:
        caption += f"。{why}"
    caption += "*"
    parts.append(caption)
    return "\n\n".join(parts) + "\n"
