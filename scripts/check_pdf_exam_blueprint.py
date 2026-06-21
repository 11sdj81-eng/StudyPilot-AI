#!/usr/bin/env python3
"""Validate MockExam against ExamBlueprint for probability chapter 2."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("Exam Blueprint Validation — 概率论第二章 MockExam")
    print("=" * 60)

    from core.pdf_content_v2.exam_blueprint import (
        ExamBlueprintRegistry, ExamBlueprintValidator, BlueprintValidationReport,
    )
    from core.pdf_content_v2.exam_blueprint.exam_distribution_analyzer import ExamDistributionAnalyzer

    # ── 1. Get blueprint ──
    registry = ExamBlueprintRegistry()
    bp = registry.get("probability_ch2")
    if not bp:
        print("❌ Blueprint not found")
        return 1

    print(f"\n📋 Blueprint: {bp.course_name} / {bp.chapter_name}")
    print(f"   Source: {bp.source.value} (confidence={bp.confidence})")
    for s in bp.sections:
        print(f"   {s.section_name}: {s.question_count}题×{s.score_per_question}分 = {s.total_score}分")
    print(f"   Total: {bp.section_total()}")
    print(f"   Difficulty: {bp.difficulty_distribution}")
    print(f"   Concept weights: {bp.concept_weight_distribution}")

    # ── 2. Run distribution analyzer ──
    print(f"\n📊 Distribution Analyzer:")
    analyzer = ExamDistributionAnalyzer()
    dist_report = analyzer.analyze("probability_ch2")
    source, conf = analyzer.should_use_blueprint()
    print(f"   Source: {analyzer.get_source_label()}")
    print(f"   Confidence: {conf:.2f}")
    print(f"   Detected exams: {dist_report.detected_exam_count}")
    print(f"   Sections found: {dist_report.section_distribution}")

    # ── 3. Validate MockExam against blueprint ──
    typst_path = Path("data/outputs/pdf_v2_probability_ch2/StudyPilot_v2_Probability_Ch2_MockExam.typ")
    typst_text = ""
    answer_letters = []

    if typst_path.exists():
        typst_text = typst_path.read_text(encoding="utf-8")
        answer_letters = [l for _, l in re.findall(r'(\d+)\.\s*([A-D])', typst_text)]

    validator = ExamBlueprintValidator(bp)
    report = validator.validate(typst_text=typst_text, answer_letters=answer_letters)

    print(f"\n🔍 Validation Report:")
    print(f"   exam_total_score:           {report.exam_total_score}")
    print(f"   section_score_sum_valid:    {report.section_score_sum_valid}")
    print(f"   exam_blueprint_match:       {report.exam_blueprint_match}")
    print(f"   difficulty_distribution:     {report.difficulty_distribution_match}")
    print(f"   concept_weight_match:        {report.concept_weight_match}")
    print(f"   choice_answer_distribution:  {report.choice_answer_distribution}")
    print(f"   blueprint_source:            {report.blueprint_source}")

    for sc in report.section_checks:
        icon = "✅" if sc["valid"] else "❌"
        print(f"   {icon} {sc['section']}: {sc['expected_count']}×{sc['expected_per_score']}={sc['expected_total']}")

    print(f"\n   Choice answers: {answer_letters}")
    if answer_letters:
        same = len(set(answer_letters)) == 1
        print(f"   All same: {'❌ YES (bad)' if same else '✅ No (good)'}")

    # ── 4. Hard gates ──
    hard_pass = report.passed
    print(f"\n{'='*60}")
    print(f"硬门禁:")
    print(f"  exam_total_score == 100:      {'✅' if report.exam_total_score == 100 else '❌'}")
    print(f"  section_score_sum_valid:      {'✅' if report.section_score_sum_valid else '❌'}")
    print(f"  exam_blueprint_match:         {'✅' if report.exam_blueprint_match else '❌'}")
    print(f"  OVERALL:                      {'✅ PASSED' if hard_pass else '❌ FAILED'}")

    # Save report
    report_path = Path("data/outputs/pdf_v2_probability_ch2/exam_blueprint_report.json")
    report_data = report.to_dict()
    report_data["distribution_analysis"] = dist_report.to_dict()
    report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {report_path}")

    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
