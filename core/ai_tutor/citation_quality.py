"""Citation quality gate for StudyPilot RAG results."""

from __future__ import annotations

import re
from typing import Iterable


CITATION_QUALITY_THRESHOLD = 0.48


def _chinese_ratio(text: str) -> float:
    if not text:
        return 0.0
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    visible = len(re.findall(r"\S", text))
    return chinese / max(visible, 1)


def _symbol_ratio(text: str) -> float:
    if not text:
        return 0.0
    symbols = len(re.findall(r"[=+\-*/\\^_{}()[\]<>∇∂πµεηβϕ√×≤≥]", text))
    visible = len(re.findall(r"\S", text))
    return symbols / max(visible, 1)


def _query_terms(query: str) -> list[str]:
    cleaned = query
    for marker in ["是什么", "怎么用", "怎么考", "如何", "为什么", "我不会", "不懂", "解释", "讲一下", "？", "?"]:
        cleaned = cleaned.replace(marker, " ")
    terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{3,}", cleaned)
    stop = {"什么", "怎么", "如何", "不会", "不懂", "解释", "讲讲", "一下", "的是"}
    return [t for t in terms if t not in stop]


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term and term in text for term in terms)


def score_citation(chunk: dict, query: str) -> dict:
    """Return a quality score and rejection reason for one retrieved chunk."""
    text = str(chunk.get("text") or chunk.get("preview") or "")
    preview = str(chunk.get("preview") or text[:160])
    combined = f"{text}\n{preview}"
    raw_score = float(chunk.get("score") or 0.0)
    chinese_ratio = _chinese_ratio(combined)
    symbol_ratio = _symbol_ratio(combined)
    terms = _query_terms(query)

    directory_markers = ["封面", "书名", "版权", "前言", "目录", "contents"]
    directory_hits = sum(1 for marker in directory_markers if marker.lower() in combined.lower())
    looks_directory = directory_hits >= 2 or bool(re.search(r"第\d+章\s+.*\s+\d+\.\d+", combined))
    if looks_directory:
        return {"quality_score": 0.0, "accepted": False, "reason": "directory"}

    private_use_count = len(re.findall(r"[\uf000-\uf8ff]", combined))
    looks_garbled = chinese_ratio < 0.18 or private_use_count >= 3 or len(re.findall(r"[�□]{2,}|||", combined)) > 0
    formula_noise = symbol_ratio > 0.28 and chinese_ratio < 0.42
    if looks_garbled or formula_noise:
        return {"quality_score": 0.0, "accepted": False, "reason": "garbled"}

    off_topic = bool(terms) and not _contains_any(combined, terms)
    if off_topic:
        return {"quality_score": 0.15, "accepted": False, "reason": "off_topic"}

    if raw_score < 0.02:
        return {"quality_score": round(raw_score, 4), "accepted": False, "reason": "low_score"}

    score_component = min(raw_score / 0.12, 1.0) * 0.45
    text_component = min(chinese_ratio / 0.55, 1.0) * 0.35
    topic_component = 0.20 if not terms or _contains_any(combined, terms) else 0.0
    quality_score = round(score_component + text_component + topic_component, 4)

    if quality_score < CITATION_QUALITY_THRESHOLD:
        return {"quality_score": quality_score, "accepted": False, "reason": "low_score"}

    return {"quality_score": quality_score, "accepted": True, "reason": ""}


def filter_citations(results: list[dict], query: str) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    rejected: list[dict] = []
    for chunk in results:
        verdict = score_citation(chunk, query)
        enriched = dict(chunk)
        enriched["citation_quality_score"] = verdict["quality_score"]
        if verdict["accepted"]:
            accepted.append(enriched)
        else:
            rejected.append({
                "chunk_id": str(chunk.get("chunk_id", "")),
                "source_file": str(chunk.get("source_file", chunk.get("source", ""))),
                "page": str(chunk.get("page", "")),
                "score": chunk.get("score", 0.0),
                "citation_quality_score": verdict["quality_score"],
                "reason": verdict["reason"],
                "preview": str(chunk.get("preview", chunk.get("text", "")))[:120],
            })
    return accepted, rejected
