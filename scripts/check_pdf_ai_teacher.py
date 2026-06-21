#!/usr/bin/env python3
"""AI Teacher Layer — generate TeacherNotes and run quality review."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("AI Teacher Layer — 概率论第二章 TeacherNotes")
    print("=" * 60)

    from core.pdf_content_v2.ai_teacher import (
        AITeacher, StudentLevel, StudentLevelAdapter, TeacherReviewer,
    )

    # ── Load concepts from seed data ──
    concepts_path = Path("data/golden_chapters/math/probability_random_var_ch2/concepts.json")
    if not concepts_path.exists():
        print("❌ concepts.json not found")
        return 1
    concepts = json.loads(concepts_path.read_text(encoding="utf-8"))
    print(f"\n📚 Loaded {len(concepts)} concepts")

    # ── 1. Generate TeacherNotes (math subject type) ──
    teacher = AITeacher(subject_type="math")
    notes = teacher.generate_all(concepts)
    print(f"📝 Generated {len(notes)} TeacherNotes")

    # Show sample
    for note in notes[:3]:
        print(f"\n  [{note.concept_id}] score={note.teacher_score()}")
        print(f"    为什么考: {note.why_exam_likes_it[:80]}...")
        print(f"    考前提醒: {note.exam_tip[:60]}...")
        print(f"    易错: {', '.join(note.common_mistakes[:2])}")

    # ── 2. Student level adaptation ──
    print(f"\n🎓 Student Level Adaptation:")
    for level in [StudentLevel.BEGINNER, StudentLevel.EXAM_SPRINT]:
        adapter = StudentLevelAdapter(level)
        adapted = adapter.adapt(notes[0])
        print(f"   {level.value}: tip='{adapted.exam_tip[:60]}...'")

    # ── 3. Run Teacher Reviewer ──
    all_typst = ""
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        p = Path(f"data/outputs/pdf_v2_probability_ch2/StudyPilot_v2_Probability_Ch2_{name}.typ")
        if p.exists():
            all_typst += p.read_text(encoding="utf-8")

    reviewer = TeacherReviewer()
    report = reviewer.review(notes, typst_text=all_typst)

    print(f"\n{'='*60}")
    print(f"📊 Teacher Review Report:")
    print(f"  teacher_note_count:            {report.teacher_note_count}")
    print(f"  empty_advice_count:            {report.empty_advice_count}")
    print(f"  missing_exam_strategy_count:   {report.missing_exam_strategy_count}")
    print(f"  missing_common_mistake_count:  {report.missing_common_mistake_count}")
    print(f"  teacher_like_score:            {report.teacher_like_score:.1f}/100")
    print(f"  student_level_adaptation_pass: {report.student_level_adaptation_pass}")

    if report.issues:
        print(f"\n  Issues ({len(report.issues)}):")
        for iss in report.issues[:8]:
            print(f"    {iss['type']}: {iss['concept']}")

    # ── 4. Hard gates ──
    hard_pass = report.passed
    print(f"\n硬门禁: {'✅ PASSED' if hard_pass else '❌ FAILED'}")
    print(f"  teacher_like_score >= 85:        {'✅' if report.teacher_like_score >= 85 else '❌ ' + str(round(report.teacher_like_score, 1))}")
    print(f"  empty_advice_count == 0:         {'✅' if report.empty_advice_count == 0 else '❌ ' + str(report.empty_advice_count)}")
    print(f"  missing_exam_strategy_count == 0: {'✅' if report.missing_exam_strategy_count == 0 else '❌ ' + str(report.missing_exam_strategy_count)}")

    # Save
    rp = Path("data/outputs/pdf_v2_probability_ch2/ai_teacher_report.json")
    report_data = report.to_dict()
    report_data["notes"] = [n.to_dict() for n in notes]
    rp.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {rp}")

    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
