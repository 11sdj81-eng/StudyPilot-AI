"""Unified Course Profile System — the single source of truth for course configuration.

Replaces fragmented profile systems at:
- quality/course_profiles.py (ChapterProfile)
- course_profiles/ (CourseProfile)
- exam_blueprint/exam_blueprint_registry.py (ExamBlueprint)

All validators MUST use this registry. Unknown courses get GenericCourseProfile — never silently skipped.
"""

from core.course_profiles.base_profile import BaseCourseProfile
from core.course_profiles.generic_course_profile import GenericCourseProfile, ProfileConfidence
from core.course_profiles.profile_builder import ProfileBuilder
from core.course_profiles.profile_registry import ProfileRegistry, get_profile

# Re-export existing known profiles
from core.pdf_content_v2.course_profiles.probability_ch2 import PROBABILITY_CH2_PROFILE
from core.pdf_content_v2.course_profiles.field_wave_ch1 import FIELD_WAVE_CH1_PROFILE
from core.pdf_content_v2.course_profiles.digital_logic_ch3 import DIGITAL_LOGIC_CH3_PROFILE
