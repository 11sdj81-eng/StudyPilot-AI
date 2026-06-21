"""UnifiedQualityGate — single quality gate for ALL output types (PDF, Chat, Quiz, MockExam).

Reuses existing validators from pdf_content_v2. Adds cross-output consistency checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnifiedQualityReport:
    """Unified quality report across all output types."""
    course_id: str = ""
    release_level: str = "FAILED"  # RELEASE_READY / MANUAL_REVIEW / DRAFT / FAILED
    final_score: float = 0.0
    hard_gate_pass: bool = False
    manual_acceptance_recommended: bool = False
    issues: list[str] = field(default_factory=list)
    gate_details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id,
            "release_level": self.release_level,
            "final_score": self.final_score,
            "hard_gate_pass": self.hard_gate_pass,
            "manual_acceptance_recommended": self.manual_acceptance_recommended,
            "issues": self.issues,
            "gate_details": self.gate_details,
        }


class UnifiedQualityGate:
    """Single quality gate for all StudyPilot output types.

    Hard gates (must ALL pass for RELEASE_READY):
        course_contamination_count = 0
        option_answer_mismatch_count = 0
        fake_question_count = 0
        template_question_count = 0
        semantic_duplicate_count = 0
        missing_pdf_count = 0
        ai_content_ratio >= 0.60
        teacher_like_score >= 85
    """

    HARD_GATES = [
        ("course_contamination_count", 0, "跨课程污染 = 0", "eq"),
        ("legacy_renderer_usage_count", 0, "旧渲染器使用 = 0", "eq"),
        ("option_answer_mismatch_count", 0, "选项答案不匹配 = 0", "eq"),
        ("template_question_count", 0, "模板题 = 0", "eq"),
        ("fake_question_count", 0, "假题 = 0", "eq"),
        ("semantic_duplicate_count", 0, "语义重复 = 0", "eq"),
        ("missing_pdf_count", 0, "缺失PDF = 0", "eq"),
        ("ai_content_ratio", 0.60, "AI占比 ≥ 60%", "gte"),
        ("teacher_like_score", 85, "老师感 ≥ 85", "gte"),
    ]

    def __init__(self, core=None):
        self.core = core

    def check(self, summary: dict, course_id: str = "") -> UnifiedQualityReport:
        """Run all hard gates against a generation summary."""
        report = UnifiedQualityReport(course_id=course_id)
        gate_results = {}
        all_passed = True

        for key, threshold, label, op in self.HARD_GATES:
            value = summary.get(key, -1)

            # Handle -1 (unavailable) — treat as failure for zero-count gates
            if value == -1 and threshold == 0:
                gate_results[key] = {"value": value, "threshold": threshold,
                                     "passed": False, "label": label,
                                     "issue": f"{label}: 检测器不可用 (value=-1)"}
                all_passed = False
                report.issues.append(f"检测器不可用: {key}")
                continue

            if op == "eq":
                passed = value == threshold
            elif op == "gte":
                passed = value >= threshold
            else:
                passed = True

            gate_results[key] = {"value": value, "threshold": threshold,
                                "passed": passed, "label": label}
            if not passed:
                report.issues.append(f"{label}: 当前值={value}, 要求={threshold}")

        report.hard_gate_pass = all_passed
        report.gate_details = gate_results

        # Score
        total_gates = len(self.HARD_GATES)
        passed_gates = sum(1 for g in gate_results.values() if g["passed"])
        report.final_score = round(passed_gates / total_gates * 100, 1)

        # Release level
        if all_passed and report.final_score >= 95:
            report.release_level = "RELEASE_READY"
            report.manual_acceptance_recommended = True
        elif all_passed:
            report.release_level = "MANUAL_REVIEW"
            report.manual_acceptance_recommended = True
        elif report.final_score >= 60:
            report.release_level = "DRAFT"
        else:
            report.release_level = "FAILED"

        return report

    def check_outputs(self, outputs: dict, course_id: str = "") -> UnifiedQualityReport:
        """Check across all outputs for consistency."""
        report = UnifiedQualityReport(course_id=course_id)

        # Verify all PDF outputs exist
        missing = []
        for k, v in outputs.items():
            if isinstance(v, dict):
                pdf_path = v.get("pdf", "")
                if pdf_path:
                    from pathlib import Path
                    if not Path(pdf_path).exists():
                        missing.append(pdf_path)

        if missing:
            report.issues.append(f"Missing {len(missing)} PDF files")
            report.hard_gate_pass = False
            report.release_level = "FILE_MISSING"
        else:
            report.hard_gate_pass = True
            report.release_level = "MANUAL_REVIEW"

        return report
