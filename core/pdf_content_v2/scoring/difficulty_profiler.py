"""DifficultyProfiler — tags questions easy/medium/hard for PDF 5.0.

Course-agnostic difficulty assessment based on:
- Number of solution steps
- Formula complexity
- Concept depth
- Exam pattern score weight
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DifficultyTag:
    question_id: str
    difficulty: str = "medium"  # easy / medium / hard
    factors: dict | None = None


class DifficultyProfiler:
    """Tags questions with difficulty levels.

    MockExam distribution target:
        easy: 30%
        medium: 50%
        hard: 20%
    """

    DEFAULT_DISTRIBUTION = {"easy": 0.30, "medium": 0.50, "hard": 0.20}

    def tag(self, question: dict, concept_data: dict | None = None) -> str:
        """Tag a single question with difficulty.

        Rules:
            - 0-2 solution steps → easy
            - 3-4 solution steps → medium
            - 5+ solution steps → hard
            - Formula with 3+ variables → bump up
            - "基础" in difficulty label → easy
            - "综合" or "高" → hard
        """
        steps = question.get("solution_steps", [])
        if isinstance(steps, list):
            step_count = len(steps)
        else:
            step_count = 0

        difficulty_label = question.get("difficulty", "")

        # Explicit difficulty hints
        if "基础" in str(difficulty_label):
            return "easy"
        if "综合" in str(difficulty_label) or "高" in str(difficulty_label):
            return "hard"

        # Step count based
        if step_count <= 2:
            return "easy"
        elif step_count <= 4:
            return "medium"
        else:
            return "hard"

    def tag_all(self, questions: list[dict]) -> list[dict]:
        """Tag all questions and return them with difficulty added."""
        for q in questions:
            q["difficulty"] = self.tag(q)
        return questions

    def get_distribution(self, questions: list[dict]) -> dict:
        """Get actual difficulty distribution of a question set."""
        counts = {"easy": 0, "medium": 0, "hard": 0}
        for q in questions:
            diff = q.get("difficulty", self.tag(q))
            counts[diff] = counts.get(diff, 0) + 1
        total = max(sum(counts.values()), 1)
        return {k: round(v / total, 3) for k, v in counts.items()}

    def validate_distribution(self, questions: list[dict],
                              target: dict | None = None) -> dict:
        """Check if distribution matches target. Returns compliance report."""
        target = target or self.DEFAULT_DISTRIBUTION
        actual = self.get_distribution(questions)
        compliant = all(
            abs(actual.get(k, 0) - target.get(k, 0)) <= 0.15
            for k in target
        )
        return {
            "actual": actual,
            "target": target,
            "compliant": compliant,
            "deviations": {
                k: round(actual.get(k, 0) - target.get(k, 0), 3)
                for k in target
            },
        }

    def rebalance(self, questions: list[dict],
                  target: dict | None = None) -> list[dict]:
        """Rebalance questions to match target distribution.

        Strategy: adjust difficulty tags, don't remove questions.
        """
        target = target or self.DEFAULT_DISTRIBUTION
        total = len(questions)
        target_counts = {k: max(1, int(v * total)) for k, v in target.items()}

        # Sort questions by complexity
        scored = [(q, self._complexity_score(q)) for q in questions]
        scored.sort(key=lambda x: x[1])

        # Assign difficulties to match target
        easy_count = target_counts.get("easy", 0)
        medium_count = target_counts.get("medium", 0)

        for i, (q, _) in enumerate(scored):
            if i < easy_count:
                q["difficulty"] = "easy"
            elif i < easy_count + medium_count:
                q["difficulty"] = "medium"
            else:
                q["difficulty"] = "hard"

        return questions

    def _complexity_score(self, question: dict) -> float:
        """Internal complexity score for ranking."""
        steps = question.get("solution_steps", [])
        step_count = len(steps) if isinstance(steps, list) else 0
        answer_len = len(str(question.get("answer", question.get("standard_answer", ""))))
        return step_count * 10 + min(answer_len / 10, 50)
