"""StudyPilot AI v1.3 — Course Classifier.

Stateless rule-based classifier that maps uploaded filenames to:
- Course name (e.g. 概率论与随机过程)
- Subject type (math / engineering / humanities / language)
- Chapter name with confidence score

All methods are pure functions — no session state, no history.
This guarantees zero cross-course pollution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── Course rule definitions ─────────────────────────────────────────────────

@dataclass
class CourseRule:
    """A single course matching rule."""
    course_name: str
    subject_type: str  # math, engineering, humanities, language
    filename_keywords: list[str] = field(default_factory=list)
    typical_chapters: list[str] = field(default_factory=list)
    # Priority: higher = match first when keywords overlap
    priority: int = 100


COURSE_RULES: list[CourseRule] = [
    CourseRule(
        course_name="概率论与随机过程",
        subject_type="math",
        filename_keywords=[
            "概率论", "随机过程", "贝叶斯", "随机变量", "概率",
            "马尔可夫", "泊松", "大数定律", "中心极限", "期望",
            "方差", "协方差", "条件概率", "全概率", "先验",
            "后验", "似然", "假设检验", "参数估计", "区间估计",
        ],
        typical_chapters=[
            "随机事件与概率",
            "随机变量及其分布",
            "多维随机变量",
            "数字特征",
            "大数定律与中心极限定理",
            "随机过程基本概念",
            "泊松过程",
            "马尔可夫链",
        ],
        priority=110,
    ),
    CourseRule(
        course_name="电磁场与电磁波",
        subject_type="engineering",
        filename_keywords=[
            "静电场", "高斯", "镜像法", "电位", "电磁场",
            "场波", "电磁波", "麦克斯韦", "电动力学", "恒定电场",
            "恒定磁场", "时变", "平面波", "边界条件", "电介质",
            "导体", "电容", "电感", "传输线", "波导", "天线",
        ],
        typical_chapters=[
            "第一章 静电场",
            "第二章 恒定电场",
            "第三章 恒定磁场",
            "第四章 时变电磁场",
            "第五章 均匀平面波",
            "第六章 传输线理论",
            "第七章 波导与谐振腔",
        ],
        priority=110,
    ),
    CourseRule(
        course_name="数字电路逻辑设计",
        subject_type="engineering",
        filename_keywords=[
            "组合逻辑", "时序逻辑", "触发器", "FPGA",
            "数电", "数字电路", "逻辑门", "卡诺图",
            "状态机", "计数器", "寄存器", "译码器",
            "编码器", "数据选择器", "加法器", "移位寄存器",
        ],
        typical_chapters=[
            "数制与码制",
            "逻辑代数基础",
            "门电路",
            "组合逻辑电路",
            "触发器",
            "时序逻辑电路",
            "半导体存储器",
            "可编程逻辑器件",
        ],
        priority=110,
    ),
    CourseRule(
        course_name="信号与系统",
        subject_type="engineering",
        filename_keywords=[
            "信号", "系统分析", "信号与系统", "傅里叶", "拉普拉斯",
            "Z变换", "卷积", "采样", "频谱",
        ],
        typical_chapters=[
            "信号与系统概述",
            "时域分析",
            "傅里叶分析",
            "拉普拉斯变换",
            "Z变换",
            "采样定理",
        ],
        priority=100,
    ),
    CourseRule(
        course_name="模拟电子技术",
        subject_type="engineering",
        filename_keywords=[
            "模电", "模拟电路", "模拟电子", "放大电路",
            "运算放大器", "三极管", "二极管", "反馈",
        ],
        typical_chapters=[
            "半导体器件",
            "基本放大电路",
            "集成运算放大器",
            "反馈放大电路",
            "信号处理电路",
        ],
        priority=100,
    ),
]


# ── Subject type label map ──────────────────────────────────────────────────

SUBJECT_LABELS: dict[str, str] = {
    "math": "数学类",
    "engineering": "理工工程类",
    "humanities": "人文社科类",
    "language": "语言类",
}


# ── Chapter detection patterns (per course) ─────────────────────────────────

# Chapter detection uses both filename keywords AND explicit chapter number patterns.
# Each entry: (regex_pattern, chapter_name, base_confidence)
CHAPTER_PATTERNS: dict[str, list[tuple[str, str, float]]] = {
    "电磁场与电磁波": [
        (r"第[一1][章节]|静电(场|荷)|静电场|电场强度|库仑|散度定理", "第一章 静电场", 0.95),
        (r"第[二2][章节]|恒定电场|恒定电流|稳恒电场|电流密度|电阻", "第二章 恒定电场", 0.95),
        (r"第[三3][章节]|恒定磁场|静磁|稳恒磁场|毕奥|安培环路", "第三章 恒定磁场", 0.95),
        (r"第[四4][章节]|时变|电磁感应|法拉第|位移电流|动态电磁", "第四章 时变电磁场", 0.95),
        (r"第[五5][章节]|平面波|均匀平面|波动方程|相速|群速", "第五章 均匀平面波", 0.95),
        (r"第[六6][章节]|传输线|特性阻抗|反射系数|驻波", "第六章 传输线理论", 0.95),
        (r"第[七7][章节]|波导|谐振腔|矩形波导|TE.*TM", "第七章 波导与谐振腔", 0.95),
    ],
    "概率论与随机过程": [
        (r"第[一1][章节]|随机事件|概率.*基本|样本空间|条件概率|全概率|贝叶斯", "随机事件与概率", 0.95),
        (r"第[二2][章节]|随机变量.*分布|随机变量|分布函数|离散.*随机变量|连续.*随机变量", "随机变量及其分布", 0.95),
        (r"第[三3][章节]|多维.*随机变量|联合分布|边缘分布|条件分布|独立性", "多维随机变量", 0.95),
        (r"第[四4][章节]|数字特征|期望|方差|协方差|矩|相关系数", "数字特征", 0.95),
        (r"第[五5][章节]|大数定律|中心极限|切比雪夫|辛钦", "大数定律与中心极限定理", 0.95),
        (r"第[六6][章节]|随机过程.*基本|平稳过程|相关函数|谱密度", "随机过程基本概念", 0.95),
        (r"泊松过程|poisson|泊松.*过程", "泊松过程", 0.85),
        (r"马尔可夫|markov|马氏链|转移概率|状态.*分类", "马尔可夫链", 0.85),
    ],
    "数字电路逻辑设计": [
        (r"第[一1][章节]|数制|码制|二进制|十六进制|BCD|格雷码", "数制与码制", 0.95),
        (r"第[二2][章节]|逻辑代数|布尔代数|摩根|卡诺图|公式.*化简", "逻辑代数基础", 0.95),
        (r"第[三3][章节]|门电路|TTL|CMOS|与非|或非|异或", "门电路", 0.95),
        (r"第[四4][章节]|组合逻辑|编码器|译码器|数据选择器|加法器", "组合逻辑电路", 0.95),
        (r"第[五5][章节]|触发器|RS|JK|D触发器|T触发器|锁存器", "触发器", 0.95),
        (r"第[六6][章节]|时序逻辑|计数器|寄存器|状态机|移位", "时序逻辑电路", 0.95),
    ],
}

# Fallback: generic chapter number patterns
GENERIC_CHAPTER_PATTERN = re.compile(
    r"第\s*([一二三四五六七八九十\d]+)\s*[章节]"
)

CN_NUM_MAP = {
    "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
    "六": "6", "七": "7", "八": "8", "九": "9", "十": "10",
}


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


class CourseClassifier:
    """Stateless classifier — call with fresh inputs each time, no history."""

    def classify(self, filenames: list[str]) -> dict[str, Any]:
        """Classify course and subject from a list of uploaded filenames.

        Args:
            filenames: List of uploaded file names, e.g.
                       ["概率论与随机过程.pdf", "2015-2020 随机过程试卷.pdf"]

        Returns:
            dict with keys:
                course (str | None)        — best-match course name
                subject_type (str | None)  — math / engineering / humanities / language
                subject_label (str | None) — human-readable label
                confidence (float)         — 0.0–1.0
                source (str)               — how the match was made
                matched_keywords (list)    — which keywords matched
                all_candidates (list)      — all courses that matched with scores
        """
        if not filenames:
            return {
                "course": None,
                "subject_type": None,
                "subject_label": None,
                "confidence": 0.0,
                "source": "no_files",
                "matched_keywords": [],
                "all_candidates": [],
            }

        combined = " ".join(filenames).lower().replace("_", " ").replace("-", " ")

        # Score every course rule
        candidates: list[dict] = []
        for rule in COURSE_RULES:
            matched = []
            total_weight = len(rule.filename_keywords)
            for kw in rule.filename_keywords:
                if kw.lower() in combined:
                    matched.append(kw)

            if matched:
                # Confidence: fraction of keywords matched, capped at 0.95
                # Add bonus for longer keyword matches
                raw_score = len(matched) / max(1, total_weight)
                # Bonus for specific (long) keyword matches
                long_match_bonus = sum(
                    0.05 for kw in matched if len(kw) >= 4
                )
                confidence = min(0.95, raw_score * 0.6 + 0.3 + long_match_bonus)

                candidates.append({
                    "course": rule.course_name,
                    "subject_type": rule.subject_type,
                    "subject_label": SUBJECT_LABELS.get(rule.subject_type, rule.subject_type),
                    "confidence": round(confidence, 3),
                    "matched_keywords": matched,
                    "match_count": len(matched),
                    "priority": rule.priority,
                })

        if not candidates:
            return {
                "course": None,
                "subject_type": None,
                "subject_label": None,
                "confidence": 0.0,
                "source": "no_match",
                "matched_keywords": [],
                "all_candidates": [],
            }

        # Sort by: priority desc, match_count desc, confidence desc
        candidates.sort(
            key=lambda c: (c["priority"], c["match_count"], c["confidence"]),
            reverse=True,
        )

        best = candidates[0]

        # Build source description
        if best["match_count"] >= 2:
            source = f"文件名匹配 ({best['match_count']}个关键词)"
        else:
            source = "文件名匹配 (单关键词)"

        return {
            "course": best["course"],
            "subject_type": best["subject_type"],
            "subject_label": best["subject_label"],
            "confidence": best["confidence"],
            "source": source,
            "matched_keywords": best["matched_keywords"],
            "all_candidates": candidates,
        }

    def detect_chapter(
        self,
        filenames: list[str],
        course_name: str | None = None,
    ) -> dict[str, Any]:
        """Detect chapter from filenames, optionally scoped to a known course.

        Args:
            filenames: List of uploaded file names.
            course_name: If known, use course-specific chapter patterns.

        Returns:
            dict with keys:
                chapter_name (str | None)
                confidence (float)
                source (str)
        """
        if not filenames:
            return {
                "chapter_name": None,
                "confidence": 0.0,
                "source": "no_files",
            }

        combined = " ".join(filenames).lower().replace("_", " ").replace("-", " ")

        # 1) Try course-specific chapter patterns (high confidence)
        if course_name and course_name in CHAPTER_PATTERNS:
            patterns = CHAPTER_PATTERNS[course_name]
            for pattern, chapter_name, base_confidence in patterns:
                if re.search(pattern, combined):
                    return {
                        "chapter_name": chapter_name,
                        "confidence": base_confidence,
                        "source": f"课程章节匹配 ({course_name})",
                    }

        # 2) Try generic "第X章" pattern across all course patterns
        generic_match = GENERIC_CHAPTER_PATTERN.search(combined)
        if generic_match:
            num = generic_match.group(1)
            num = CN_NUM_MAP.get(num, num)
            return {
                "chapter_name": f"第{num}章",
                "confidence": 0.60,
                "source": "通用章节编号匹配",
            }

        # 3) No match
        return {
            "chapter_name": None,
            "confidence": 0.0,
            "source": "no_match",
        }

    def detect_subject(
        self,
        filenames: list[str],
    ) -> dict[str, Any]:
        """Detect subject type from filenames.

        Returns:
            dict with subject_type, subject_label, confidence, source
        """
        course_result = self.classify(filenames)
        if course_result["subject_type"]:
            return {
                "subject_type": course_result["subject_type"],
                "subject_label": course_result["subject_label"],
                "confidence": course_result["confidence"],
                "source": f"课程规则推导 ({course_result['course']})",
            }

        # Fallback: keyword-based subject detection
        combined = " ".join(filenames).lower()

        math_keywords = ["数学", "概率", "统计", "高数", "线代", "离散"]
        eng_keywords = ["电路", "信号", "电磁", "数电", "模电", "物理", "通信"]

        if any(kw in combined for kw in math_keywords):
            return {
                "subject_type": "math",
                "subject_label": "数学类",
                "confidence": 0.60,
                "source": "学科关键词匹配",
            }
        if any(kw in combined for kw in eng_keywords):
            return {
                "subject_type": "engineering",
                "subject_label": "理工工程类",
                "confidence": 0.60,
                "source": "学科关键词匹配",
            }

        return {
            "subject_type": None,
            "subject_label": None,
            "confidence": 0.0,
            "source": "no_match",
        }

    def classify_full(
        self,
        filenames: list[str],
    ) -> dict[str, Any]:
        """Run full classification: course + subject + chapter in one call.

        Returns a complete RecognitionResult dict.
        """
        course_result = self.classify(filenames)
        chapter_result = self.detect_chapter(
            filenames, course_name=course_result["course"]
        )
        subject_result = self.detect_subject(filenames)

        # Use course-derived subject when available (higher confidence)
        if course_result["confidence"] > 0 and course_result["subject_type"]:
            subject_result = {
                "subject_type": course_result["subject_type"],
                "subject_label": course_result["subject_label"],
                "confidence": course_result["confidence"],
                "source": f"课程规则推导 ({course_result['course']})",
            }

        return {
            "course": course_result["course"],
            "course_confidence": course_result["confidence"],
            "course_source": course_result["source"],
            "course_matched_keywords": course_result["matched_keywords"],
            "chapter": chapter_result["chapter_name"],
            "chapter_confidence": chapter_result["confidence"],
            "chapter_source": chapter_result["source"],
            "subject_type": subject_result["subject_type"],
            "subject_label": subject_result["subject_label"],
            "subject_confidence": subject_result["confidence"],
            "subject_source": subject_result["source"],
        }


# ── Convenience function ────────────────────────────────────────────────────

def classify_uploads(filenames: list[str]) -> dict[str, Any]:
    """One-shot classification of uploaded files.

    >>> classify_uploads(["概率论与随机过程.pdf"])
    {'course': '概率论与随机过程', 'course_confidence': 0.9, ...}
    """
    return CourseClassifier().classify_full(filenames)
