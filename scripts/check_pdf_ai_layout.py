#!/usr/bin/env python3
"""AI Layout Reviewer — heuristic visual quality assessment for all 4 PDFs."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("AI Layout Reviewer — 概率论第二章 四份 PDF")
    print("=" * 60)

    from core.pdf_content_v2.ai_layout import AILayoutReviewer

    reviewer = AILayoutReviewer(use_ai_vision=False)  # heuristic scoring
    out_dir = Path("data/outputs/pdf_v2_probability_ch2")

    all_pass = True
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        pdf_path = out_dir / f"StudyPilot_v2_Probability_Ch2_{name}.pdf"
        if not pdf_path.exists():
            print(f"\n❌ {name}: PDF not found")
            all_pass = False
            continue

        report = reviewer.review(pdf_path, pdf_type=name)

        print(f"\n{'─'*50}")
        print(f"📄 {name} [{report.scoring_method}]")
        print(f"   overall:        {report.overall_layout_score:.1f}")
        print(f"   textbook_like:  {report.textbook_like_score:.1f}")
        print(f"   teacher_like:   {report.teacher_like_score:.1f}")
        print(f"   printability:   {report.printability_score:.1f}")
        print(f"   avg page:       {report.average_page_score:.1f}")

        gates = [
            report.overall_layout_score >= 85,
            report.textbook_like_score >= 85,
            report.teacher_like_score >= 85,
        ]
        print(f"   hard gates:     {'✅' if all(gates) else '❌ ' + str([round(x,1) for x in [report.overall_layout_score, report.textbook_like_score, report.teacher_like_score]])}")

        # Show worst pages
        bad_pages = [f for f in report.page_feedback if f.get("issues")]
        if bad_pages:
            print(f"   worst pages ({len(bad_pages)} with issues):")
            for fp in sorted(bad_pages, key=lambda x: x["score"])[:3]:
                print(f"     p{fp['page_number']}: score={fp['score']:.0f} issues={fp['issues']}")

        # Save report
        rp = out_dir / f"ai_layout_report_{name.lower()}.json"
        rp.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if not all(gates):
            all_pass = False

    print(f"\n{'='*60}")
    print(f"评分方式: heuristic (PyMuPDF metrics)")
    print(f"总体: {'✅ 全部通过' if all_pass else '⚠️ 部分未达 85 分阈值'}")
    print(f"{'='*60}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
