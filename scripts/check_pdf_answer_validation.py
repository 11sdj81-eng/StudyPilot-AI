#!/usr/bin/env python3
"""Validate answers in probability chapter 2 MockExam using sympy-backed ProbabilityValidator."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def extract_questions_from_typst(typst_path: Path) -> list[dict]:
    """Extract question/answer pairs from MockExam Typst source."""
    if not typst_path.exists():
        return []
    text = typst_path.read_text(encoding="utf-8")
    questions = []

    # Extract choice questions: #question("1", "选择题", "4", "stem", ("A. ...", "B. ..."), "source")
    choice_pattern = re.findall(
        r'#question\("(\d+)",\s*"选择题",\s*"(\d+)",\s*"([^"]+)",\s*\(([^)]+)\),\s*"([^"]*)"\)',
        text
    )
    for num, score, stem, options, source in choice_pattern:
        questions.append({
            "id": f"choice_{num}", "type": "选择题", "score": score,
            "stem": stem, "options": options, "source": source,
            "answer": "",  # will be extracted separately
        })

    # Extract fill/open questions
    open_pattern = re.findall(
        r'#open-question\("(\d+)",\s*"([^"]+)",\s*"(\d+)",\s*"([^"]+)",\s*"([^"]*)"\)',
        text
    )
    for num, qtype, score, stem, source in open_pattern:
        questions.append({
            "id": f"open_{num}", "type": qtype, "score": score,
            "stem": stem, "source": source, "answer": "",
            "problem": stem,
        })

    # Extract answers from the answer section
    answer_section = text.split("标准答案")[-1] if "标准答案" in text else text
    answer_lines = re.findall(r'(\d+)\.\s+(.+?)(?:\n|$)', answer_section)

    for num_str, answer_text in answer_lines:
        num = int(num_str)
        for q in questions:
            qnum = int(re.search(r'(\d+)', q["id"]).group(1))
            if qnum == num:
                q["answer"] = answer_text.strip()
                q["standard_answer"] = answer_text.strip()
                break

    return questions


def main():
    print("=" * 60)
    print("Answer Validation — 概率论第二章 MockExam")
    print("=" * 60)

    from core.pdf_content_v2.answer_validation import ProbabilityValidator
    from core.pdf_content_v2.answer_validation.answer_validator import ValidationReport

    validator = ProbabilityValidator()

    # Load MockExam typst
    typst_path = Path("data/outputs/pdf_v2_probability_ch2/StudyPilot_v2_Probability_Ch2_MockExam.typ")
    questions = extract_questions_from_typst(typst_path)

    if not questions:
        print("❌ No questions found in MockExam typst")
        return 1

    print(f"\n📝 Extracted {len(questions)} questions from MockExam")

    # Validate each question
    report = ValidationReport()
    for q in questions:
        result = validator.validate(q)
        report.validated_questions += 1
        if not result.is_valid:
            report.failed_questions += 1
            report.answer_error_count += 1
        if result.confidence < 0.7:
            report.manual_review_questions += 1

        icon = "✅" if result.is_valid else "❌"
        print(f"  {icon} {q['id']} [{q['type']}]: {result.message} (conf={result.confidence:.2f})")

    report.passed_questions = report.validated_questions - report.failed_questions
    report.validation_rate = (
        report.passed_questions / report.validated_questions
        if report.validated_questions > 0 else 0.0
    )
    report.passed = report.answer_error_count == 0

    # ── Run domain-specific batch checks ──
    print(f"\n🔬 Domain-specific checks:")

    all_text = ""
    for q in questions:
        all_text += str(q.get("stem", "")) + " " + str(q.get("answer", ""))

    # Poisson check
    if "泊松" in all_text or "λ" in all_text:
        lam_match = re.search(r'[λl]\s*[=＝]\s*([0-9.]+)', all_text)
        if lam_match:
            lam = float(lam_match.group(1))
            pr = validator.validate_poisson(lam)
            print(f"  泊松分布 λ={lam}: {'✅' if pr.is_valid else '❌'} {pr.message}")

    # Binomial check
    if "二项" in all_text or "B(" in all_text:
        binom_match = re.search(r'[Bb]\s*\(\s*(\d+)\s*,\s*([0-9.]+)\s*\)', all_text)
        if binom_match:
            n, p = int(binom_match.group(1)), float(binom_match.group(2))
            br = validator.validate_binomial(n, p)
            print(f"  二项分布 B({n},{p}): {'✅' if br.is_valid else '❌'} {br.message}")

    # Normal standardization check
    if "正态" in all_text or "N(" in all_text:
        nr = validator.validate_normal_standardization(all_text)
        print(f"  正态标准化: {'✅' if nr.is_valid else '❌'} {nr.message}")

    # ── Report ──
    report_path = Path("data/outputs/pdf_v2_probability_ch2/answer_validation_report.json")
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📊 Validation Report:")
    print(f"  validated_questions:    {report.validated_questions}")
    print(f"  passed_questions:       {report.passed_questions}")
    print(f"  failed_questions:       {report.failed_questions}")
    print(f"  manual_review_questions:{report.manual_review_questions}")
    print(f"  validation_rate:        {report.validation_rate:.1%}")
    print(f"  answer_error_count:     {report.answer_error_count}")
    print(f"  overall:                {'✅ PASSED' if report.passed else '⚠️ ISSUES FOUND'}")

    # ── Hard gates ──
    hard_pass = report.answer_error_count == 0 and report.validation_rate >= 0.95
    print(f"\n  硬门禁: {'✅' if hard_pass else '❌'} (answer_error=0 & validation_rate≥95%)")
    return 0 if hard_pass else 1


if __name__ == "__main__":
    sys.exit(main())
