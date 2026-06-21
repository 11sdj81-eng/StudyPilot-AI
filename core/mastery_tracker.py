"""MasteryTracker — per-concept mastery scoring for personalized learning.

Tracks correct/wrong counts per course per concept.
Drives quiz/mock_exam/summary priority based on mastery scores.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MasteryTracker:
    """Tracks student mastery of concepts across courses.

    Mastery formula:
        mastery = correct / max(correct + wrong, 1) * 100
        Untested concepts start at 50.0 (neutral).
        Clamped to [0, 100].

    Persistence: data/mastery.json
    """

    def __init__(self, data_path: str = "data/mastery.json"):
        self.data_path = Path(data_path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.data_path.exists():
            try:
                return json.loads(self.data_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def _save(self) -> None:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Core API ──────────────────────────────────────────────────────

    def record_answer(self, course_id: str, concept: str, is_correct: bool) -> None:
        """Record a correct or wrong answer for a concept."""
        if not course_id or not concept or not concept.strip():
            return
        concept = concept.strip()
        course_data = self._data.setdefault(course_id, {})
        entry = course_data.get(concept)
        if entry is None:
            entry = {"correct": 0, "wrong": 0}
            course_data[concept] = entry
        if is_correct:
            entry["correct"] = entry.get("correct", 0) + 1
        else:
            entry["wrong"] = entry.get("wrong", 0) + 1
        entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def get_mastery(self, course_id: str, concept: str) -> float:
        """Return mastery score 0-100 for a concept.

        Untested concepts return 50.0 (neutral starting point).
        """
        if not course_id or not concept:
            return 50.0
        concept = concept.strip()
        entry = (self._data.get(course_id, {}).get(concept))
        if entry is None:
            return 50.0
        correct = entry.get("correct", 0)
        wrong = entry.get("wrong", 0)
        total = correct + wrong
        if total == 0:
            return 50.0
        score = correct / total * 100.0
        return max(0.0, min(100.0, score))

    def get_all_mastery(self, course_id: str) -> dict[str, float]:
        """Return dict of concept_name -> mastery_score for a course."""
        result = {}
        for concept, entry in self._data.get(course_id, {}).items():
            correct = entry.get("correct", 0)
            wrong = entry.get("wrong", 0)
            total = correct + wrong
            if total == 0:
                result[concept] = 50.0
            else:
                result[concept] = max(0.0, min(100.0, correct / total * 100.0))
        return result

    def get_weakest_concepts(self, course_id: str, n: int = 5) -> list[tuple[str, float]]:
        """Return n concepts with lowest mastery, sorted ascending.

        Only returns concepts that have been tested at least once.
        If fewer than n concepts tested, returns all tested ones.
        """
        all_mastery = self.get_all_mastery(course_id)
        # Filter: only concepts that have been tested (correct+wrong > 0)
        tested = {}
        for concept, entry in self._data.get(course_id, {}).items():
            if entry.get("correct", 0) + entry.get("wrong", 0) > 0:
                tested[concept] = all_mastery.get(concept, 50.0)
        # Sort by mastery ascending
        sorted_concepts = sorted(tested.items(), key=lambda x: x[1])
        return sorted_concepts[:n]

    def update_mastery_from_quiz(self, course_id: str, quiz_results: list[dict]) -> None:
        """Batch update mastery from quiz results.

        quiz_results: list of {"concept": str, "is_correct": bool}
        """
        for r in quiz_results:
            concept = r.get("concept", "")
            is_correct = r.get("is_correct", False)
            if concept:
                self.record_answer(course_id, concept, is_correct)

    def get_stats(self, course_id: str) -> dict:
        """Return summary stats for a course."""
        all_m = self.get_all_mastery(course_id)
        if not all_m:
            return {
                "course_id": course_id,
                "total_concepts": 0,
                "tested_concepts": 0,
                "avg_mastery": 50.0,
                "min_mastery": 50.0,
                "max_mastery": 50.0,
                "weakest": [],
            }
        values = list(all_m.values())
        weakest = self.get_weakest_concepts(course_id, n=3)
        return {
            "course_id": course_id,
            "total_concepts": len(all_m),
            "tested_concepts": sum(
                1
                for c, e in self._data.get(course_id, {}).items()
                if e.get("correct", 0) + e.get("wrong", 0) > 0
            ),
            "avg_mastery": round(sum(values) / len(values), 1),
            "min_mastery": round(min(values), 1),
            "max_mastery": round(max(values), 1),
            "weakest": [{"concept": c, "mastery": m} for c, m in weakest],
        }


# ── Singleton ──────────────────────────────────────────────────────

_tracker: MasteryTracker | None = None


def get_mastery_tracker() -> MasteryTracker:
    global _tracker
    if _tracker is None:
        _tracker = MasteryTracker()
    return _tracker
