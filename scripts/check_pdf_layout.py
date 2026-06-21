#!/usr/bin/env python3
"""Layout Validator — analyze all 4 probability Ch2 PDFs."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("Layout Validator — 概率论第二章 四份 PDF")
    print("=" * 60)

    from core.pdf_content_v2.layout import LayoutValidator

    validator = LayoutValidator()
    out_dir = Path("data/outputs/pdf_v2_probability_ch2")

    all_pass = True
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        pdf_path = out_dir / f"StudyPilot_v2_Probability_Ch2_{name}.pdf"
        if not pdf_path.exists():
            print(f"\n  ❌ {name}: PDF not found")
            all_pass = False
            continue

        report = validator.validate(pdf_path, pdf_type=name)

        print(f"\n{'─'*50}")
        print(f"📄 {name} ({report.page_count} pages)")
        print(f"   critical:  {report.critical_layout_issue_count}")
        print(f"   warning:   {report.warning_layout_issue_count}")
        print(f"   blank:     {report.blank_page_risk_count}")
        print(f"   crowded:   {report.overcrowded_page_count}")
        print(f"   overlap:   {report.text_image_overlap_count}")
        print(f"   formula:   {report.formula_overflow_count}")
        print(f"   table:     {report.table_overflow_count}")
        print(f"   orphan:    {report.orphan_heading_count}")
        print(f"   footer:    {report.footer_overlap_count}")
        print(f"   PASSED:    {'✅' if report.passed else '❌'}")

        if report.pages:
            page_issues = [p for p in report.pages if isinstance(p, dict) and p.get("issue_codes")]
            if page_issues:
                for p in page_issues[:3]:
                    print(f"   p{p['page_number']}: {p['issue_codes']} (density={p.get('content_density', 0):.2f})")

        # Save per-PDF report
        rp = out_dir / f"layout_report_{name.lower()}.json"
        rp.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if not report.passed:
            all_pass = False

    print(f"\n{'='*60}")
    print(f"总体: {'✅ 全部通过' if all_pass else '⚠️ 存在 layout issues（详见报告）'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
