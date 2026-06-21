#!/usr/bin/env python3
"""Final Quality Gate — unified evaluation across all validators."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("Final Quality Gate — 概率论第二章")
    print("=" * 60)

    from core.pdf_content_v2.final_quality import FinalQualityGate

    gate = FinalQualityGate()
    report = gate.evaluate()

    rd = report.to_dict()

    print(f"\n📊 Quality Scores:")
    print(f"   correctness:   {rd['correctness_score']:.1f} / 100")
    print(f"   coverage:      {rd['coverage_score']:.1f} / 100")
    print(f"   pedagogy:      {rd['pedagogy_score']:.1f} / 100")
    print(f"   layout:        {rd['layout_score']:.1f} / 100")
    print(f"   diversity:     {rd['diversity_score']:.1f} / 100")
    print(f"   reliability:   {rd['reliability_score']:.1f} / 100")
    print(f"   ─────────────────────────────")
    print(f"   FINAL SCORE:   {rd['final_score']:.1f} / 100")
    print(f"   RELEASE LEVEL: {rd['release_level']}")

    print(f"\n🔒 Hard Gates:")
    for key, detail in rd.get("gate_details", {}).items():
        icon = "✅" if detail["passed"] else "❌"
        print(f"   {icon} {detail['desc']}: {detail['value']} (threshold: {detail['threshold']})")

    if rd["issues"]:
        print(f"\n⚠️  Issues:")
        for issue in rd["issues"]:
            print(f"   - {issue}")

    print(f"\n{'='*60}")
    print(f"Hard gate pass:           {'✅' if rd['hard_gate_pass'] else '❌'}")
    print(f"Manual acceptance:        {'✅ Recommended' if rd['manual_acceptance_recommended'] else '❌ Not recommended'}")

    # Save
    rp = Path("data/outputs/pdf_v2_probability_ch2/final_quality_report.json")
    rp.write_text(json.dumps(rd, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {rp}")

    return 0 if rd["hard_gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
