"""ProfileBuilder — build BaseCourseProfile from seed data or auto-extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.course_profiles.base_profile import BaseCourseProfile, ProfileSource
from core.course_profiles.generic_course_profile import GenericCourseProfile


class ProfileBuilder:
    """Build a BaseCourseProfile from the best available source."""

    def __init__(self):
        self.generic = GenericCourseProfile()

    def build_from_seed(self, seed_dir: str | Path) -> BaseCourseProfile | None:
        """Build from golden_chapters seed data."""
        base = Path(seed_dir)
        concepts_path = base / "concepts.json"
        if not concepts_path.exists():
            return None

        try:
            concepts = json.loads(concepts_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return None

        # Extract course name from first concept's chapter field
        chapter_hint = ""
        for c in concepts:
            chapter_hint = c.get("chapter", "")
            if chapter_hint:
                break

        # Infer course name from chapter prefix
        course_name = self._infer_course_name(chapter_hint, str(base))

        concept_names = [c.get("display_name", c.get("name", c.get("id", ""))) for c in concepts]
        concept_names = [n for n in concept_names if n]

        # Load formulas
        formulas_path = base / "formulas.json"
        formula_names = []
        if formulas_path.exists():
            try:
                formulas = json.loads(formulas_path.read_text(encoding="utf-8"))
                formula_names = [f.get("display_name", f.get("id", "")) for f in formulas]
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        subject_type = self._infer_subject(str(base))

        return BaseCourseProfile(
            course_id=base.name,
            course_name=course_name,
            subject_type=subject_type,
            chapter_name=chapter_hint,
            expected_concepts=concept_names,
            expected_formulas=formula_names,
            expected_question_types=GenericCourseProfile.DEFAULT_QUESTION_TYPES,
            exam_blueprint=GenericCourseProfile.DEFAULT_EXAM_BLUEPRINT,
            source=ProfileSource.SEED_DATA,
            confidence=0.85,
        )

    def build_from_files(self, filenames: list[str], parsed_text: str = "",
                         course_id: str = "unknown") -> BaseCourseProfile:
        """Build from uploaded files."""
        return self.generic.build(filenames, parsed_text, course_id)

    # ── Internal ────────────────────────────────────────────────────────

    def _infer_course_name(self, chapter_hint: str, seed_path: str) -> str:
        """Try to derive course name from chapter or path."""
        import re
        # Extract "电磁场与电磁波" from "电磁场与电磁波 第一章 静电场"
        match = re.match(r'(.+?)\s*第[一二三四五六七八九十\d]+章', chapter_hint)
        if match:
            return match.group(1).strip()
        # From path
        path_lower = seed_path.lower()
        if "probability" in path_lower or "概率" in path_lower:
            return "概率论与随机过程"
        if "electromagnetic" in path_lower or "电磁" in path_lower:
            return "电磁场与电磁波"
        if "digital" in path_lower or "数电" in path_lower or "数字" in path_lower:
            return "数字电路逻辑设计"
        return chapter_hint or Path(seed_path).parent.name

    def _infer_subject(self, seed_path: str) -> str:
        path_lower = seed_path.lower()
        if "math" in path_lower or "概率" in path_lower:
            return "math"
        if "engineering" in path_lower or "电磁" in path_lower or "电路" in path_lower:
            return "engineering"
        return "unknown"
