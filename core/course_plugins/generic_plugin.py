"""GenericCoursePlugin — fallback for any unknown course. Never crashes, never returns wrong content."""

from __future__ import annotations

from core.course_plugins.base_plugin import BaseCoursePlugin


class GenericCoursePlugin(BaseCoursePlugin):
    """Fallback plugin for courses without explicit implementation.

    Uses GenericCourseProfile for content extraction.
    Never returns another course's content.
    """

    def __init__(self, course_id: str = "unknown", course_name: str = "未命名课程",
                 subject_type: str = "unknown"):
        super().__init__(course_id=course_id, course_name=course_name,
                         subject_type=subject_type)

    def extract_concepts(self, materials: dict | None = None) -> list[str]:
        if materials and "parsed_text" in materials:
            return self._from_text(materials["parsed_text"])
        if materials and "filenames" in materials:
            return materials["filenames"][:5]
        return []

    def extract_formulas(self, materials: dict | None = None) -> list[str]:
        return []

    def _from_text(self, text: str) -> list[str]:
        import re
        terms = re.findall(r'[一-鿿]{2,6}', text[:3000])
        from collections import Counter
        return [t for t, _ in Counter(terms).most_common(10)]
