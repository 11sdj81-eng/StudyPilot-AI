"""Strict chapter-scope guard for v1.1 question/PDF generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class ChapterScopeV2:
    chapter: str
    allow_topics: list[str]
    forbidden_topics: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def electrostatics_scope_v2() -> ChapterScopeV2:
    return ChapterScopeV2(
        chapter="第一章 静电场",
        allow_topics=[
            "库仑定律", "电场强度", "高斯定理", "电位与电场关系", "边界条件", "镜像法",
            "静电能量", "点电荷", "均匀带电球体", "导体平面", "导体球",
        ],
        forbidden_topics=[
            "电磁波传播", "波导", "天线", "高频电磁场", "Maxwell 方程完整时变形式深讲",
            "后续章节复杂内容", "传输线", "谐振腔", "均匀平面波",
        ],
    )


def check_chapter_scope_v2(content: str, scope: ChapterScopeV2 | None = None) -> dict:
    scope = scope or electrostatics_scope_v2()
    text = str(content or "")
    forbidden_hits: list[str] = []
    for topic in scope.forbidden_topics:
        if topic in text:
            forbidden_hits.append(topic)
    allowed_hits = [topic for topic in scope.allow_topics if topic in text]
    return {
        "passed": not forbidden_hits,
        "chapter": scope.chapter,
        "allowed_hits": allowed_hits,
        "forbidden_hits": forbidden_hits,
        "in_scope_ratio_hint": round(len(allowed_hits) / max(1, len(scope.allow_topics)), 2),
    }


def metadata_in_scope_v2(metadata: dict, scope: ChapterScopeV2 | None = None) -> bool:
    scope = scope or electrostatics_scope_v2()
    topic_text = " ".join(str(metadata.get(key, "")) for key in ["knowledge_point", "chapter", "source_basis"])
    return not any(topic in topic_text for topic in scope.forbidden_topics)
