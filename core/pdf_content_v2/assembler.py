"""Assemble PDF 2.0/5.0 cards into four evidence-first document types.

PDF 5.0: Course-aware assembly. Concept ordering is driven by CourseProfile,
not hardcoded per-course dictionaries. No course names appear in logic.
"""

from __future__ import annotations

from typing import Any

from core.pdf_content_v2.builder import get_course_config
from core.pdf_content_v2.models import (
    ConceptCard,
    ExamPatternCard,
    ExampleCard,
    LectureDocument,
    LectureSection,
    MarginNote,
)


def get_concept_order(course_id: str, pdf_type: str,
                      deck: dict[str, Any] | None = None) -> list[str]:
    """Get the concept ordering for a course and PDF type.

    PDF 5.0: Uses CourseProfile.expected_concepts for ordering.
    Falls back to alphabetical if no profile available.

    Ordering rules:
        - Sprint: top 4-6 concepts by exam frequency (from exam_patterns)
        - Review: all concepts in textbook/profile order
        - PastPaper: concepts with exam data (max 6)
        - MockExam: all concepts in textbook/profile order
    """
    config = get_course_config(course_id)
    profile_concepts = []

    # Try to get concept ordering from CourseProfile
    try:
        from core.course_profiles.profile_registry import get_profile
        profile = get_profile(course_id)
        profile_concepts = list(profile.expected_concepts)
    except Exception:
        pass

    # If we have the deck, compute frequencies for Sprint ordering
    exam_freq: dict[str, int] = {}
    if deck:
        patterns = deck.get("exam_patterns", {})
        for cid, pat in patterns.items():
            exam_freq[cid] = pat.get("frequency", 0)

    # Map profile concept names to concept IDs used in the deck
    if deck and profile_concepts:
        deck_concepts = deck.get("concepts", {})
        # Try to match profile concept names to deck concept IDs
        mapped = []
        for pc_name in profile_concepts:
            for dc_id, dc_data in deck_concepts.items():
                dc_title = dc_data.get("title", "") if isinstance(dc_data, dict) else getattr(dc_data, "title", "")
                if pc_name in dc_title or dc_title in pc_name or dc_id == pc_name:
                    mapped.append(dc_id)
                    break
            else:
                # No match found — use the profile concept name directly
                mapped.append(pc_name)
        profile_concepts = mapped

    if pdf_type == "Sprint":
        if exam_freq:
            # Pick top concepts by exam frequency (max 6)
            sorted_concepts = sorted(exam_freq.keys(), key=lambda c: exam_freq.get(c, 0), reverse=True)
            return sorted_concepts[:6] if len(sorted_concepts) > 6 else sorted_concepts
        # No frequency data — use first 4-6 concepts
        concepts = list(deck.get("concepts", {}).keys()) if deck else profile_concepts
        return concepts[:5] if len(concepts) > 5 else concepts

    elif pdf_type == "PastPaper":
        if exam_freq:
            # Only concepts with exam data
            sorted_concepts = sorted(exam_freq.keys(), key=lambda c: exam_freq.get(c, 0), reverse=True)
            return sorted_concepts[:6] if len(sorted_concepts) > 6 else sorted_concepts
        concepts = list(deck.get("concepts", {}).keys()) if deck else profile_concepts
        return concepts[:6] if len(concepts) > 6 else concepts

    else:  # Review, MockExam — textbook/profile order
        concepts = (list(deck.get("concepts", {}).keys()) if deck
                    else profile_concepts)
        return concepts


def get_document_metadata(course_id: str, pdf_type: str) -> dict:
    """Get course-aware titles, subtitles, and metadata for a PDF type."""
    config = get_course_config(course_id)
    if config:
        course_name = config.get("course_name", "未知课程")
        chapter_name = config.get("chapter_name", "")
        is_demo = config.get("is_demo", False)
    else:
        course_name = "未知课程"
        chapter_name = ""
        is_demo = True

    demo_prefix = "Demo only — " if is_demo else ""

    titles = {
        "Sprint": f"{demo_prefix}{course_name} {chapter_name} · 30分钟冲刺讲义",
        "Review": f"{demo_prefix}{course_name} {chapter_name} · Evidence-first 系统复习讲义",
        "PastPaper": f"{demo_prefix}{course_name} {chapter_name} · 真题题型精讲",
        "MockExam": f"{demo_prefix}{course_name} {chapter_name} · Source-aligned 模拟考试",
    }
    subtitles = {
        "Sprint": f"{chapter_name} — 只保留高频公式、考法入口和每个考点 1 道经典例题。",
        "Review": f"按教材顺序讲清概念、公式、例题、真题考法和易错点。",
        "PastPaper": f"从真题考点回到教材例题，再生成同考法变式并给出完整评分点。",
        "MockExam": f"题型、分值、答案和评分点均对齐已有教材/真题证据。总分 100 分。",
    }

    if is_demo:
        subtitles = {k: f"[Demo only — No user textbook uploaded] {v}" for k, v in subtitles.items()}

    return {
        "title": titles.get(pdf_type, titles["Review"]),
        "subtitle": subtitles.get(pdf_type, subtitles["Review"]),
        "chapter": f"{course_name} {chapter_name}".strip(),
        "is_demo": is_demo,
    }


