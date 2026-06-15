import json

from core.config import LEARNING_PROFILES_FILE, ensure_json_files


DEFAULT_PROFILE = {
    "goal": "80+",
    "level": "一般",
    "daily_hours": 3,
    "remaining_days": 7,
    "preferred_styles": ["详细讲解", "经典例题"],
    "learning_phase": "期末复习",
}


def load_profiles() -> dict:
    ensure_json_files()
    return json.loads(LEARNING_PROFILES_FILE.read_text(encoding="utf-8"))


def save_profile(course_id: str, profile: dict) -> None:
    profiles = load_profiles()
    profiles[course_id] = profile
    LEARNING_PROFILES_FILE.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def get_profile(course_id: str | None) -> dict:
    if not course_id:
        return DEFAULT_PROFILE.copy()
    raw = load_profiles().get(course_id, DEFAULT_PROFILE.copy())
    # 向后兼容 v1.0：将旧的 preferred_style 字符串迁移为 preferred_styles 列表
    if "preferred_styles" not in raw and "preferred_style" in raw:
        raw["preferred_styles"] = [raw.pop("preferred_style")]
    # v1.0 兼容：如果没有 learning_phase，使用默认值
    if "learning_phase" not in raw:
        raw["learning_phase"] = DEFAULT_PROFILE["learning_phase"]
    return raw
