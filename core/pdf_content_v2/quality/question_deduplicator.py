"""Detect duplicate and near-duplicate questions within and across PDFs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DedupResult:
    passed: bool = False
    duplicate_question_count: int = 0
    near_duplicate_question_count: int = 0
    cross_pdf_duplicate_count: int = 0
    duplicate_pairs: list[dict] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "duplicate_question_count": self.duplicate_question_count,
            "near_duplicate_question_count": self.near_duplicate_question_count,
            "cross_pdf_duplicate_count": self.cross_pdf_duplicate_count,
            "duplicate_pairs": self.duplicate_pairs,
            "checks": self.checks,
        }


class QuestionDeduplicator:
    """Detect duplicate questions by comparing normalized stems."""

    def check_all(self, typst_files: dict[str, Path]) -> DedupResult:
        """Check all four typst files for duplicates within and across PDFs."""
        result = DedupResult()
        all_questions: list[dict] = []

        for name, path in typst_files.items():
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            stems = self._extract_stems(content)
            for stem in stems:
                all_questions.append({"pdf": name, "stem": stem, "norm": self._normalize(stem)})

        # Check exact duplicates
        seen_norms: dict[str, list[dict]] = {}
        for q in all_questions:
            seen_norms.setdefault(q["norm"], []).append(q)

        for norm, questions in seen_norms.items():
            if len(questions) > 1:
                pdfs = {q["pdf"] for q in questions}
                if len(pdfs) > 1:
                    result.cross_pdf_duplicate_count += 1
                    result.duplicate_pairs.append({
                        "type": "cross_pdf_exact", "pdfs": list(pdfs), "stem_preview": questions[0]["stem"][:80],
                    })
                else:
                    result.duplicate_question_count += 1
                    result.duplicate_pairs.append({
                        "type": "within_pdf_exact", "pdf": questions[0]["pdf"], "stem_preview": questions[0]["stem"][:80],
                    })

        # Check near-duplicates (same numbers, same structure but different wording)
        near_dupes = self._find_near_duplicates(all_questions)
        result.near_duplicate_question_count = len(near_dupes)
        result.duplicate_pairs.extend(near_dupes)

        result.passed = (
            result.duplicate_question_count == 0
            and result.cross_pdf_duplicate_count == 0
            and result.near_duplicate_question_count <= 2  # allow minor near-dupes
        )
        result.checks = {
            "total_questions": len(all_questions),
            "unique_norms": len(seen_norms),
            "pdf_question_counts": {name: sum(1 for q in all_questions if q["pdf"] == name) for name in set(q["pdf"] for q in all_questions)},
        }
        return result

    def _extract_stems(self, content: str) -> list[str]:
        """Extract question stems from typst content."""
        stems = []
        # #question or #open-question patterns
        for m in re.finditer(r'#(?:question|open-question)\("([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]+)"', content):
            stem = m.group(4)
            if len(stem) > 10:
                stems.append(stem)
        # Also catch block-title followed by problem description
        for m in re.finditer(r'#strong\[题目\]：(.+?)(?:\n|$)', content):
            stems.append(m.group(1).strip())
        return stems

    def _normalize(self, text: str) -> str:
        """Normalize question text for comparison."""
        t = text.lower().strip()
        t = re.sub(r'[0-9]+', 'N', t)  # replace numbers
        t = re.sub(r'[a-zA-Z]+', 'X', t)  # replace latin words
        return t.strip()

    def _find_near_duplicates(self, questions: list[dict]) -> list[dict]:
        """Find questions that are structurally identical (same numbers, same pattern)."""
        near_dupes = []
        for i, q1 in enumerate(questions):
            for j, q2 in enumerate(questions):
                if j <= i:
                    continue
                # Same normalized structure but different PDFs is the main concern
                if q1["norm"] == q2["norm"]:
                    continue  # already caught as exact
                if q1["pdf"] != q2["pdf"] and self._structural_similar(q1["stem"], q2["stem"]):
                    near_dupes.append({
                        "type": "cross_pdf_near", "pdfs": [q1["pdf"], q2["pdf"]],
                        "stem1": q1["stem"][:60], "stem2": q2["stem"][:60],
                    })
        return near_dupes

    def _structural_similar(self, s1: str, s2: str) -> bool:
        """Check if two questions have the same structure with different data."""
        # Replace numbers
        r1 = re.sub(r'\d+\.?\d*', '#', s1)
        r2 = re.sub(r'\d+\.?\d*', '#', s2)
        # Compare after removing numbers — only flag if highly similar
        words1 = set(re.findall(r'[一-鿿]{2,}', r1))
        words2 = set(re.findall(r'[一-鿿]{2,}', r2))
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / min(len(words1), len(words2))
        return overlap > 0.92
