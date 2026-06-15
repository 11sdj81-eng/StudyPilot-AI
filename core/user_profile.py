"""StudyPilot v1.3 — Personal Learning Profile.

Persistent user profile that drives personalization across the app.
Stored at data/user_profile/profile.json.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

PROFILE_DIR = Path("data/user_profile")
PROFILE_PATH = PROFILE_DIR / "profile.json"


@dataclass
class UserProfile:
    """Personal learning profile for one user/student."""

    user_name: str = "Student"
    school: str = ""
    major: str = ""
    grade: str = ""
    course_name: str = ""
    chapter_name: str = ""
    target_score: str = "85+"
    exam_date: str = ""
    remaining_days: int | None = None
    remaining_hours_today: float | None = None
    weak_points: list[str] = field(default_factory=list)
    strong_points: list[str] = field(default_factory=list)
    preferred_learning_style: str = "教材讲解 + 例题"
    preferred_pdf_style: str = "GoodNotes 友好"
    prefers_more_examples: bool = True
    prefers_more_diagrams: bool = True
    prefers_exam_driven: bool = True
    stress_level: str = "normal"
    last_generated_outputs: list[str] = field(default_factory=list)
    last_updated: str = ""

    # ── convenience ────────────────────────────────────────────────────────

    @property
    def has_urgent_exam(self) -> bool:
        """True if exam is within 1 day or remaining hours ≤ 4."""
        if self.remaining_hours_today is not None and self.remaining_hours_today <= 4:
            return True
        if self.remaining_days is not None and self.remaining_days <= 1:
            return True
        return False

    @property
    def has_weak_points(self) -> bool:
        return len(self.weak_points) > 0

    @property
    def scenario(self) -> str:
        """Infer the current learning scenario."""
        if self.has_urgent_exam:
            return "exam_sprint"
        if self.target_score in ("90+",) and self.has_weak_points:
            return "targeted_improvement"
        if self.remaining_days is not None and self.remaining_days <= 7:
            return "intensive_review"
        return "systematic_study"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfile":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid_keys})


# ── Persistence ────────────────────────────────────────────────────────────


def load_profile() -> UserProfile:
    """Load the user profile from disk, or return a default one."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            return UserProfile.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            pass
    return UserProfile()


def save_profile(profile: UserProfile) -> None:
    """Persist the user profile to disk."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    profile.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PROFILE_PATH.write_text(
        json.dumps(profile.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_profile_from_goal_text(goal_text: str, profile: UserProfile | None = None) -> UserProfile:
    """Parse a natural-language goal text and update the profile.

    Uses core.goal_parser.parse_goal_input under the hood.
    """
    from core.goal_parser import parse_goal_input

    if profile is None:
        profile = load_profile()

    parsed = parse_goal_input(goal_text)

    if parsed.get("course"):
        profile.course_name = parsed["course"]
    if parsed.get("chapter"):
        profile.chapter_name = parsed["chapter"]
    if parsed.get("target_score"):
        profile.target_score = parsed["target_score"]
    if parsed.get("remaining_time"):
        # Try to extract hours
        import re
        hours_match = re.search(r"(\d+)\s*小时", parsed["remaining_time"])
        if hours_match:
            profile.remaining_hours_today = float(hours_match.group(1))
        days_match = re.search(r"(\d+)\s*天", parsed["remaining_time"])
        if days_match:
            profile.remaining_days = int(days_match.group(1))
        if "明天" in parsed["remaining_time"]:
            profile.remaining_days = 1
        if "几小时" in parsed.get("remaining_time", ""):
            profile.remaining_hours_today = 3.0

    if parsed.get("weak_points"):
        profile.weak_points = list(dict.fromkeys(profile.weak_points + parsed["weak_points"]))

    if parsed.get("mode"):
        mode = parsed["mode"]
        if mode == "exam_sprint":
            profile.stress_level = "high"
        elif mode == "systematic_study":
            profile.stress_level = "normal"

    save_profile(profile)
    return profile


def update_profile_from_ui(
    profile: UserProfile | None = None,
    **kwargs: Any,
) -> UserProfile:
    """Update profile fields from UI widget values."""
    if profile is None:
        profile = load_profile()

    for key, value in kwargs.items():
        if hasattr(profile, key) and value is not None and value != "":
            setattr(profile, key, value)

    save_profile(profile)
    return profile


def export_profile_summary(profile: UserProfile | None = None) -> dict[str, Any]:
    """Export a human-readable summary of the profile."""
    if profile is None:
        profile = load_profile()

    return {
        "user_name": profile.user_name,
        "course": profile.course_name or "未设置",
        "chapter": profile.chapter_name or "未设置",
        "target_score": profile.target_score,
        "exam_date": profile.exam_date or "未设置",
        "remaining_days": profile.remaining_days,
        "remaining_hours": profile.remaining_hours_today,
        "weak_points": profile.weak_points,
        "strong_points": profile.strong_points,
        "scenario": profile.scenario,
        "stress_level": profile.stress_level,
        "preferred_pdf_style": profile.preferred_pdf_style,
        "last_updated": profile.last_updated,
        "has_profile": bool(profile.course_name or profile.weak_points),
    }


def reset_profile() -> UserProfile:
    """Reset the profile to default and save."""
    profile = UserProfile()
    save_profile(profile)
    return profile
