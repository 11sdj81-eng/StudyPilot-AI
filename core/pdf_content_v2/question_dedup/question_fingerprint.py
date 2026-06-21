"""QuestionFingerprint — structured identity for deduplication."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DuplicateLevel(Enum):
    EXACT = 1
    NORMALIZED = 2
    PATTERN = 3
    SEMANTIC = 4


@dataclass
class QuestionFingerprint:
    """A structured fingerprint for a single question."""
    question_id: str
    course_id: str = ""
    chapter_id: str = ""
    concept_id: str = ""
    question_type: str = ""            # choice / fill / calculation / comprehensive
    difficulty: int = 3                # 1-5
    solution_method: str = ""          # e.g. "cdf_method", "binomial_formula"
    knowledge_tags: list[str] = field(default_factory=list)
    raw_text: str = ""                 # original question text
    normalized_text: str = ""          # numbers/variables removed
    normalized_text_hash: str = ""     # md5 of normalized text
    source_pdf: str = ""               # which PDF this question came from

    def __post_init__(self):
        if not self.normalized_text and self.raw_text:
            self.normalized_text = self._normalize(self.raw_text)
        if not self.normalized_text_hash and self.normalized_text:
            self.normalized_text_hash = hashlib.md5(
                self.normalized_text.encode()
            ).hexdigest()

    @staticmethod
    def _normalize(text: str) -> str:
        """Remove numbers, units, variable names; keep structure."""
        t = text.lower()
        t = re.sub(r'[0-9]+\.?[0-9]*', '{N}', t)         # numbers → {N}
        t = re.sub(r'[a-zA-Z_][a-zA-Z0-9_]*', '{VAR}', t) # variables → {VAR}
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def key(self) -> str:
        """Unique key for exact matching."""
        return f"{self.course_id}|{self.concept_id}|{self.question_type}|{self.solution_method}"

    def pattern_key(self) -> str:
        """Key for pattern-level matching (same concept + method + type)."""
        return f"{self.concept_id}|{self.question_type}|{self.solution_method}"

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "course_id": self.course_id, "chapter_id": self.chapter_id,
            "concept_id": self.concept_id, "question_type": self.question_type,
            "difficulty": self.difficulty, "solution_method": self.solution_method,
            "knowledge_tags": self.knowledge_tags,
            "normalized_text_hash": self.normalized_text_hash,
            "source_pdf": self.source_pdf,
        }

    @classmethod
    def from_dict(cls, q: dict, source_pdf: str = "") -> "QuestionFingerprint":
        """Create a fingerprint from a question dict (from Typst extraction)."""
        raw = str(q.get("stem", q.get("problem", "")))
        concept = cls._guess_concept(raw)
        sol_method = cls._guess_method(raw, q.get("type", q.get("question_type", "")))
        diff = cls._guess_difficulty(q.get("difficulty", q.get("score", 3)))
        return cls(
            question_id=str(q.get("id", q.get("question_id", ""))),
            course_id=q.get("course_id", "probability_ch2"),
            chapter_id=q.get("chapter_id", "ch2"),
            concept_id=concept,
            question_type=str(q.get("type", q.get("question_type", ""))),
            difficulty=diff,
            solution_method=sol_method,
            knowledge_tags=cls._guess_tags(raw),
            raw_text=raw,
            source_pdf=source_pdf,
        )

    @staticmethod
    def _guess_concept(text: str) -> str:
        m = {
            "随机变量": "random_variable", "分布函数": "distribution_function",
            "离散": "discrete_random_variable", "连续": "continuous_random_variable",
            "二项": "binomial", "泊松": "poisson", "正态": "normal",
            "指数": "exponential", "均匀": "uniform", "几何": "geometric",
            "超几何": "hypergeometric", "变换": "rv_function_distribution",
            "分布律": "discrete_random_variable", "密度": "continuous_random_variable",
            "标准化": "normal", "分布": "distribution_function",
        }
        for kw, cid in m.items():
            if kw in text:
                return cid
        return "unknown"

    @staticmethod
    def _guess_method(text: str, qtype: str) -> str:
        m = {
            "分布函数法": "cdf_method", "标准化": "standardize",
            "单调变换": "monotonic_transform", "公式法": "formula_direct",
            "查表": "table_lookup", "补事件": "complement", "归一化": "normalize",
            "组合数": "combinatorial", "积分": "integration",
        }
        for kw, method in m.items():
            if kw in text:
                return method
        if "计算" in qtype:
            return "formula_direct"
        if "选择" in qtype:
            return "concept_judgment"
        if "填空" in qtype:
            return "formula_recall"
        return "unknown"

    @staticmethod
    def _guess_tags(text: str) -> list[str]:
        tags = []
        kw_map = {
            "概率": "probability", "期望": "expectation", "方差": "variance",
            "条件": "conditions", "定义": "definition", "性质": "properties",
        }
        for kw, tag in kw_map.items():
            if kw in text:
                tags.append(tag)
        return tags

    @staticmethod
    def _guess_difficulty(raw: Any) -> int:
        if isinstance(raw, int):
            return max(1, min(5, raw))
        if isinstance(raw, str):
            return {
                "基础": 2, "典型": 3, "综合": 4, "高": 4, "难": 5,
            }.get(raw, 3)
        if isinstance(raw, (int, float)):
            # Score-based: higher score → higher difficulty
            s = float(raw)
            return 2 if s <= 4 else 3 if s <= 10 else 4 if s <= 20 else 5
        return 3
