"""CoursePluginRegistry — maps course_id to plugin instance. NEVER returns None."""

from __future__ import annotations

from typing import Any

from core.course_plugins.base_plugin import BaseCoursePlugin
from core.course_plugins.generic_plugin import GenericCoursePlugin


class CourseNotSupportedError(RuntimeError):
    """Raised when a course has no valid plugin and no GenericCoursePlugin fallback is allowed."""
    pass


class CoursePluginRegistry:
    """Resolves course_id → BaseCoursePlugin instance.

    Three-tier resolution:
        1. Known course plugin (registered by course_id)
        2. GenericCoursePlugin via GenericCourseProfile auto-extraction
        3. FAIL — never silently returns wrong content

    This is the single routing point for PDF generation.
    All render paths MUST go through get_plugin().
    """

    def __init__(self):
        self._plugins: dict[str, BaseCoursePlugin] = {}
        self._register_known()

    def _register_known(self) -> None:
        """Register plugins for courses with known implementations."""
        # Each known course gets a BaseCoursePlugin instance
        # The plugin's methods delegate to the course profile + seed data
        try:
            from core.course_profiles.profile_registry import get_profile
            profile = get_profile("probability_ch2")
            if profile and not profile.is_generic:
                self._plugins["probability_ch2"] = _CourseProfilePlugin(
                    course_id="probability_ch2",
                    course_name=profile.course_name,
                    subject_type=profile.subject_type,
                    profile=profile,
                )
        except Exception:
            pass

        try:
            from core.course_profiles.profile_registry import get_profile
            profile = get_profile("field_wave_ch1")
            if profile and not profile.is_generic:
                self._plugins["field_wave_ch1"] = _CourseProfilePlugin(
                    course_id="field_wave_ch1",
                    course_name=profile.course_name,
                    subject_type=profile.subject_type,
                    profile=profile,
                )
        except Exception:
            pass

        try:
            from core.course_profiles.profile_registry import get_profile
            profile = get_profile("digital_logic_ch3")
            if profile and not profile.is_generic:
                self._plugins["digital_logic_ch3"] = _CourseProfilePlugin(
                    course_id="digital_logic_ch3",
                    course_name=profile.course_name,
                    subject_type=profile.subject_type,
                    profile=profile,
                    is_demo=True,  # No textbook uploaded
                )
        except Exception:
            pass

    def get_plugin(self, course_id: str, allow_generic: bool = True) -> BaseCoursePlugin:
        """Get plugin for course_id. NEVER returns None.

        Args:
            course_id: The course identifier
            allow_generic: If True, falls back to GenericCoursePlugin for unknown courses.
                          If False, raises CourseNotSupportedError.

        Returns:
            BaseCoursePlugin instance

        Raises:
            CourseNotSupportedError: If no plugin found and allow_generic is False
        """
        # 1. Known course
        if course_id in self._plugins:
            return self._plugins[course_id]

        # 2. Try auto-extraction via GenericCoursePlugin
        if allow_generic:
            from core.course_profiles.profile_registry import get_profile
            profile = get_profile(course_id)
            return GenericCoursePlugin(
                course_id=course_id,
                course_name=profile.course_name,
                subject_type=profile.subject_type,
            )

        # 3. FAIL — no fallback allowed
        raise CourseNotSupportedError(
            f"Course '{course_id}' has no registered plugin and generic fallback is disabled. "
            f"Upload textbook/PPT/past papers to enable auto-extraction, or register a course plugin."
        )

    def register(self, course_id: str, plugin: BaseCoursePlugin) -> None:
        """Register a custom plugin for a course."""
        self._plugins[course_id] = plugin

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())

    def is_known(self, course_id: str) -> bool:
        return course_id in self._plugins

    def stats(self) -> dict:
        return {
            "registered_plugins": len(self._plugins),
            "plugin_ids": list(self._plugins.keys()),
        }


class _CourseProfilePlugin(BaseCoursePlugin):
    """Plugin that delegates to a CourseProfile for content extraction.

    This bridges the CourseProfile system (which already exists and works)
    with the CoursePlugin interface (which was defined but never wired).
    """

    def __init__(self, course_id: str, course_name: str, subject_type: str,
                 profile: Any = None, is_demo: bool = False):
        super().__init__(course_id=course_id, course_name=course_name,
                         subject_type=subject_type)
        self.profile = profile
        self.is_demo = is_demo

    def extract_concepts(self, materials: dict | None = None) -> list[str]:
        if self.profile:
            return list(self.profile.expected_concepts)
        return []

    def extract_formulas(self, materials: dict | None = None) -> list[str]:
        if self.profile:
            return list(self.profile.expected_formulas)
        return []

    def extract_question_types(self, materials: dict | None = None) -> list[str]:
        if self.profile:
            return list(self.profile.expected_question_types)
        return super().extract_question_types(materials)

    def concept_ids(self) -> list[str]:
        if self.profile:
            return list(self.profile.expected_concepts)
        return []

    def forbidden_keywords(self) -> list[str]:
        if self.profile:
            return list(self.profile.forbidden_keywords)
        return []

    def required_keywords(self) -> list[str]:
        if self.profile:
            return list(self.profile.required_keywords)
        return []

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["is_demo"] = self.is_demo
        d["profile_source"] = self.profile.source.value if self.profile else "none"
        return d


# ── Singleton ───────────────────────────────────────────────────────────

_registry: CoursePluginRegistry | None = None


def get_plugin_registry() -> CoursePluginRegistry:
    global _registry
    if _registry is None:
        _registry = CoursePluginRegistry()
    return _registry


def get_plugin(course_id: str, allow_generic: bool = True) -> BaseCoursePlugin:
    """Convenience: get plugin from singleton registry. NEVER returns None."""
    return get_plugin_registry().get_plugin(course_id, allow_generic=allow_generic)
