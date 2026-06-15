"""StudyPilot v5.2 — Real Content Builder.

Cleans OCR output from DI Worker and generates structured evidence
for concepts, formulas, questions, and review sections.

Principle: OCR noise stays out of PDFs. Low-confidence content is flagged.
All real content carries source_file and page_number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Data structures ──────────────────────────────────────────────────────


@dataclass
class RealConceptEvidence:
    concept_id: str
    concept_name: str
    source_file: str
    page_number: int
    evidence_text: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class RealExamQuestionCandidate:
    question_id: str
    source_file: str
    page_number: int
    raw_text: str
    inferred_question_type: str = "unknown"
    inferred_concepts: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class RealSourceRef:
    source_file: str
    page_number: int
    snippet: str
    concept_id: str | None = None


# ── OCR text cleaning ────────────────────────────────────────────────────

def clean_ocr_text(text: str) -> str:
    """Clean raw OCR output for PDF use."""
    if not text:
        return ""

    # Remove obvious header/footer patterns
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*第\s*\d+\s*页\s*$', '', text, flags=re.MULTILINE)

    # Remove excessive whitespace
    text = re.sub(r'[ \t]{3,}', '  ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # Remove obvious garbage (lines that are 80%+ non-CJK/non-ASCII/non-math symbols)
    cleaned_lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            cleaned_lines.append('')
            continue
        # Skip lines that are just single characters or pure noise
        if len(line) <= 2 and not any('一' <= c <= '鿿' for c in line):
            continue
        cleaned_lines.append(line)

    # Merge broken lines (lines ending without punctuation are likely continuations)
    merged = []
    for line in cleaned_lines:
        if line == '':
            merged.append('')
        elif merged and merged[-1] and not merged[-1].endswith(('。', '，', '；', '：', '）', ')', '？', '！', '、')):
            if len(merged[-1]) < 60:
                merged[-1] = merged[-1] + line
                continue
        merged.append(line)

    return '\n'.join(line for line in merged if line or (merged and merged[-1] != ''))


def is_low_confidence(confidence: float) -> bool:
    """Confidence below 0.7 is considered low."""
    return confidence < 0.7


def is_ocr_noise(text: str, confidence: float) -> bool:
    """Quick heuristic for OCR noise."""
    if confidence < 0.5:
        return True
    if len(text) < 3 and not any('一' <= c <= '鿿' for c in text):
        return True
    # Pure numbers/symbols with no context
    if re.match(r'^[\d\s\.\,\;\:\-]+$', text) and len(text) < 10:
        return True
    return False


# ── Concept extraction from OCR blocks ────────────────────────────────────

CONCEPT_KEYWORDS = {
    "gauss_law": {
        "name": "高斯定理",
        "keywords": ["高斯", "通量", "闭合面", "包围电荷", "Gauss", "D·dS", "电位移"],
    },
    "electric_field": {
        "name": "电场强度",
        "keywords": ["电场强度", "电场", "场强", "库仑", "∇×E", "点电荷", "场线"],
    },
    "potential_gradient": {
        "name": "电位梯度",
        "keywords": ["电位", "电势", "梯度", "∇φ", "等位", "E=-∇φ", "电压"],
    },
    "boundary_condition": {
        "name": "边界条件",
        "keywords": ["边界条件", "边界", "介质", "法向", "切向", "Dn", "Et", "分界面", "ρs"],
    },
    "mirror_method": {
        "name": "镜像法",
        "keywords": ["镜像", "接地", "导体平面", "像电荷", "image charge", "V=0", "导体"],
    },
    "electrostatic_energy": {
        "name": "静电能量",
        "keywords": ["静电能量", "能量密度", "电容器", "储能", "D·E", "wₑ", "1/2"],
    },
}


def extract_concept_evidence(
    blocks: list[dict[str, Any]],
    source_file: str = "unknown",
) -> list[RealConceptEvidence]:
    """Extract concept evidence from OCR blocks."""
    evidence_list: list[RealConceptEvidence] = []
    seen: dict[str, set[str]] = {}  # concept_id -> set of matched keywords

    for block in blocks:
        # Accept both 'text' (from document.json) and 'content' (from DocumentBlocks)
        text = block.get("text", "") or block.get("content", "")
        page = block.get("source_page", 0) or block.get("page_number", 0)
        conf = block.get("confidence", 0.0)

        if is_ocr_noise(text, conf):
            continue

        cleaned = clean_ocr_text(text)

        for cid, info in CONCEPT_KEYWORDS.items():
            matched = [kw for kw in info["keywords"] if kw.lower() in cleaned.lower()]
            if matched:
                if cid not in seen:
                    seen[cid] = set()
                new_kw = [kw for kw in matched if kw not in seen[cid]]
                if new_kw:
                    seen[cid].update(new_kw)
                    evidence_list.append(RealConceptEvidence(
                        concept_id=cid,
                        concept_name=info["name"],
                        source_file=source_file,
                        page_number=page,
                        evidence_text=cleaned[:200],
                        confidence=conf,
                        matched_keywords=new_kw,
                    ))

    return evidence_list


def extract_exam_questions(
    blocks: list[dict[str, Any]],
    source_file: str = "unknown",
) -> list[RealExamQuestionCandidate]:
    """Extract exam question candidates from OCR blocks."""
    questions: list[RealExamQuestionCandidate] = []

    for block in blocks:
        text = block.get("text", "") or block.get("content", "")
        page = block.get("source_page", 0) or block.get("page_number", 0)
        conf = block.get("confidence", 0.0)
        bt = block.get("block_type", "text")

        # Only process blocks tagged as question, or containing question-like markers
        if bt != "question" and not ("?" in text or "求" in text or "计算" in text or "写出" in text):
            continue

        if is_ocr_noise(text, conf) or len(text) < 10:
            continue

        cleaned = clean_ocr_text(text)

        # Infer question type
        qtype = "unknown"
        if re.search(r'[A-D]\s*[\.\．]', cleaned):
            qtype = "choice"
        elif "计算" in cleaned or "求" in cleaned:
            qtype = "compute"
        elif "写出" in cleaned or "简述" in cleaned or "证明" in cleaned:
            qtype = "short"
        elif "综合" in cleaned:
            qtype = "comprehensive"

        # Infer concepts
        concepts = []
        for cid, info in CONCEPT_KEYWORDS.items():
            if any(kw in cleaned for kw in info["keywords"]):
                concepts.append(cid)

        questions.append(RealExamQuestionCandidate(
            question_id=f"q_{source_file[:10]}_p{page}_{len(questions)}",
            source_file=source_file,
            page_number=page,
            raw_text=cleaned[:500],
            inferred_question_type=qtype,
            inferred_concepts=concepts,
            confidence=conf,
        ))

    return questions


def extract_real_source_refs(
    blocks: list[dict[str, Any]],
    source_file: str = "unknown",
) -> list[RealSourceRef]:
    """Extract clean source references from blocks."""
    refs: list[RealSourceRef] = []
    for block in blocks[:50]:  # cap
        text = block.get("text", "") or block.get("content", "")
        conf = block.get("confidence", 0.0)
        if is_ocr_noise(text, conf) or len(text) < 15:
            continue
        cleaned = clean_ocr_text(text)
        cid = None
        for concept_id, info in CONCEPT_KEYWORDS.items():
            if any(kw in cleaned for kw in info["keywords"]):
                cid = concept_id
                break
        refs.append(RealSourceRef(
            source_file=source_file,
            page_number=block.get("source_page", 0),
            snippet=cleaned[:150],
            concept_id=cid,
        ))
    return refs


def build_review_sections(
    concept_evidence: list[RealConceptEvidence],
    profile: Any = None,
) -> list[dict[str, Any]]:
    """Build review sections from concept evidence."""
    sections: list[dict[str, Any]] = []
    by_concept: dict[str, list[RealConceptEvidence]] = {}
    for ev in concept_evidence:
        by_concept.setdefault(ev.concept_id, []).append(ev)

    for cid, info in CONCEPT_KEYWORDS.items():
        ev_list = by_concept.get(cid, [])
        section = {
            "concept_id": cid,
            "concept_name": info["name"],
            "has_real_evidence": len(ev_list) > 0,
            "evidence_count": len(ev_list),
            "sources": [],
            "is_weak_point": False,
        }
        for ev in ev_list[:3]:
            section["sources"].append({
                "source_file": ev.source_file,
                "page": ev.page_number,
                "snippet": ev.evidence_text[:120],
                "confidence": ev.confidence,
            })

        # Check if this is a weak point
        if profile is not None:
            try:
                if info["name"] in (profile.weak_points or []):
                    section["is_weak_point"] = True
            except Exception:
                pass

        sections.append(section)

    return sections
