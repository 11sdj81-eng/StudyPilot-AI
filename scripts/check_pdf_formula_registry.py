#!/usr/bin/env python3
"""Check FormulaRegistry integrity and PDF formula compliance."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("Formula Registry 验收检查")
    print("=" * 60)

    all_pass = True

    # ── 1. Registry loading ──
    try:
        from core.pdf_content_v2.formula_registry import get_registry
        registry = get_registry()
        stats = registry.stats()
        print(f"\n✅ Registry loaded: {stats['total_registered']} formulas registered")
        print(f"   By level: {stats['by_source_level']}")
    except Exception as e:
        print(f"❌ Registry load failed: {e}")
        return 1

    # ── 2. Probability Ch2 expected formulas ──
    expected_ids = registry.get_expected_ids("probability_ch2")
    print(f"\n📊 概率论第二章 expected formulas: {len(expected_ids)}")
    for fid in expected_ids:
        f = registry.lookup(fid)
        if f:
            print(f"   ✅ {fid}: {f.title}")
        else:
            print(f"   ❌ {fid}: NOT FOUND")
            all_pass = False

    # ── 3. PDF content check ──
    typst_dir = Path("data/outputs/pdf_v2_probability_ch2")
    all_typst = ""
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        path = typst_dir / f"StudyPilot_v2_Probability_Ch2_{name}.typ"
        if path.exists():
            all_typst += path.read_text(encoding="utf-8")

    if all_typst:
        from core.pdf_content_v2.quality.formula_validator import FormulaValidator
        fv = FormulaValidator()
        report = fv.validate("probability_ch2", all_typst)

        print(f"\n🔬 Formula Validator Report:")
        print(f"   expected:    {report.expected_formula_count}")
        print(f"   covered:     {report.covered_formula_count}")
        print(f"   missing:     {report.missing_formulas}")
        print(f"   unregistered:{report.unregistered_formula_count}")
        print(f"   latex_leak:  {report.latex_leak_count}")
        print(f"   cond_missing:{report.condition_missing_count}")
        print(f"   duplicates:  {report.duplicate_formula_variant_count}")
        print(f"   formula_issues: {report.formula_issue_count}")
        print(f"   PASSED:      {report.passed}")

        if report.missing_formulas:
            print(f"\n   ⚠️ Missing formulas detected: {report.missing_formulas}")
        if report.latex_leak_count > 0:
            print(f"   ⚠️ LaTeX leaks detected: {report.latex_leak_count}")
        if not report.passed:
            all_pass = False
    else:
        print("\n⚠️ No Typst files found — skipping content check")

    # ── 4. Cross-course coverage ──
    for course_id in ["field_wave_ch1", "digital_logic_ch3"]:
        formulas = registry.by_course(course_id)
        print(f"\n   {course_id}: {len(formulas)} formulas registered")

    # ── 5. Unverified queue ──
    print(f"\n   Unverified queue: {registry.unverified_count()}")

    print("\n" + "=" * 60)
    print(f"总体: {'✅ 通过' if all_pass else '⚠️ 存在问题（详见报告）'}")
    print("=" * 60)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
