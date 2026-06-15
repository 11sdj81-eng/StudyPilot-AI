"""v2.0 Step 1: 资料自动识别与上传质量检测。

Analyze uploaded PDFs to determine quality, guess resource type, and extract
metadata hints before vector indexing.
"""

import re
from pathlib import Path

import fitz

from core.config import CHUNK_OVERLAP, CHUNK_SIZE


def _estimate_chunk_count(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> int:
    """Estimate how many chunks `split_text_pages` would produce from *text*."""
    if not text.strip():
        return 0
    step = max(1, chunk_size - chunk_overlap)
    count = 0
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) <= chunk_size:
            count += 1
        else:
            count += max(1, (len(para) - chunk_size) // step + 1)
    return count


def _guess_resource_type(filename: str, first_pages_text: str) -> str:
    """Guess resource type from filename and the first few pages of text."""
    combined = (filename + " " + first_pages_text[:2000]).lower()

    exam_keywords = ["期末", "试卷", "真题", "往年题", "考题", "试题", "exam", "考试题"]
    for kw in exam_keywords:
        if kw in combined:
            return "往年题"

    ppt_keywords = ["ppt", "课件", "lecture", "slides", "幻灯片"]
    for kw in ppt_keywords:
        if kw in combined:
            return "PPT"

    lab_keywords = ["实验", "lab", "上机", "实验指导"]
    for kw in lab_keywords:
        if kw in combined:
            return "实验指导书"

    notes_keywords = ["笔记", "note", "整理", "总结", "复习资料"]
    for kw in notes_keywords:
        if kw in combined:
            return "笔记"

    return "教材"


def _guess_title(filename: str, first_pages_text: str) -> str:
    """Guess the book / resource title."""
    name = Path(filename).stem
    # Remove edition markers, years, common suffixes
    name = re.sub(r"[_\-]*第[一二三四五六七八九十\d]+版.*", "", name)
    name = re.sub(r"[_\-]*\d{4}[_\-]*", "", name)
    name = re.sub(r"[_\-]+", " ", name).strip()

    if 2 <= len(name) <= 50:
        return name

    # Fallback: scan first-page lines for a title-like line
    for line in first_pages_text.strip().split("\n")[:10]:
        line = line.strip()
        if 4 <= len(line) <= 60 and any(
            kw in line for kw in ["学", "论", "原理", "技术", "基础", "导论", "教程", "概论"]
        ):
            return line

    return name if name else ""


def _guess_edition(filename: str, first_pages_text: str) -> str:
    """Guess edition string, e.g. '第3版'."""
    combined = filename + " " + first_pages_text[:2000]

    m = re.search(r"第([一二三四五六七八九十\d]+)版", combined)
    if m:
        num = m.group(1)
        cn_map = {
            "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
            "六": "6", "七": "7", "八": "8", "九": "9", "十": "10",
        }
        num = cn_map.get(num, num)
        return f"第{num}版"

    m = re.search(r"(?:Edition|edition|Ed\.|ed\.)\s*(\d+)", combined)
    if m:
        return f"第{m.group(1)}版"

    m = re.search(r"[Vv](\d+)", combined)
    if m:
        return f"第{m.group(1)}版"

    return ""


def _guess_course(filename: str, first_pages_text: str) -> str:
    """Guess course name from first pages."""
    course_keywords = ["学", "论", "原理", "技术", "基础", "导论", "电磁", "电路", "信号"]

    for line in first_pages_text.strip().split("\n")[:15]:
        line = line.strip()
        if any(kw in line for kw in course_keywords) and 4 <= len(line) <= 40:
            if not any(skip in line for skip in ["出版社", "ISBN", "http", "www.", "@"]):
                return line

    # Fallback: use the first reasonable-looking line as course name
    for line in first_pages_text.strip().split("\n")[:5]:
        line = line.strip()
        if 4 <= len(line) <= 40 and not any(
            skip in line for skip in ["出版社", "ISBN", "http", "www.", "@", "第", "页"]
        ):
            return line

    return ""


# ---- public API ----


def analyze_pdf(file_path: str | Path, filename: str = "") -> dict:
    """Analyze a PDF and return quality + guessed metadata.

    Returns
    -------
    dict with keys:
        page_count, extractable_text_chars, chunk_count (estimated),
        is_scanned, resource_type_guess, title_guess, edition_guess,
        course_guess, quality_status, quality_message
    """
    path = Path(file_path)
    if not filename:
        filename = path.name

    result: dict = {
        "page_count": 0,
        "extractable_text_chars": 0,
        "chunk_count": 0,
        "is_scanned": False,
        "resource_type_guess": "未知",
        "title_guess": "",
        "edition_guess": "",
        "course_guess": "",
        "quality_status": "failed",
        "quality_message": "",
    }

    # 1. Open
    try:
        doc = fitz.open(path)
    except Exception:
        result["quality_status"] = "failed"
        result["quality_message"] = "未能打开 PDF 文件，文件可能损坏或格式不受支持。"
        return result

    result["page_count"] = len(doc)

    if result["page_count"] == 0:
        doc.close()
        result["quality_status"] = "failed"
        result["quality_message"] = "未能解析 PDF 页数，文件可能损坏或格式不受支持。"
        return result

    # 2. Extract text from all pages; keep first 5 for guessing
    all_parts: list[str] = []
    first_parts: list[str] = []

    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            all_parts.append(text)
            if i < 5:
                first_parts.append(text)
    doc.close()

    full_text = "\n".join(all_parts)
    first_pages_text = "\n".join(first_parts)

    result["extractable_text_chars"] = len(full_text)
    result["chunk_count"] = _estimate_chunk_count(full_text)

    # 3. Guesses
    result["resource_type_guess"] = _guess_resource_type(filename, first_pages_text)
    result["title_guess"] = _guess_title(filename, first_pages_text)
    result["edition_guess"] = _guess_edition(filename, first_pages_text)
    result["course_guess"] = _guess_course(filename, first_pages_text)

    # 4. Quality
    if result["extractable_text_chars"] == 0 or result["chunk_count"] == 0:
        result["quality_status"] = "warning"
        result["is_scanned"] = True
        result["quality_message"] = "该 PDF 可能是扫描版，当前无法提取文字，建议后续使用 OCR。"
    elif result["extractable_text_chars"] < 500:
        result["quality_status"] = "warning"
        result["quality_message"] = "该 PDF 可提取文本较少，生成效果可能受影响。"
    else:
        result["quality_status"] = "usable"
        result["quality_message"] = "资料可用，已成功解析并建立知识库。"

    return result
