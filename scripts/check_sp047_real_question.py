#!/usr/bin/env python3
"""SP-047: Verify Real Question Pipeline — zero template questions."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def extract_questions(typst_path: Path) -> list[dict]:
    if not typst_path.exists():
        return []
    text = typst_path.read_text(encoding="utf-8")
    questions = []
    for m in re.finditer(r'#question\("(\d+)",\s*"(\w+)",\s*"(\d+)",\s*"([^"]+)"', text):
        questions.append({"id": f"q{m.group(1)}", "type": m.group(2), "stem": m.group(4)})
    for m in re.finditer(r'#open-question\("(\d+)",\s*"(\w+)",\s*"(\d+)",\s*"([^"]+)"', text):
        questions.append({"id": f"o{m.group(1)}", "type": m.group(2), "stem": m.group(4)})
    return questions


def main():
    print("=" * 60)
    print("SP-047: Real Question Pipeline Verification")
    print("=" * 60)

    from core.pdf_content_v2.question_pipeline import (
        ExamPatternLibrary, RealQuestionValidator,
    )
    from core.pdf_content_v2.question_pipeline.question_source_priority import (
        SourcePriority, QuestionSource,
    )

    # ── 1. Exam Pattern Library stats ──
    lib = ExamPatternLibrary()
    print(f"\n📚 ExamPatternLibrary:")
    for course_id in lib.all_courses():
        print(f"   {course_id}: {lib.count(course_id)} patterns")

    # ── 2. Validate MockExam questions ──
    typst_path = Path("data/outputs/pdf_v2_probability_ch2/StudyPilot_v2_Probability_Ch2_MockExam.typ")
    questions = extract_questions(typst_path)
    print(f"\n📝 MockExam: {len(questions)} questions extracted")

    validator = RealQuestionValidator("probability_ch2")
    report = validator.validate(questions)

    print(f"\n🔍 Real Question Report:")
    for k, v in report.to_dict().items():
        if k != "issues":
            print(f"   {k}: {v}")

    if report.issues:
        print(f"\n   Issues:")
        for iss in report.issues[:5]:
            print(f"     [{iss['issue']}] {iss['question'][:60]}...")

    # ── 3. Generate real questions from patterns ──
    print(f"\n📋 Sample Real Questions from Patterns:")

    # Select 1 pattern per question type
    types = ["选择题", "填空题", "计算题", "综合题"]
    for qtype in types:
        patterns = lib.get_by_type("probability_ch2", qtype)
        if patterns:
            p = patterns[0]
            q = p.generate()
            print(f"\n   [{qtype}] {p.pattern_id}")
            print(f"   题干: {q['stem'][:100]}...")
            print(f"   答案: {q['answer'][:80]}...")
            print(f"   来源: {q['source']}, 难度: {q['difficulty']}")

    # ── 4. Source Priority Rules ──
    print(f"\n📊 Source Priority:")
    for src in SourcePriority.ORDER:
        print(f"   {src.priority}. {src.label}")
    print(f"\n   AI allowed: {SourcePriority.ai_allowed_actions()}")
    print(f"   AI forbidden: {SourcePriority.ai_forbidden_actions()[:3]}...")

    # ── 5. Hard gate ──
    hard_pass = report.passed
    print(f"\n{'='*60}")
    print(f"硬门禁:")
    print(f"  template_fake == 0:    {'✅' if report.template_fake == 0 else '❌ ' + str(report.template_fake)}")
    print(f"  real_exam_score >= 85: {'✅' if report.real_exam_score >= 85 else '❌ ' + str(report.real_exam_score)}")
    print(f"  OVERALL:              {'✅ PASSED' if hard_pass else '❌ FAILED'}")

    # Save
    rp = Path("data/outputs/pdf_v2_probability_ch2/question_quality_report.json")
    rp.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {rp}")

    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
