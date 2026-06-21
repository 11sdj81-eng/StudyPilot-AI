#!/usr/bin/env python3
"""Check probability chapter 2 PDF 2.0 outputs for correctness."""

import json
import sys
from pathlib import Path

OUT_DIR = Path("data/outputs/pdf_v2_probability_ch2")
REPORT_PATH = OUT_DIR / "pdf_v2_probability_ch2_report.json"

FORBIDDEN = ["静电场", "电磁场与电磁波", "高斯定理", "镜像法", "边界条件", "电位与电场", "电荷", "介质分界面"]
REQUIRED = ["概率论与随机过程", "第二章", "随机变量", "分布函数", "离散型随机变量", "连续型随机变量", "二项分布", "泊松分布", "正态分布"]

PDF_FILES = {
    "Sprint": OUT_DIR / "StudyPilot_v2_Probability_Ch2_Sprint.pdf",
    "Review": OUT_DIR / "StudyPilot_v2_Probability_Ch2_Review.pdf",
    "PastPaper": OUT_DIR / "StudyPilot_v2_Probability_Ch2_PastPaper.pdf",
    "MockExam": OUT_DIR / "StudyPilot_v2_Probability_Ch2_MockExam.pdf",
}

TYPST_FILES = {
    "Sprint": OUT_DIR / "StudyPilot_v2_Probability_Ch2_Sprint.typ",
    "Review": OUT_DIR / "StudyPilot_v2_Probability_Ch2_Review.typ",
    "PastPaper": OUT_DIR / "StudyPilot_v2_Probability_Ch2_PastPaper.typ",
    "MockExam": OUT_DIR / "StudyPilot_v2_Probability_Ch2_MockExam.typ",
}


def check_pdf_exists() -> dict:
    results = {}
    for name, path in PDF_FILES.items():
        results[name] = path.exists()
    return results


def check_forbidden_keywords() -> dict:
    hits = {}
    for name, path in TYPST_FILES.items():
        if not path.exists():
            hits[name] = ["FILE_NOT_FOUND"]
            continue
        content = path.read_text(encoding="utf-8")
        found = [kw for kw in FORBIDDEN if kw in content]
        hits[name] = found
    return hits


def check_required_keywords() -> dict:
    missing = {}
    for name, path in TYPST_FILES.items():
        if not path.exists():
            missing[name] = REQUIRED
            continue
        content = path.read_text(encoding="utf-8")
        not_found = [kw for kw in REQUIRED if kw not in content]
        missing[name] = not_found
    return missing


def check_mock_exam_questions() -> dict:
    """Verify MockExam has real questions with varied answers."""
    path = TYPST_FILES.get("MockExam")
    if not path or not path.exists():
        return {"mock_exam_exists": False, "error": "MockExam file not found"}

    content = path.read_text(encoding="utf-8")
    # Count question items
    choice_count = content.count("#question(")
    open_count = content.count("#open-question(")
    total_questions = choice_count + open_count

    # Check answer variety (not all A)
    answer_letters = []
    import re
    for match in re.finditer(r"(\d+)\.\s*([A-D])", content):
        answer_letters.append(match.group(2))

    all_same = len(set(answer_letters)) == 1 if answer_letters else False

    # Check for 100 points
    has_100 = "100" in content and ("分" in content or "总分" in content)

    # Check for standard answers section
    has_answers = "标准答案" in content or "答案" in content
    has_grading = "评分点" in content

    return {
        "mock_exam_exists": True,
        "total_questions": total_questions,
        "choice_questions": choice_count,
        "open_questions": open_count,
        "answer_letters_found": answer_letters[:10],
        "all_answers_same": all_same,
        "has_100_points": has_100,
        "has_standard_answers": has_answers,
        "has_grading_points": has_grading,
    }


def check_report() -> dict:
    if not REPORT_PATH.exists():
        return {"report_exists": False}
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    return {
        "report_exists": True,
        "probability_chapter2_pass": report.get("probability_chapter2_pass", False),
        "wrong_course_leak_count": report.get("wrong_course_leak_count", -1),
        "field_wave_leak_count": report.get("field_wave_leak_count", -1),
        "required_keyword_missing_count": report.get("required_keyword_missing_count", -1),
        "source_aligned_rate": report.get("source_aligned_rate", 0),
        "manual_acceptance_recommended": report.get("manual_acceptance_recommended", False),
    }


def main():
    print("=" * 60)
    print("概率论第二章 PDF 2.0 验收检查")
    print("=" * 60)

    # 1. PDF existence
    pdf_exists = check_pdf_exists()
    print("\n📄 PDF 文件存在性：")
    all_exist = True
    for name, exists in pdf_exists.items():
        status = "✅" if exists else "❌"
        if not exists:
            all_exist = False
        print(f"  {status} {name}: {PDF_FILES[name]}")

    # 2. Forbidden keywords
    forbidden = check_forbidden_keywords()
    print("\n🚫 禁止词检查：")
    total_forbidden = 0
    for name, hits in forbidden.items():
        if hits == ["FILE_NOT_FOUND"]:
            print(f"  ⚠️  {name}: Typst 文件不存在")
        elif hits:
            total_forbidden += len(hits)
            print(f"  ❌ {name}: 命中禁止词 {hits}")
        else:
            print(f"  ✅ {name}: 无禁止词")

    # 3. Required keywords
    required = check_required_keywords()
    print("\n✅ 必须词检查：")
    total_missing = 0
    for name, missing in required.items():
        if missing == REQUIRED:
            print(f"  ⚠️  {name}: Typst 文件不存在")
        elif missing:
            total_missing += len(missing)
            print(f"  ❌ {name}: 缺失 {missing}")
        else:
            print(f"  ✅ {name}: 全部必须词通过")

    # 4. MockExam quality
    mock = check_mock_exam_questions()
    print("\n📝 MockExam 质量：")
    for k, v in mock.items():
        print(f"  {k}: {v}")

    # 5. Report
    report = check_report()
    print("\n📊 报告检查：")
    for k, v in report.items():
        print(f"  {k}: {v}")

    # Summary
    print("\n" + "=" * 60)
    passed = (
        all_exist
        and total_forbidden == 0
        and total_missing == 0
        and mock.get("mock_exam_exists", False)
        and not mock.get("all_answers_same", True)
        and mock.get("has_100_points", False)
        and mock.get("has_standard_answers", False)
        and report.get("probability_chapter2_pass", False)
    )
    print(f"总体验收: {'✅ 通过' if passed else '❌ 未通过'}")
    print(f"  禁止词命中总数: {total_forbidden}")
    print(f"  必须词缺失总数: {total_missing}")
    print(f"  所有 PDF 存在: {all_exist}")
    print(f"  MockExam 合格: {mock.get('mock_exam_exists') and not mock.get('all_answers_same') and mock.get('has_100_points')}")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
