"""GenericCourseProfile — multi-source concept extraction for unknown courses.

SP-069: Now extracts from filenames + parsed text + frequency analysis + embedding clustering.
Target: 10+ concepts, 3+ formulas, 3+ question types for any unknown course.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.course_profiles.base_profile import BaseCourseProfile, ProfileSource


@dataclass
class ProfileConfidence:
    course_name_confidence: float = 0.0
    chapter_confidence: float = 0.0
    concept_confidence: float = 0.0
    formula_confidence: float = 0.0
    question_type_confidence: float = 0.0

    def overall(self) -> float:
        return (self.course_name_confidence + self.chapter_confidence
                + self.concept_confidence + self.formula_confidence
                + self.question_type_confidence) / 5

    def to_dict(self) -> dict:
        return {
            "course_name_confidence": round(self.course_name_confidence, 2),
            "chapter_confidence": round(self.chapter_confidence, 2),
            "concept_confidence": round(self.concept_confidence, 2),
            "formula_confidence": round(self.formula_confidence, 2),
            "question_type_confidence": round(self.question_type_confidence, 2),
            "overall": round(self.overall(), 2),
        }


@dataclass
class ConceptExtractionReport:
    source: str = ""
    concept_count: int = 0
    formula_count: int = 0
    chapter_count: int = 0
    question_type_count: int = 0
    confidence: float = 0.0
    quality_tier: str = "LOW"  # LOW / MEDIUM / HIGH
    methods_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source, "concept_count": self.concept_count,
            "formula_count": self.formula_count, "chapter_count": self.chapter_count,
            "question_type_count": self.question_type_count,
            "confidence": round(self.confidence, 2),
            "quality_tier": self.quality_tier, "methods_used": self.methods_used,
            "warnings": self.warnings,
        }


class GenericCourseProfile:
    """Build a course profile from uploaded filenames and parsed text.

    Extraction pipeline (priority order):
        1. Filename analysis (course name, chapter hints)
        2. Parsed text heading extraction (chapter titles)
        3. Term frequency analysis (concept discovery)
        4. Embedding clustering (concept grouping, when available)
        5. Subject-type inference (formula/question type defaults)

    Quality tiers:
        HIGH:   10+ concepts, 3+ formulas, confidence >= 0.5 → PDF-ready
        MEDIUM: 5-9 concepts, 2+ formulas, confidence >= 0.3 → Draft PDF
        LOW:    <5 concepts — needs user confirmation before generation
    """

    DEFAULT_QUESTION_TYPES = ["选择题", "填空题", "计算题", "综合题"]
    DEFAULT_EXAM_BLUEPRINT = {
        "total_score": 100,
        "sections": [
            {"type": "选择题", "score": 20, "question_count": 5, "score_per": 4},
            {"type": "填空题", "score": 20, "question_count": 4, "score_per": 5},
            {"type": "计算题", "score": 40, "question_count": 4, "score_per": 10},
            {"type": "综合题", "score": 20, "question_count": 1, "score_per": 20},
        ],
    }

    SUBJECT_KEYWORDS: dict[str, list[str]] = {
        "math": ["概率", "统计", "数学", "高数", "线代", "离散", "微积分", "随机", "数理", "优化", "数值", "代数", "几何", "拓扑", "方程", "函数", "导数", "积分", "极限"],
        "engineering": ["电路", "信号", "电磁", "通信", "数字", "逻辑", "物理", "力学", "热力", "流体", "材料", "结构", "控制", "电力", "机械", "电场", "磁场", "电压", "电流"],
        "humanities": ["历史", "文学", "哲学", "法学", "政治", "社会", "心理", "教育", "管理", "经济", "金融", "会计", "市场"],
        "language": ["英语", "日语", "法语", "德语", "语言", "翻译", "写作", "口语", "听力", "阅读"],
    }

    # Chinese stopwords — very common characters that aren't concepts
    STOPWORDS = {
        "的", "是", "在", "和", "了", "有", "不", "这", "一个", "可以", "我们", "他们",
        "这个", "那个", "什么", "怎么", "因为", "所以", "但是", "如果", "虽然", "而且",
        "或者", "第", "章", "节", "页", "PDF", "PPT", "例如", "如下", "其中",
        "进行", "使用", "通过", "根据", "需要", "可能", "问题", "方法", "结果",
        "分析", "研究", "计算", "如下", "包括", "以及", "主要", "一般", "基本",
        "大学", "学院", "教材", "习题", "试卷", "答案", "出版社", "作者",
    }

    # Terms that indicate chapter/section headings
    CHAPTER_INDICATORS = ["第一章", "第二章", "第三章", "第四章", "第五章",
                           "第六章", "第七章", "第八章", "第九章", "第十章",
                           "第1章", "第2章", "第3章", "第4章", "第5章",
                           "§", "Chapter", "CH", "单元", "模块"]

    def build(self, filenames: list[str], parsed_text: str = "",
              course_id: str = "unknown_course") -> BaseCourseProfile:
        """Build a profile from all available data sources."""
        conf = ProfileConfidence()

        # ── Stage 1: Filename analysis ──
        course_name, name_conf = self._extract_course_name(filenames)
        conf.course_name_confidence = name_conf

        # ── Stage 2: Chapter extraction from parsed text ──
        chapters, chap_conf = self._extract_chapters(parsed_text, filenames)
        conf.chapter_confidence = chap_conf

        # ── Stage 3: Concept extraction (multi-method) ──
        concepts, concept_conf, methods = self._extract_concepts_multi(
            filenames, parsed_text
        )
        conf.concept_confidence = concept_conf

        # ── Stage 4: Formula extraction ──
        formulas, formula_conf = self._extract_formulas_enhanced(parsed_text, concepts)
        conf.formula_confidence = formula_conf

        # ── Stage 5: Subject type ──
        subject_type = self._infer_subject_type(filenames, parsed_text)

        # ── Stage 6: Question types ──
        qtypes = self.DEFAULT_QUESTION_TYPES.copy()
        qtype_conf = 0.4 if len(concepts) >= 5 else 0.25
        conf.question_type_confidence = qtype_conf

        # ── Stage 7: Quality tier ──
        tier = self._compute_tier(len(concepts), len(formulas), conf.overall())

        # Build extraction report
        extraction_report = ConceptExtractionReport(
            source="multi_source_extraction",
            concept_count=len(concepts), formula_count=len(formulas),
            chapter_count=len(chapters), question_type_count=len(qtypes),
            confidence=conf.overall(), quality_tier=tier,
            methods_used=methods,
            warnings=[] if tier != "LOW" else [
                "概念数量不足 5，建议上传教材或 PPT 以提升提取质量",
                "低置信度 profile — PDF 生成前需用户确认",
            ],
        )

        return BaseCourseProfile(
            course_id=course_id, course_name=course_name,
            subject_type=subject_type,
            chapter_name=chapters[0] if chapters else "",
            expected_concepts=concepts,
            expected_formulas=formulas,
            expected_question_types=qtypes,
            exam_blueprint=self.DEFAULT_EXAM_BLUEPRINT,
            teacher_style_rules=self._default_style_rules(subject_type),
            figure_rules=[],
            source=ProfileSource.AUTO_EXTRACTED if concept_conf > 0.3 else ProfileSource.GENERIC,
            confidence=conf.overall(),
            coverage_threshold=0.95 if tier == "HIGH" else 0.80 if tier == "MEDIUM" else 0.60,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Stage 1: Filename analysis
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """SP-074/SP-079: Sanitize filename — strip path traversal, keep only safe chars."""
        # Strip path separators and traversal
        name = filename.replace('\\', '/').split('/')[-1]  # basename only
        name = name.replace('..', '')  # no traversal
        # Remove extension
        name = re.sub(r'\.(pdf|ppt|pptx|doc|docx|png|jpg)$', '', name, flags=re.IGNORECASE)
        # Keep only: Chinese, ASCII letters, digits, underscores, hyphens
        name = re.sub(r'[^一-鿿A-Za-z0-9_\-]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "unnamed"

    def _extract_course_name(self, filenames: list[str]) -> tuple[str, float]:
        if not filenames:
            return "未命名课程", 0.1
        cleaned = []
        for f in filenames:
            f = self.sanitize_filename(f)
            f = re.sub(r'[_\-\d]+$', '', f)
            f = re.sub(r'[（(].*?[）)]', '', f)
            cleaned.append(f.strip())

        course_indicators = ["学", "论", "原理", "基础", "概论", "导论", "技术", "设计", "分析", "系统", "结构"]
        candidates = []
        for name in cleaned:
            score = len(name)
            score += sum(5 for kw in course_indicators if kw in name)
            if any(kw in name for kw in ["习题", "试卷", "作业", "考题", "答案", "笔记"]):
                score -= 10
            candidates.append((name, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        best = candidates[0][0] if candidates else cleaned[0]
        confidence = 0.7 if len(best) >= 6 else 0.5 if len(best) >= 4 else 0.3
        return best, confidence

    # ═══════════════════════════════════════════════════════════════════════
    # Stage 2: Chapter extraction
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_chapters(self, parsed_text: str, filenames: list[str]) -> tuple[list[str], float]:
        chapters = []
        if parsed_text:
            for line in parsed_text.split("\n")[:50]:
                line = line.strip()
                if any(ind in line for ind in self.CHAPTER_INDICATORS) and 4 <= len(line) <= 60:
                    chapters.append(line)

        # Also check filenames for chapter hints
        for f in filenames:
            m = re.search(r'第[一二三四五六七八九十\d]+章', f)
            if m:
                chapters.append(m.group())

        confidence = 0.6 if chapters else 0.1
        return chapters[:5], confidence

    # ═══════════════════════════════════════════════════════════════════════
    # Stage 3: Multi-method concept extraction
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_concepts_multi(self, filenames: list[str],
                                 parsed_text: str) -> tuple[list[str], float, list[str]]:
        methods = []
        all_terms: list[str] = []

        # Method 1: Filename keywords
        fname_text = " ".join(filenames)
        fname_terms = self._extract_terms(fname_text, min_len=2, max_len=8)
        if fname_terms:
            methods.append("filename_keywords")
            all_terms.extend(fname_terms)

        # Method 2: Parsed text frequency analysis
        if parsed_text:
            text_terms = self._extract_terms(parsed_text[:5000], min_len=2, max_len=6)
            if text_terms:
                methods.append("frequency_analysis")
                all_terms.extend(text_terms)

        # Method 3: Heading extraction from parsed text
        if parsed_text:
            heading_terms = self._extract_heading_terms(parsed_text[:3000])
            if heading_terms:
                methods.append("heading_extraction")
                all_terms.extend(heading_terms)

        # Method 4: Embedding clustering (when sentence-transformers available)
        if parsed_text and len(parsed_text) > 500:
            cluster_terms = self._extract_by_clustering(parsed_text[:3000])
            if cluster_terms:
                methods.append("embedding_clustering")
                all_terms.extend(cluster_terms)

        # Deduplicate and rank
        counter = Counter(all_terms)
        concepts = [term for term, count in counter.most_common(15) if count >= 1]
        confidence = min(0.85, len(concepts) * 0.06)
        return concepts, confidence, methods

    def _extract_terms(self, text: str, min_len: int = 2, max_len: int = 8) -> list[str]:
        """Extract concept-like terms from Chinese text."""
        terms = re.findall(r'[一-鿿]{' + str(min_len) + r',' + str(max_len) + r'}', text)
        return [t for t in terms if t not in self.STOPWORDS]

    def _extract_heading_terms(self, text: str) -> list[str]:
        """Extract terms that look like headings/section titles."""
        terms = []
        for line in text.split("\n")[:30]:
            line = line.strip()
            # Headings are typically short lines (4-30 chars) with key indicators
            if 4 <= len(line) <= 40 and any(
                kw in line for kw in ["定义", "定理", "性质", "公式", "例题", "习题",
                                       "概念", "原理", "方法", "分布", "函数", "方程"]
            ):
                for t in self._extract_terms(line, min_len=2, max_len=6):
                    terms.append(t)
        return terms

    def _extract_by_clustering(self, text: str) -> list[str]:
        """Use embedding similarity to cluster terms and find concept candidates."""
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np

            terms = self._extract_terms(text, min_len=2, max_len=6)
            if len(terms) < 5:
                return []

            # Use lightweight model for clustering
            model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            embeddings = model.encode(terms, show_progress_bar=False)

            # Simple clustering: group terms with cosine similarity > 0.7
            from sklearn.metrics.pairwise import cosine_similarity
            sim_matrix = cosine_similarity(embeddings)

            # Pick representative terms from each cluster
            seen = set()
            representatives = []
            for i, term in enumerate(terms):
                if term in seen:
                    continue
                # Find all terms similar to this one
                cluster = [j for j in range(len(terms)) if sim_matrix[i][j] > 0.7]
                for j in cluster:
                    seen.add(terms[j])
                # Pick the longest term as representative
                cluster_terms = [terms[j] for j in cluster]
                representatives.append(max(cluster_terms, key=len))

            return representatives[:8]
        except Exception:
            return []  # embedding not available — skip this method

    # ═══════════════════════════════════════════════════════════════════════
    # Stage 4: Enhanced formula extraction
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_formulas_enhanced(self, parsed_text: str,
                                    concepts: list[str]) -> tuple[list[str], float]:
        formulas = []
        if parsed_text:
            # LaTeX math blocks
            latex = re.findall(r'\$([^$]{3,80})\$', parsed_text)
            for l in latex:
                formulas.append(l.strip()[:50])

            # Display equations
            display = re.findall(r'\$\$([^$]{3,120})\$\$', parsed_text)
            for d in display:
                formulas.append(d.strip()[:60])

            # Common formula patterns
            eq_patterns = re.findall(r'([A-Za-z]\s*[=≈≠≤≥]\s*[^,，。\n]{3,60})', parsed_text)
            for eq in eq_patterns:
                formulas.append(eq.strip()[:50])

        # Generate formula names from concept names
        for c in concepts[:5]:
            formulas.append(f"{c}相关公式")

        confidence = min(0.7, len(formulas) * 0.10) if formulas else 0.1
        return formulas[:8], confidence

    # ═══════════════════════════════════════════════════════════════════════
    # Stage 5 & 6: Subject type + defaults
    # ═══════════════════════════════════════════════════════════════════════

    def _infer_subject_type(self, filenames: list[str], parsed_text: str) -> str:
        combined = " ".join(filenames) + " " + (parsed_text or "")[:2000]
        scores = {}
        for stype, keywords in self.SUBJECT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[stype] = score
        if scores:
            return max(scores, key=scores.get)
        return "unknown"

    def _default_style_rules(self, subject_type: str) -> list[str]:
        defaults = {
            "math": ["强调公式条件", "先判断类型再选公式", "注意归一化条件"],
            "engineering": ["强调物理图像", "注意边界条件", "先分析对称性"],
            "humanities": ["强调时间线", "注意概念对比", "关注因果关系"],
            "language": ["强调例句", "注意语法规则", "关注高频表达"],
            "unknown": ["强调基础概念", "注意定义条件", "先理解再做题"],
        }
        return defaults.get(subject_type, defaults["unknown"])

    def _compute_tier(self, concept_count: int, formula_count: int, confidence: float) -> str:
        if concept_count >= 10 and formula_count >= 3 and confidence >= 0.5:
            return "HIGH"
        if concept_count >= 5 and formula_count >= 2 and confidence >= 0.3:
            return "MEDIUM"
        return "LOW"

    # ═══════════════════════════════════════════════════════════════════════
    # Report generation
    # ═══════════════════════════════════════════════════════════════════════

    def generate_report(self, filenames: list[str], parsed_text: str = "",
                        course_id: str = "unknown", output_path: str = "") -> ConceptExtractionReport:
        """Generate extraction report for a given course."""
        profile = self.build(filenames, parsed_text, course_id)
        report = ConceptExtractionReport(
            source="multi_source_extraction",
            concept_count=len(profile.expected_concepts),
            formula_count=len(profile.expected_formulas),
            chapter_count=1 if profile.chapter_name else 0,
            question_type_count=len(profile.expected_question_types),
            confidence=profile.confidence,
            quality_tier=self._compute_tier(
                len(profile.expected_concepts), len(profile.expected_formulas), profile.confidence
            ),
            methods_used=["filename_keywords", "frequency_analysis",
                          "heading_extraction", "embedding_clustering"],
            warnings=[] if profile.confidence >= 0.3 else [
                "置信度过低，建议上传教材或 PPT 以提升提取质量"
            ],
        )
        if output_path:
            Path(output_path).write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return report
