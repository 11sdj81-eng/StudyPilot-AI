"""Course profiles — syllabus-level knowledge coverage definitions for PDF 3.0."""

from core.pdf_content_v2.course_profiles.base import CourseProfile, ExpectedConcept, ExpectedFormula, ExpectedQuestionType
from core.pdf_content_v2.course_profiles.probability_ch2 import PROBABILITY_CH2_PROFILE
from core.pdf_content_v2.course_profiles.field_wave_ch1 import FIELD_WAVE_CH1_PROFILE
from core.pdf_content_v2.course_profiles.digital_logic_ch3 import DIGITAL_LOGIC_CH3_PROFILE

REGISTRY: dict[str, CourseProfile] = {
    "概率论与随机过程::ch2": PROBABILITY_CH2_PROFILE,
    "电磁场与电磁波::ch1": FIELD_WAVE_CH1_PROFILE,
    "数字电路逻辑设计::ch3": DIGITAL_LOGIC_CH3_PROFILE,
}


def get_course_profile(course_name: str, chapter_key: str = "ch2") -> CourseProfile | None:
    return REGISTRY.get(f"{course_name}::{chapter_key}")


def list_profiles() -> list[str]:
    return list(REGISTRY.keys())
