"""SemanticDeduplicator — semantic-aware question deduplication for PDF 5.0.

Extends QuestionDeduplicator with concept-overlap and formula-fingerprint
based similarity detection. Cross-PDF dedup rules:
  - Review keeps detailed explanation
  - Sprint keeps compressed version
  - PastPaper keeps exam analysis
  - MockExam keeps only Q&A
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SemanticDeduplicateReport:
    """Result of semantic deduplication across PDFs."""
    total_questions: int = 0
    duplicate_pairs: list[dict] = field(default_factory=list)
    semantic_duplicate_count: int = 0
    resolved_count: int = 0
    kept_in: dict[str, list[str]] = field(default_factory=dict)  # pdf_type -> [q_ids]
    removed_from: dict[str, list[str]] = field(default_factory=dict)
    diversity_score: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict:
        return {
            "total_questions": self.total_questions,
            "duplicate_pairs": self.duplicate_pairs,
            "semantic_duplicate_count": self.semantic_duplicate_count,
            "resolved_count": self.resolved_count,
            "kept_in": self.kept_in,
            "removed_from": self.removed_from,
            "diversity_score": self.diversity_score,
            "passed": self.passed,
        }


class SemanticDeduplicator:
    """Detects semantically similar questions across PDF types.

    Uses concept overlap + formula fingerprint + key phrase matching
    to identify semantic duplicates beyond exact text matching.

    Resolution strategy:
        If same concept+formula appears in multiple PDFs:
        - Review: KEEP full explanation
        - PastPaper: KEEP exam analysis
        - Sprint: KEEP compressed version only if not in Review
        - MockExam: KEEP Q&A format
    """

    # PDF priority for keeping duplicates (higher = preferred to keep)
    PDF_KEEP_PRIORITY = {
        "Review": 4,       # Most detailed — keep
        "PastPaper": 3,    # Exam-specific — keep
        "Sprint": 2,       # Compressed — keep only if no Review/PastPaper
        "MockExam": 1,     # Q&A only — keep only if unique
    }

    def __init__(self, similarity_threshold: float = 0.70):
        self.threshold = similarity_threshold

    def check_all(self, typst_files: dict[str, Path],
                  questions_by_pdf: dict[str, list[dict]] | None = None) -> SemanticDeduplicateReport:
        """Check all PDFs for semantic duplicates.

        Args:
            typst_files: Dict of pdf_type -> Path to typst file
            questions_by_pdf: Optional pre-extracted questions by pdf_type

        Returns:
            SemanticDeduplicateReport
        """
        report = SemanticDeduplicateReport()

        # Extract questions if not provided
        if questions_by_pdf is None:
            questions_by_pdf = {}
            for pdf_type, path in typst_files.items():
                if path.exists():
                    questions_by_pdf[pdf_type] = self._extract_questions(
                        path.read_text(encoding="utf-8")
                    )

        # Flatten and fingerprint
        all_questions = []
        for pdf_type, questions in questions_by_pdf.items():
            for q in questions:
                q["_pdf_type"] = pdf_type
                q["_fingerprint"] = self._fingerprint(q)
                all_questions.append(q)

        report.total_questions = len(all_questions)

        # Find semantic duplicates across PDFs
        dup_pairs = []
        for i in range(len(all_questions)):
            for j in range(i + 1, len(all_questions)):
                qi, qj = all_questions[i], all_questions[j]
                # Skip same PDF
                if qi["_pdf_type"] == qj["_pdf_type"]:
                    continue
                sim = self._semantic_similarity(qi, qj)
                if sim >= self.threshold:
                    dup_pairs.append({
                        "q1_pdf": qi["_pdf_type"],
                        "q1_id": qi.get("id", ""),
                        "q2_pdf": qj["_pdf_type"],
                        "q2_id": qj.get("id", ""),
                        "similarity": round(sim, 4),
                        "reason": self._duplicate_reason(qi, qj),
                    })

        report.duplicate_pairs = dup_pairs
        report.semantic_duplicate_count = len(dup_pairs)

        # Resolve duplicates using priority rules
        resolved = self._resolve_duplicates(dup_pairs)
        report.resolved_count = resolved["resolved"]
        report.kept_in = resolved["kept"]
        report.removed_from = resolved["removed"]

        # Diversity score
        unique_fingerprints = len(set(q["_fingerprint"] for q in all_questions))
        report.diversity_score = round(unique_fingerprints / max(report.total_questions, 1), 4)
        report.passed = report.semantic_duplicate_count == 0

        return report

    def _extract_questions(self, text: str) -> list[dict]:
        """Extract question dicts from typst text."""
        questions = []
        # Find question blocks
        blocks = re.split(r'#(?:question|open-question)\[', text)
        for block in blocks[1:]:  # skip preamble
            # Extract fields
            stem_match = re.search(r'"([^"]*)"', block)
            qtype_match = re.search(r'"([^"]*)"', block)
            if stem_match:
                questions.append({
                    "stem": stem_match.group(1)[:100],
                    "type": "unknown",
                    "_raw": block[:200],
                })
        return questions

    def _fingerprint(self, question: dict) -> str:
        """Create a semantic fingerprint from question content."""
        stem = question.get("stem", question.get("problem", ""))
        answer = question.get("answer", question.get("standard_answer", ""))

        # Extract key features
        concepts = self._extract_concepts_from_text(stem)
        formulas = self._extract_formulas_from_text(stem + answer)
        qtype = question.get("type", question.get("question_type", ""))

        # Build fingerprint
        parts = [
            qtype[:20],
            "|".join(sorted(concepts)[:3]),
            "|".join(sorted(formulas)[:3]),
        ]
        return "::".join(parts)

    def _semantic_similarity(self, q1: dict, q2: dict) -> float:
        """Compute semantic similarity between two questions."""
        fp1, fp2 = q1["_fingerprint"], q2["_fingerprint"]

        # Quick exact match
        if fp1 == fp2:
            return 1.0

        parts1, parts2 = fp1.split("::"), fp2.split("::")
        scores = []

        # Type similarity
        if parts1[0] and parts2[0] and parts1[0] == parts2[0]:
            scores.append(1.0)
        else:
            scores.append(0.0)

        # Concept overlap
        concepts1 = set(parts1[1].split("|")) if parts1[1] else set()
        concepts2 = set(parts2[1].split("|")) if parts2[1] else set()
        if concepts1 or concepts2:
            overlap = len(concepts1 & concepts2) / max(len(concepts1 | concepts2), 1)
            scores.append(overlap)
        else:
            scores.append(0.0)

        # Formula overlap
        formulas1 = set(parts1[2].split("|")) if len(parts1) > 2 and parts1[2] else set()
        formulas2 = set(parts2[2].split("|")) if len(parts2) > 2 and parts2[2] else set()
        if formulas1 or formulas2:
            overlap = len(formulas1 & formulas2) / max(len(formulas1 | formulas2), 1)
            scores.append(overlap)
        else:
            scores.append(0.0)

        # Weighted average
        weights = [0.2, 0.5, 0.3]
        return sum(s * w for s, w in zip(scores, weights))

    def _extract_concepts_from_text(self, text: str) -> list[str]:
        """Extract concept keywords from question text."""
        # Look for concept identifiers in brackets or common patterns
        concepts = []
        # Match [concept_id] patterns
        bracket_matches = re.findall(r'\[([a-z_]+)\]', text)
        concepts.extend(bracket_matches)
        # Match common Chinese concept keywords
        cn_matches = re.findall(r'[分布函数|随机变量|高斯|静电场|逻辑|卡诺图|触发器]{2,6}', text)
        concepts.extend(cn_matches)
        return concepts[:5]

    def _extract_formulas_from_text(self, text: str) -> list[str]:
        """Extract formula signatures from text."""
        formulas = []
        # Match LaTeX-like patterns
        latex_matches = re.findall(r'\$[^$]+\$', text)
        for m in latex_matches[:5]:
            # Normalize whitespace
            normalized = re.sub(r'\s+', ' ', m)
            formulas.append(normalized[:30])
        return formulas

    def _duplicate_reason(self, q1: dict, q2: dict) -> str:
        """Explain why two questions are considered duplicates."""
        reasons = []
        if q1["_fingerprint"] == q2["_fingerprint"]:
            reasons.append("exact fingerprint match")
        fp1_parts = q1["_fingerprint"].split("::")
        fp2_parts = q2["_fingerprint"].split("::")
        if fp1_parts[0] == fp2_parts[0]:
            reasons.append("same question type")
        if len(fp1_parts) > 1 and len(fp2_parts) > 1:
            c1 = set(fp1_parts[1].split("|"))
            c2 = set(fp2_parts[1].split("|"))
            overlap = c1 & c2
            if overlap:
                reasons.append(f"concept overlap: {', '.join(overlap)}")
        return "; ".join(reasons) if reasons else "unknown"

    def _resolve_duplicates(self, dup_pairs: list[dict]) -> dict:
        """Apply resolution strategy to duplicates."""
        kept: dict[str, list[str]] = defaultdict(list)
        removed: dict[str, list[str]] = defaultdict(list)
        resolved = 0

        for pair in dup_pairs:
            pdf1, pdf2 = pair["q1_pdf"], pair["q2_pdf"]
            priority1 = self.PDF_KEEP_PRIORITY.get(pdf1, 0)
            priority2 = self.PDF_KEEP_PRIORITY.get(pdf2, 0)

            if priority1 >= priority2:
                kept[pdf1].append(pair["q1_id"])
                removed[pdf2].append(pair["q2_id"])
            else:
                kept[pdf2].append(pair["q2_id"])
                removed[pdf1].append(pair["q1_id"])
            resolved += 1

        return {
            "resolved": resolved,
            "kept": dict(kept),
            "removed": dict(removed),
        }
