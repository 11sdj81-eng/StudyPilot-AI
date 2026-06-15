import json
from datetime import datetime
from uuid import uuid4

from core.config import METADATA_FILE, ensure_json_files


def load_metadata() -> list[dict]:
    ensure_json_files()
    return json.loads(METADATA_FILE.read_text(encoding="utf-8"))


def save_metadata(items: list[dict]) -> None:
    ensure_json_files()
    METADATA_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add_resource_metadata(
    course: dict,
    book_name: str,
    edition: str,
    resource_type: str,
    year: str,
    teacher: str,
    filename: str,
    file_path: str,
    analysis: dict | None = None,
    status: str = "completed",
) -> dict:
    items = load_metadata()
    resource = {
        "resource_id": f"res_{uuid4().hex[:8]}",
        "course_id": course["course_id"],
        "university": course.get("university", ""),
        "course_name": course.get("course_name", ""),
        "book_name": book_name.strip(),
        "edition": edition.strip(),
        "resource_type": resource_type,
        "year": str(year).strip(),
        "teacher": teacher.strip(),
        "filename": filename,
        "file_path": file_path,
        "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "analysis": analysis or {},
    }
    items.append(resource)
    save_metadata(items)
    return resource


def resources_for_course(course_id: str) -> list[dict]:
    return [item for item in load_metadata() if item.get("course_id") == course_id]


def delete_resource_metadata(resource_id: str) -> dict | None:
    """删除指定 resource 的元数据，返回被删除的记录（若不存在则返回 None）。"""
    items = load_metadata()
    target = next((item for item in items if item.get("resource_id") == resource_id), None)
    if target is None:
        return None
    items = [item for item in items if item.get("resource_id") != resource_id]
    save_metadata(items)
    return target
