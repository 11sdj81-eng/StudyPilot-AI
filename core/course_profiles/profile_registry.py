"""ProfileRegistry — unified course profile lookup. NEVER returns None."""

from __future__ import annotations

from typing import Any

from core.course_profiles.base_profile import BaseCourseProfile, ProfileSource
from core.course_profiles.generic_course_profile import GenericCourseProfile


class ProfileRegistry:
    """Unified registry. get() NEVER returns None — falls back to GenericCourseProfile.

    This is the single point of truth for course configuration.
    All validators must call get_profile() from here.
    """

    def __init__(self):
        self._profiles: dict[str, BaseCourseProfile] = {}
        self._generic_builder = GenericCourseProfile()

        # Register known courses from seed data
        self._register_known()

    def _register_known(self) -> None:
        """Register courses with explicit seed data profiles."""
        try:
            from core.pdf_content_v2.course_profiles.probability_ch2 import PROBABILITY_CH2_PROFILE
            self.register(self._convert_legacy(PROBABILITY_CH2_PROFILE, "probability_ch2"))
        except ImportError:
            pass
        try:
            from core.pdf_content_v2.course_profiles.field_wave_ch1 import FIELD_WAVE_CH1_PROFILE
            self.register(self._convert_legacy(FIELD_WAVE_CH1_PROFILE, "field_wave_ch1"))
        except ImportError:
            pass
        try:
            from core.pdf_content_v2.course_profiles.digital_logic_ch3 import DIGITAL_LOGIC_CH3_PROFILE
            self.register(self._convert_legacy(DIGITAL_LOGIC_CH3_PROFILE, "digital_logic_ch3"))
        except ImportError:
            pass

    def _convert_legacy(self, legacy: Any, course_id: str) -> BaseCourseProfile:
        """Convert a legacy CourseProfile to unified BaseCourseProfile."""
        return BaseCourseProfile(
            course_id=course_id,
            course_name=getattr(legacy, "course_name", ""),
            subject_type=getattr(legacy, "subject_type", "unknown"),
            chapter_name=getattr(legacy, "chapter_name", ""),
            expected_concepts=[c.name for c in getattr(legacy, "expected_concepts", [])],
            expected_formulas=[f.name for f in getattr(legacy, "expected_formulas", [])],
            expected_question_types=[q.name for q in getattr(legacy, "expected_question_types", [])],
            source=ProfileSource.SEED_DATA,
            confidence=0.9,
        )

    def register(self, profile: BaseCourseProfile) -> None:
        # SP-081: Log warning on duplicate registration instead of silent overwrite
        if profile.course_id in self._profiles:
            existing = self._profiles[profile.course_id]
            if existing.source != profile.source or existing.confidence != profile.confidence:
                import warnings
                warnings.warn(
                    f"Profile '{profile.course_id}' already registered (source={existing.source.value}). "
                    f"Overwriting with source={profile.source.value}.", UserWarning
                )
        self._profiles[profile.course_id] = profile

    def get(self, course_id: str, filenames: list[str] | None = None,
            parsed_text: str = "") -> BaseCourseProfile:
        """Get a profile. NEVER returns None.

        Priority:
            1. Registered known course (seed data)
            2. Auto-extracted from filenames (GenericCourseProfile)
            3. Pure generic fallback (GenericCourseProfile with empty data)
        """
        # 1. Known course
        if course_id in self._profiles:
            return self._profiles[course_id]

        # 2. Try auto-extraction from filenames
        if filenames:
            return self._generic_builder.build(
                filenames=filenames, parsed_text=parsed_text, course_id=course_id
            )

        # 3. Pure generic fallback — never None
        return self._generic_builder.build(
            filenames=[], parsed_text="", course_id=course_id
        )

    def list_courses(self) -> list[str]:
        return list(self._profiles.keys())

    def count(self) -> int:
        return len(self._profiles)

    def stats(self) -> dict:
        profiles = list(self._profiles.values())
        return {
            "registered_courses": len(profiles),
            "by_source": {
                src.value: sum(1 for p in profiles if p.source == src)
                for src in ProfileSource
            },
        }


# ── Singleton ───────────────────────────────────────────────────────────

_registry: ProfileRegistry | None = None


def get_registry() -> ProfileRegistry:
    global _registry
    if _registry is None:
        _registry = ProfileRegistry()
    return _registry


def get_profile(course_id: str, filenames: list[str] | None = None,
                parsed_text: str = "") -> BaseCourseProfile:
    """Convenience: get profile from singleton registry. NEVER returns None."""
    return get_registry().get(course_id, filenames=filenames, parsed_text=parsed_text)
