"""WrongQuestionMemory — records wrong answers and auto-decreases mastery.

Each wrong question is stored with:
- id, question, error_concept, user_answer, correct_answer, timestamp

Integration: record_wrong() also calls MasteryTracker.record_answer(is_correct=False).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WrongQuestionMemory:
    """Records wrong answers and provides recurring mistake analysis.

    Persistence: data/wrong_questions.json
    Auto-updates: MasteryTracker on each record_wrong() call.
    """

    def __init__(self, data_path: str = "data/wrong_questions.json"):
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

    def record_wrong(
        self,
        course_id: str,
        question: str,
        error_concept: str,
        user_answer: str | None = None,
        correct_answer: str | None = None,
    ) -> str:
        """Record a wrong question. Returns the question ID.

        Also auto-decreases mastery for the error_concept via MasteryTracker.
        """
        if not course_id or not error_concept:
            return ""
        error_concept = error_concept.strip()
        question = question.strip()[:500]

        # Generate unique ID
        qid = f"wq_{uuid.uuid4().hex[:8]}"

        record = {
            "id": qid,
            "question": question,
            "error_concept": error_concept,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        course_records = self._data.setdefault(course_id, [])
        course_records.insert(0, record)  # Most recent first
        self._save()

        # Auto-decrease mastery
        try:
            from core.mastery_tracker import get_mastery_tracker
            get_mastery_tracker().record_answer(course_id, error_concept, is_correct=False)
        except Exception:
            pass

        return qid

    def get_wrong_history(self, course_id: str, concept: str | None = None) -> list[dict]:
        """Get wrong questions for a course, optionally filtered by concept.

        Returns list sorted by timestamp descending (most recent first).
        """
        records = self._data.get(course_id, [])
        if concept:
            records = [r for r in records if r.get("error_concept") == concept]
        return sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)

    def get_recurring_mistakes(self, course_id: str, min_occurrences: int = 2) -> list[dict]:
        """Get concepts that appear in multiple wrong questions.

        Returns list of {"concept": str, "count": int, "latest_question": str}
        sorted by count descending.
        """
        records = self._data.get(course_id, [])
        concept_counts: dict[str, int] = {}
        concept_latest: dict[str, str] = {}
        for r in records:
            concept = r.get("error_concept", "")
            if not concept:
                continue
            concept_counts[concept] = concept_counts.get(concept, 0) + 1
            if concept not in concept_latest:
                concept_latest[concept] = r.get("question", "")
        result = [
            {
                "concept": c,
                "count": cnt,
                "latest_question": concept_latest.get(c, ""),
            }
            for c, cnt in concept_counts.items()
            if cnt >= min_occurrences
        ]
        return sorted(result, key=lambda x: x["count"], reverse=True)

    def get_error_count(self, course_id: str, concept: str | None = None) -> int:
        """Count wrong questions for a course. Optional concept filter."""
        records = self._data.get(course_id, [])
        if concept:
            records = [r for r in records if r.get("error_concept") == concept]
        return len(records)

    def get_stats(self, course_id: str) -> dict:
        """Return summary stats for a course."""
        records = self._data.get(course_id, [])
        recurring = self.get_recurring_mistakes(course_id, min_occurrences=2)
        # Count unique error concepts
        error_concepts = set(r.get("error_concept", "") for r in records)
        error_concepts.discard("")
        return {
            "course_id": course_id,
            "total_wrong": len(records),
            "unique_error_concepts": len(error_concepts),
            "recurring_mistakes": recurring,
        }

    def clear_history(self, course_id: str) -> None:
        """Clear all wrong questions for a course."""
        if course_id in self._data:
            del self._data[course_id]
            self._save()


# ── Singleton ──────────────────────────────────────────────────────

_memory: WrongQuestionMemory | None = None


def get_wrong_memory() -> WrongQuestionMemory:
    global _memory
    if _memory is None:
        _memory = WrongQuestionMemory()
    return _memory
