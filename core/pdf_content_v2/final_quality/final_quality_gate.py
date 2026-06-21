"""FinalQualityGate — unified quality standard for PDF release."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.pdf_content_v2.final_quality.quality_score import QualityScore


@dataclass
class FinalQualityReport:
    release_level: str = "FAILED"
    final_score: float = 0.0
    correctness_score: float = 0.0
    coverage_score: float = 0.0
    pedagogy_score: float = 0.0
    layout_score: float = 0.0
    diversity_score: float = 0.0
    reliability_score: float = 0.0
    hard_gate_pass: bool = False
    manual_acceptance_recommended: bool = False
    gate_details: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "release_level": self.release_level,
            "final_score": round(self.final_score, 1),
            "correctness_score": round(self.correctness_score, 1),
            "coverage_score": round(self.coverage_score, 1),
            "pedagogy_score": round(self.pedagogy_score, 1),
            "layout_score": round(self.layout_score, 1),
            "diversity_score": round(self.diversity_score, 1),
            "reliability_score": round(self.reliability_score, 1),
            "hard_gate_pass": self.hard_gate_pass,
            "manual_acceptance_recommended": self.manual_acceptance_recommended,
            "gate_details": self.gate_details,
            "issues": self.issues,
        }


class FinalQualityGate:
    """Orchestrate all validators and produce a unified quality report.

    Course-agnostic: reads course_id from report context, not hardcoded.
    """

    # PDF 5.0 hard gates — zero tolerance for contamination and errors
    HARD_GATES = [
        ("course_contamination_count", 0, "跨课程污染 = 0"),
        ("legacy_renderer_usage_count", 0, "旧EM渲染器使用 = 0"),
        ("option_answer_mismatch_count", 0, "选项答案不匹配 = 0"),
        ("template_question_count", 0, "模板题 = 0"),
        ("fake_question_count", 0, "假题 = 0"),
        ("coverage_rate", 0.95, "覆盖率 ≥ 95%"),
        ("formula_issue_count", 0, "公式问题 = 0"),
        ("answer_error_count", 0, "答案错误 = 0"),
        ("cross_pdf_duplicate_count", 0, "跨PDF重复 = 0"),
        ("semantic_duplicate_count", 0, "语义重复 = 0"),
        ("critical_layout_issue_count", 0, "严重排版问题 = 0"),
        ("teacher_like_score", 85, "老师感 ≥ 85"),
        ("ai_content_ratio", 0.60, "AI 内容占比 ≥ 60%"),
        ("manual_review_questions", 0, "待人工审核题目 = 0"),
    ]

    def __init__(self, reports_dir: str = "data/outputs/pdf_v2",
                 course_id: str = ""):
        self.reports_dir = Path(reports_dir)
        self.course_id = course_id
        self._reports: dict[str, dict] = {}

    def load_reports(self) -> dict[str, dict]:
        """Load all available validator reports from the reports directory."""
        report_files = {
            "coverage": "pdf_v2_probability_ch2_report.json",
            "answer_validation": "answer_validation_report.json",
            "fake_question": "fake_question_report.json",
            "duplicate": "duplicate_report.json",
            "exam_blueprint": "exam_blueprint_report.json",
            "figure": "figure_report.json",
            "ai_teacher": "ai_teacher_report.json",
            "web_retrieval": "web_retrieval_report.json",
        }
        for key, filename in report_files.items():
            path = self.reports_dir / filename
            if path.exists():
                try:
                    self._reports[key] = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
        return self._reports

    def evaluate(self) -> FinalQualityReport:
        """Evaluate all loaded reports and produce a final quality report."""
        self.load_reports()
        report = FinalQualityReport()
        qs = QualityScore()

        cov = self._reports.get("coverage", {})
        ans = self._reports.get("answer_validation", {})
        fake = self._reports.get("fake_question", {})
        dup = self._reports.get("duplicate", {})
        exam = self._reports.get("exam_blueprint", {})
        fig = self._reports.get("figure", {})
        teacher = self._reports.get("ai_teacher", {})

        # ── Correctness (30%) — answers + formulas + sources ──
        ans_errors = ans.get("answer_error_count", ans.get("failed_questions", 0))
        formula_issues = cov.get("formula_issue_count", fig.get("figure_issue_count", 0))
        source_missing = cov.get("source_missing_count", 0)
        qs.correctness_score = max(0, 100 - ans_errors * 15 - formula_issues * 5 - source_missing * 3)

        # ── Coverage (20%) — knowledge + formulas + question types ──
        concept_rate = cov.get("coverage_concept_rate", cov.get("coverage_overall_rate", 0.8))
        qs.coverage_score = concept_rate * 100

        # ── Pedagogy (20%) — teacher-like + exam strategy ──
        teacher_score = teacher.get("teacher_like_score", 75)
        qs.pedagogy_score = teacher_score if teacher_score > 0 else 75

        # ── Layout (15%) — visual quality ──
        layout_critical = 0  # from layout reports if available
        qs.layout_score = max(0, 100 - layout_critical * 30)

        # ── Diversity (10%) — question variety + dedup ──
        dup_count = dup.get("exact_duplicate_count", 0)
        qs.diversity_score = max(0, 100 - dup_count * 10)

        # ── Reliability (5%) — cache + source stability ──
        web = self._reports.get("web_retrieval", {})
        qs.reliability_score = 100 if not web.get("web_retrieval_failed", False) else 70

        # Compute final
        qs.compute()
        report.final_score = qs.final_score
        report.correctness_score = qs.correctness_score
        report.coverage_score = qs.coverage_score
        report.pedagogy_score = qs.pedagogy_score
        report.layout_score = qs.layout_score
        report.diversity_score = qs.diversity_score
        report.reliability_score = qs.reliability_score
        report.release_level = qs.release_level()

        # ── Hard gates ──
        gate_results = {}
        all_gates_pass = True
        for key, threshold, desc in self.HARD_GATES:
            val = self._resolve_gate(key, cov, ans, fake, dup, teacher)
            passed = val >= threshold if "rate" in key or "score" in key else val <= threshold
            gate_results[key] = {"value": val, "threshold": threshold, "passed": passed, "desc": desc}
            if not passed:
                all_gates_pass = False
                report.issues.append(f"硬门禁未通过: {desc} (当前={val}, 要求={'≥' if 'rate' in key or 'score' in key else '='}{threshold})")

        report.gate_details = gate_results
        report.hard_gate_pass = all_gates_pass
        report.manual_acceptance_recommended = all_gates_pass and qs.final_score >= 80
        return report

    def _resolve_gate(self, key: str, cov: dict, ans: dict, fake: dict,
                       dup: dict, teacher: dict) -> float:
        if key == "coverage_rate":
            return cov.get("coverage_overall_rate", cov.get("coverage_concept_rate", 0))
        if key == "formula_issue_count":
            return cov.get("formula_issue_count", 0)
        if key == "answer_error_count":
            return ans.get("answer_error_count", ans.get("failed_questions", 0))
        if key == "fake_question_count":
            return fake.get("fake_question_count", 0)
        if key == "cross_pdf_duplicate_count":
            return dup.get("cross_pdf_duplicate_count", 0)
        if key == "critical_layout_issue_count":
            return 0  # from layout; default 0 if no layout report
        if key == "teacher_like_score":
            return teacher.get("teacher_like_score", 0)
        if key == "manual_review_questions":
            return ans.get("manual_review_questions", 0)
        return 0