def assemble_documents(deck: dict[str, Any],
                       course_id: str = "field_wave_ch1") -> dict[str, LectureDocument]:
    """Assemble four PDF document types from an evidence deck.

    PDF 5.0: Course-aware. Uses course_id to determine concept ordering
    and document metadata. No hardcoded concept lists.
    """
    concepts = {k: _concept(v) for k, v in deck["concepts"].items()}
    examples = [_example(v) for v in deck["examples"].values()]
    patterns = {k: _pattern(v) for k, v in deck["exam_patterns"].items()}
    examples_by_concept: dict[str, list[ExampleCard]] = {}
    for example in examples:
        examples_by_concept.setdefault(example.concept_id, []).append(example)

    result = {}
    for pdf_type in ["Sprint", "Review", "PastPaper", "MockExam"]:
        result[pdf_type] = _build_document(pdf_type, concepts, examples_by_concept,
                                           patterns, course_id, deck)
    return result


def _build_document(
    pdf_type: str,
    concepts: dict[str, ConceptCard],
    examples_by_concept: dict[str, list[ExampleCard]],
    patterns: dict[str, ExamPatternCard],
    course_id: str = "field_wave_ch1",
    deck: dict[str, Any] | None = None,
) -> LectureDocument:
    order = get_concept_order(course_id, pdf_type, deck)
    meta = get_document_metadata(course_id, pdf_type)
    sections = []
    for cid in order:
        concept = concepts.get(cid)
        if not concept:
            continue
        example_limit = 1 if pdf_type == "Sprint" else 2
        section_examples = _rank_examples(examples_by_concept.get(cid, []), pdf_type)[:example_limit]
        pattern = patterns.get(cid)
        notes = list(concept.margin_notes)
        if pattern:
            notes.append(MarginNote("exam", f"考频：近 5 年 {pattern.frequency} 次；题型：{' / '.join(pattern.question_types)}"))
        sections.append(
            LectureSection(
                section_id=f"{pdf_type.lower()}_{cid}",
                title=concept.title,
                concept=concept,
                examples=section_examples,
                exam_pattern=pattern,
                margin_notes=notes,
            )
        )
    return LectureDocument(
        document_id=f"pdf_v2_{course_id}_{pdf_type.lower()}",
        pdf_type=pdf_type,  # type: ignore[arg-type]
        title=meta["title"],
        subtitle=meta["subtitle"],
        sections=sections,
        source_aligned=all(s.concept and s.concept.has_source() for s in sections),
        target_pages=_target_pages(pdf_type),
        metadata={"chapter": meta["chapter"], "content_policy": "evidence-first, no free-form whole-PDF LLM"},
    )


def _rank_examples(examples: list[ExampleCard], pdf_type: str) -> list[ExampleCard]:
    if pdf_type == "PastPaper":
        return sorted(examples, key=lambda e: (e.source_type != "generated_variant", -e.difficulty))
    if pdf_type == "Sprint":
        return sorted(examples, key=lambda e: (-e.difficulty, e.source_type == "generated_variant"))
    return sorted(examples, key=lambda e: (e.source_type == "generated_variant", -e.difficulty))


def _target_pages(pdf_type: str) -> str:
    return {"Sprint": "5-8", "Review": "20-40", "PastPaper": "12-24", "MockExam": "8-16"}[pdf_type]


def _concept(data: dict[str, Any]) -> ConceptCard:
    from core.pdf_content_v2.models import FormulaCard, SourceRef

    def ref(raw: dict[str, Any]) -> SourceRef:
        return SourceRef(**raw)

    formulas = []
    for f in data.get("formulas", []):
        formulas.append(FormulaCard(**{**f, "source_refs": [ref(r) for r in f.get("source_refs", [])]}))
    return ConceptCard(
        **{
            **data,
            "textbook_evidence": [ref(r) for r in data.get("textbook_evidence", [])],
            "ppt_evidence": [ref(r) for r in data.get("ppt_evidence", [])],
            "exam_evidence": [ref(r) for r in data.get("exam_evidence", [])],
            "formulas": formulas,
            "source_refs": [ref(r) for r in data.get("source_refs", [])],
            "margin_notes": [MarginNote(type=n["type"], content=n["content"], source_ref=ref(n["source_ref"]) if n.get("source_ref") else None) for n in data.get("margin_notes", [])],
        }
    )


def _example(data: dict[str, Any]) -> ExampleCard:
    from core.pdf_content_v2.models import SourceRef
    return ExampleCard(**{**data, "source_refs": [SourceRef(**r) for r in data.get("source_refs", [])]})


def _pattern(data: dict[str, Any]) -> ExamPatternCard:
    from core.pdf_content_v2.models import SourceRef
    return ExamPatternCard(**{**data, "past_exam_refs": [SourceRef(**r) for r in data.get("past_exam_refs", [])]})


# ═══════════════════════════════════════════════════════════════════════════
# Backward-compatible wrappers (deprecated — use assemble_documents(deck, course_id))
# ═══════════════════════════════════════════════════════════════════════════

def assemble_probability_ch2_documents(deck: dict[str, Any]) -> dict[str, LectureDocument]:
    """[DEPRECATED] Use assemble_documents(deck, 'probability_ch2') instead."""
    return assemble_documents(deck, "probability_ch2")
