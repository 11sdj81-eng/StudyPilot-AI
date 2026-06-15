import json
from datetime import date
from uuid import uuid4

from core.config import COURSES_FILE, ensure_json_files


def load_courses() -> list[dict]:
    ensure_json_files()
    return json.loads(COURSES_FILE.read_text(encoding="utf-8"))


def save_courses(courses: list[dict]) -> None:
    ensure_json_files()
    COURSES_FILE.write_text(json.dumps(courses, ensure_ascii=False, indent=2), encoding="utf-8")


def create_course(university: str, course_name: str, exam_date: str | None = None) -> dict:
    courses = load_courses()
    course = {
        "course_id": f"course_{uuid4().hex[:8]}",
        "university": university.strip(),
        "course_name": course_name.strip(),
        "exam_date": exam_date or "",
        "created_at": date.today().isoformat(),
    }
    courses.append(course)
    save_courses(courses)
    return course


def update_course(course_id: str, **fields: str) -> dict | None:
    courses = load_courses()
    updated = None
    for course in courses:
        if course["course_id"] == course_id:
            course.update({k: v for k, v in fields.items() if v is not None})
            updated = course
            break
    save_courses(courses)
    return updated


def get_course(course_id: str | None) -> dict | None:
    if not course_id:
        return None
    return next((course for course in load_courses() if course["course_id"] == course_id), None)
