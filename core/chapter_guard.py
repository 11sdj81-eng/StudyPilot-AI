"""Chapter scope guard for generated study materials."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass
class ChapterScope:
    chapter: str
    allow_topics: list[str]
    forbidden_topics: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def build_chapter_scope(course: dict | None = None, chapter: str = "第一章 静电场") -> ChapterScope:
    return ChapterScope(
        chapter=chapter,
        allow_topics=["库仑定律", "电场强度", "高斯定理", "电位", "边界条件", "镜像法", "静电能量"],
        forbidden_topics=["电磁波传播", "波导", "时变场深入", "均匀平面波", "谐振腔", "传输线"],
    )


def check_chapter_scope(content: str, scope: ChapterScope | None = None) -> dict:
    scope = scope or build_chapter_scope()
    text = str(content or "")
    forbidden_hits: list[str] = []
    for topic in scope.forbidden_topics:
        for match in re.finditer(re.escape(topic), text):
            window = text[max(0, match.start() - 24): match.end() + 24]
            if any(marker in window for marker in ["后续", "后面", "不展开", "不涉及", "不是本章重点"]):
                continue
            forbidden_hits.append(topic)
            break
    allowed_hits = [topic for topic in scope.allow_topics if topic in text]
    return {
        "passed": not forbidden_hits,
        "chapter": scope.chapter,
        "allowed_hits": allowed_hits,
        "forbidden_hits": forbidden_hits,
    }
