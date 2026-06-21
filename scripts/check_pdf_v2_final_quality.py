#!/usr/bin/env python3
"""Comprehensive PDF 2.2 quality verification script."""

import json
import re
import sys
from pathlib import Path

OUT_DIR = Path("data/outputs/pdf_v2_probability_ch2")
REPORT_PATH = OUT_DIR / "pdf_v2_probability_ch2_report.json"

FORBIDDEN = ["静电场", "电磁场与电磁波", "高斯定理", "镜像法", "边界条件", "电位与电场", "电荷", "介质分界面"]
REQUIRED = ["概率论与随机过程", "第二章", "随机变量", "分布函数", "离散型随机变量", "连续型随机变量", "二项分布", "泊松分布", "正态分布"]

TYPST_FILES = {
    "Sprint": OUT_DIR / "StudyPilot_v2_Probability_Ch2_Sprint.typ",
    "Review": OUT_DIR / "StudyPilot_v2_Probability_Ch2_Review.typ",
    "PastPaper": OUT_DIR / "StudyPilot_v2_Probability_Ch2_PastPaper.typ",
    "MockExam": OUT_DIR / "StudyPilot_v2_Probability_Ch2_MockExam.typ",
}


def check_all() -> dict:
    results = {"checks": {}, "pass": True, "issues": []}

    # 1. PDF existence
    pdf_ok = True
    for name in ["Sprint", "Review", "PastPaper", "MockExam"]:
        pdf = OUT_DIR / f"StudyPilot_v2_Probability_Ch2_{name}.pdf"
        typ = OUT_DIR / f"StudyPilot_v2_Probability_Ch2_{name}.typ"
        results["checks"][f"{name}_pdf"] = pdf.exists()
        results["checks"][f"{name}_typ"] = typ.exists()
        if not pdf.exists():
            results["issues"].append(f"{name} PDF 缺失")
            pdf_ok = False
    results["checks"]["all_pdfs_exist"] = pdf_ok

    # 2. Forbidden keywords
    all_content = ""
    for name, path in TYPST_FILES.items():
        if path.exists():
            all_content += path.read_text(encoding="utf-8")
    forbidden_hits = []
    for kw in FORBIDDEN:
        if kw in all_content:
            forbidden_hits.append(kw)
    results["checks"]["forbidden_hits"] = forbidden_hits
    results["checks"]["forbidden_pass"] = len(forbidden_hits) == 0

    # 3. Required keywords
    missing_required = []
    for kw in REQUIRED:
        if kw not in all_content:
            missing_required.append(kw)
    results["checks"]["missing_required"] = missing_required
    results["checks"]["required_pass"] = len(missing_required) == 0

    # 4. MockExam quality
    mock_path = TYPST_FILES.get("MockExam")
    if mock_path and mock_path.exists():
        mock_text = mock_path.read_text(encoding="utf-8")
        # Answer variety
        answers = re.findall(r'(\d+)\.\s*([A-D])', mock_text)
        letters = [l for _, l in answers]
        all_same = len(set(letters)) == 1 if letters else True
        results["checks"]["mock_answer_letters"] = letters[:10]
        results["checks"]["mock_all_same"] = all_same
        # Score
        has_100 = "100" in mock_text and "分" in mock_text
        results["checks"]["mock_has_100"] = has_100
        # Fake questions
        fake_hits = []
        for fp in ["请填写一个高频公式", "请列举", "请简述"]:
            if fp in mock_text:
                fake_hits.append(fp)
        results["checks"]["mock_fake_questions"] = fake_hits
        # Question count
        choice_count = mock_text.count("#question(")
        open_count = mock_text.count("#open-question(")
        results["checks"]["mock_choice_count"] = choice_count
        results["checks"]["mock_open_count"] = open_count
        results["checks"]["mock_pass"] = not all_same and has_100 and len(fake_hits) == 0 and choice_count >= 4

    # 5. Report
    if REPORT_PATH.exists():
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        for key in ["answer_error_count", "duplicate_question_count", "cross_pdf_duplicate_count",
                     "fake_question_count", "field_wave_leak_count", "exam_blueprint_match"]:
            results["checks"][f"report_{key}"] = report.get(key, -1)
        results["checks"]["report_manual_accept"] = report.get("manual_acceptance_recommended", False)

    # 6. Overall pass
    results["pass"] = (
        results["checks"].get("all_pdfs_exist", False)
        and results["checks"].get("forbidden_pass", False)
        and results["checks"].get("required_pass", False)
        and results["checks"].get("mock_pass", False)
    )
    return results


def main():
    print("=" * 60)
    print("PDF 2.2 最终质量检查")
    print("=" * 60)
    results = check_all()
    for k, v in results["checks"].items():
        icon = "✅" if v else "❌" if isinstance(v, bool) else ""
        print(f"  {icon} {k}: {v}")
    print(f"\n问题: {results['issues'] if results['issues'] else '无'}")
    print(f"总体: {'✅ 通过' if results['pass'] else '❌ 未通过'}")
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
