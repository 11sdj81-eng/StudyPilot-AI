#!/usr/bin/env python3
"""4-level question deduplication across all 4 probability Ch2 PDFs."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def extract_all_questions(typst_dir: Path) -> list[dict]:
    """Extract questions from all Typst files with source PDF tagging."""
    all_questions = []
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        path = typst_dir / f"StudyPilot_v2_Probability_Ch2_{name}.typ"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")

        # Choice questions
        for m in re.finditer(
            r'#question\("(\d+)",\s*"选择题",\s*"(\d+)",\s*"([^"]+)",\s*\(([^)]+)\),\s*"([^"]*)"\)',
            text
        ):
            all_questions.append({
                "id": f"{name}_choice_{m.group(1)}", "type": "选择题",
                "score": m.group(2), "stem": m.group(3), "source_pdf": name,
            })

        # Open questions
        for m in re.finditer(
            r'#open-question\("(\d+)",\s*"([^"]+)",\s*"(\d+)",\s*"([^"]+)",\s*"([^"]*)"\)',
            text
        ):
            qtype = m.group(2)
            all_questions.append({
                "id": f"{name}_open_{m.group(1)}", "type": qtype,
                "score": m.group(3), "stem": m.group(4), "source_pdf": name,
                "problem": m.group(4),
            })

        # Example cards (in Review/Sprint/PastPaper)
        for m in re.finditer(r'#example-card\("([^"]+)",\s*"([^"]*)"\)\[(.*?)\]', text, re.DOTALL):
            card_text = m.group(3)
            problem_match = re.search(r'#strong\[题目\][：:]?\s*(.+?)(?:\n|$)', card_text)
            if problem_match:
                all_questions.append({
                    "id": f"{name}_example_{len(all_questions)}", "type": "例题",
                    "source_type": m.group(1), "stem": problem_match.group(1)[:120],
                    "source_pdf": name, "problem": problem_match.group(1)[:120],
                })

    return all_questions


def main():
    print("=" * 60)
    print("Question Deduplication — 概率论第二章 (4-level)")
    print("=" * 60)

    from core.pdf_content_v2.question_dedup import QuestionDeduplicator

    typst_dir = Path("data/outputs/pdf_v2_probability_ch2")
    questions = extract_all_questions(typst_dir)

    if not questions:
        print("❌ No questions found")
        return 1

    print(f"\n📝 Extracted {len(questions)} questions across 4 PDFs")
    pdf_counts = {}
    for q in questions:
        pdf_counts[q["source_pdf"]] = pdf_counts.get(q["source_pdf"], 0) + 1
    for pdf, count in sorted(pdf_counts.items()):
        print(f"   {pdf}: {count} questions")

    # Run dedup
    dedup = QuestionDeduplicator()
    for q in questions:
        dedup.add_questions([q], source_pdf=q.get("source_pdf", ""))

    report = dedup.check_all()
    dr = report.to_dict()

    # ── Print by level ──
    print(f"\n🔍 四层检测结果:")
    print(f"   Level 1 (Exact):       {dr['exact_duplicate_count']}")
    print(f"   Level 2 (Normalized):  {dr['normalized_duplicate_count']}")
    print(f"   Level 3 (Pattern):     {dr['pattern_duplicate_count']}")
    print(f"   Level 4 (Semantic):    {dr['semantic_duplicate_count']}")
    print(f"   Cross-PDF:             {dr['cross_pdf_duplicate_count']}")
    print(f"   Diversity Score:       {dr['diversity_score']:.1f}/100")

    # ── Show dups by type ──
    if dr["duplicates"]:
        print(f"\n📋 Duplicate pairs ({len(dr['duplicates'])} found):")
        by_level = {}
        for d in dr["duplicates"]:
            lv = d["level"]
            by_level.setdefault(lv, []).append(d)
        for lv in ["EXACT", "NORMALIZED", "PATTERN", "SEMANTIC"]:
            pairs = by_level.get(lv, [])
            if pairs:
                print(f"\n   [{lv}] ({len(pairs)} pairs):")
                for p in pairs[:5]:
                    print(f"     {p['q1']} ↔ {p['q2']} ({p['q1_source']}↔{p['q2_source']}) sim={p['similarity']:.3f}")
                if len(pairs) > 5:
                    print(f"     ... and {len(pairs)-5} more")

    # ── Cross-PDF check ──
    cross = [d for d in dr["duplicates"] if d["q1_source"] != d["q2_source"]]
    if cross:
        print(f"\n⚠️ Cross-PDF duplicates ({len(cross)}):")
        mock_cross = [d for d in cross if "MockExam" in (d["q1_source"], d["q2_source"])]
        if mock_cross:
            print(f"   MockExam copies: {len(mock_cross)}")
            for d in mock_cross[:5]:
                print(f"     {d['q1']} ({d['q1_source']}) ↔ {d['q2']} ({d['q2_source']})")

    # ── Hard gates ──
    hard_pass = (
        dr["cross_pdf_duplicate_count"] == 0
        and dr["diversity_score"] >= 80
        and dr["exact_duplicate_count"] == 0
    )
    print(f"\n{'='*60}")
    print(f"硬门禁: {'✅ 通过' if hard_pass else '❌ 未通过'}")
    print(f"  cross_pdf_duplicate=0:  {'✅' if dr['cross_pdf_duplicate_count'] == 0 else '❌'}")
    print(f"  diversity_score ≥ 80:   {'✅' if dr['diversity_score'] >= 80 else '❌ ' + str(dr['diversity_score'])}")
    print(f"  exact_duplicate=0:       {'✅' if dr['exact_duplicate_count'] == 0 else '❌'}")

    # Save report
    report_path = typst_dir / "duplicate_report.json"
    report_path.write_text(json.dumps(dr, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {report_path}")

    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
