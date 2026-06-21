#!/usr/bin/env python3
"""Fake question detection + rewriting for all 4 probability Ch2 PDFs."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def extract_all(typst_dir: Path) -> list[dict]:
    questions = []
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        path = typst_dir / f"StudyPilot_v2_Probability_Ch2_{name}.typ"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r'#question\("(\d+)",\s*"(\w+)",\s*"(\d+)",\s*"([^"]+)"', text):
            questions.append({"id": f"{name}_q{m.group(1)}", "type": m.group(2),
                              "stem": m.group(4), "source": name})
        for m in re.finditer(r'#open-question\("(\d+)",\s*"(\w+)",\s*"(\d+)",\s*"([^"]+)"', text):
            questions.append({"id": f"{name}_o{m.group(1)}", "type": m.group(2),
                              "stem": m.group(4), "source": name})
        for m in re.finditer(r'#strong\[题目\][：:]?\s*(.+?)(?:\n)', text):
            q = m.group(1).strip()
            if len(q) > 15:
                questions.append({"id": f"{name}_ex{len(questions)}", "type": "例题", "stem": q, "source": name})
    return questions


def main():
    print("=" * 60)
    print("Fake Question Detection + Rewriting — 概率论第二章")
    print("=" * 60)

    from core.pdf_content_v2.question_style import (
        FakeQuestionDetector, StyleValidator, RealQuestionRewriter,
    )

    typst_dir = Path("data/outputs/pdf_v2_probability_ch2")
    questions = extract_all(typst_dir)
    print(f"\n📝 提取 {len(questions)} 道题（4份PDF）")

    # ── 1. Fake question detection ──
    detector = FakeQuestionDetector()
    fakes = []
    for q in questions:
        r = detector.detect(q)
        if r.is_fake:
            fakes.append((q, r))
            print(f"\n  ❌ [{r.severity}] {q['id']} ({q['source']})")
            print(f"     题干: {q['stem'][:80]}")
            print(f"     原因: {'; '.join(r.fake_reasons)}")
            print(f"     建议: {r.suggestion}")

    if not fakes:
        print(f"\n  ✅ 所有题目通过假题检测")

    print(f"\n📊 假题统计: {len(fakes)}/{len(questions)}")

    # ── 2. Attempt rewriting ──
    rewriter = RealQuestionRewriter()
    rewritten = 0
    unfixable = 0
    for q, r in fakes:
        if r.can_rewrite:
            rw = rewriter.rewrite(q, r)
            if rw.success:
                rewritten += 1
                print(f"\n  🔄 已重写: {q['id']}")
                print(f"     原文: {rw.original[:60]}...")
                print(f"     新题: {rw.rewritten[:100]}...")
                print(f"     答案: {rw.rewritten_answer[:80]}")
                print(f"     来源: {rw.source_level} (conf={rw.confidence})")
            else:
                unfixable += 1
                print(f"\n  ⚠️ 无法重写: {q['id']} — {rw.strategy}")

    # ── 3. Run full style validator ──
    validator = StyleValidator("probability_ch2")
    report = validator.validate(questions)

    print(f"\n{'='*60}")
    print(f"📋 Style Validation Report:")
    print(f"  checked_question_count:      {report.checked_question_count}")
    print(f"  fake_question_count:         {report.fake_question_count}")
    print(f"  rewritten_question_count:    {report.rewritten_question_count}")
    print(f"  unfixable_fake_question_count: {report.unfixable_fake_question_count}")

    # Hard gate
    hard_pass = report.fake_question_count == 0 and report.unfixable_fake_question_count == 0
    print(f"\n硬门禁: {'✅ PASSED' if hard_pass else '❌ FAILED'}")
    print(f"  fake_question_count == 0:         {'✅' if report.fake_question_count == 0 else '❌ ' + str(report.fake_question_count)}")
    print(f"  unfixable_fake_question_count == 0: {'✅' if report.unfixable_fake_question_count == 0 else '❌ ' + str(report.unfixable_fake_question_count)}")

    # Save report
    rp = typst_dir / "fake_question_report.json"
    rp.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {rp}")
    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
