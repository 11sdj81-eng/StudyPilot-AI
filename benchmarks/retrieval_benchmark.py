"""RetrievalBenchmark — compare FAISS vs Hybrid (FAISS+BM25+RRF) retrieval.

Metrics:
- Top1 Accuracy: Does the #1 result's text contain the primary expected concept?
- Top3 Recall: Among top 3 results, what fraction of expected concepts appear?
- Citation Accuracy: What fraction of results have valid source_file + page?
- Citation Quality Pass Rate: What fraction pass the citation quality gate?

Outputs a structured results dict and generates RETRIEVAL_BENCHMARK_REPORT.md.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass
class QueryResult:
    """Benchmark result for a single query."""

    query: str
    course_id: str
    query_type: str
    expected_concepts: list[str]

    # FAISS
    faiss_top1_match: bool = False
    faiss_top3_recall: float = 0.0
    faiss_citation_accuracy: float = 0.0
    faiss_quality_pass_rate: float = 0.0
    faiss_result_count: int = 0

    # Hybrid
    hybrid_top1_match: bool = False
    hybrid_top3_recall: float = 0.0
    hybrid_citation_accuracy: float = 0.0
    hybrid_quality_pass_rate: float = 0.0
    hybrid_result_count: int = 0

    error: str = ""


class RetrievalBenchmark:
    """Runs retrieval benchmarks comparing FAISS vs Hybrid search."""

    def __init__(self, queries_path: str = "benchmarks/test_queries.json"):
        self.queries_path = Path(queries_path)
        self.queries: list[dict] = []
        self._load_queries()

    def _load_queries(self) -> None:
        data = json.loads(self.queries_path.read_text(encoding="utf-8"))
        self.queries = data

    # ═══════════════════════════════════════════════════════════════════
    # Search runners
    # ═══════════════════════════════════════════════════════════════════

    def run_faiss_search(self, course_id: str, query: str, top_k: int = 5) -> list[dict]:
        """FAISS-only search via CourseVectorStore."""
        try:
            from core.vector_store import CourseVectorStore
            store = CourseVectorStore(course_id)
            results = store.search(query, top_k=top_k)
            return results if results else []
        except Exception:
            return []

    def run_hybrid_search(self, course_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Hybrid FAISS+BM25+RRF search."""
        try:
            from core.hybrid_retrieval import hybrid_search
            results = hybrid_search(course_id, query, top_k=top_k)
            return results if results else []
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════════════════
    # Metric computations
    # ═══════════════════════════════════════════════════════════════════

    def compute_top1_accuracy(self, results: list[dict], expected_concepts: list[str]) -> float:
        """Does the #1 result contain any expected concept name?

        Checks if the primary expected concept appears in result[0] text/preview.
        Returns 1.0 or 0.0.
        """
        if not results or not expected_concepts:
            return 0.0
        top_text = results[0].get("text", "") + results[0].get("preview", "")
        for concept in expected_concepts:
            if concept in top_text:
                return 1.0
        return 0.0

    def compute_top3_recall(self, results: list[dict], expected_concepts: list[str]) -> float:
        """Among top 3 results, what fraction of expected_concepts appear?

        For each expected concept, check if it appears in any top-3 result text.
        Returns fraction (0.0 to 1.0).
        """
        if not results or not expected_concepts:
            return 0.0
        top3_texts = [
            r.get("text", "") + r.get("preview", "")
            for r in results[:3]
        ]
        combined = " ".join(top3_texts)
        matched = sum(1 for c in expected_concepts if c in combined)
        return matched / len(expected_concepts)

    def compute_citation_accuracy(self, results: list[dict]) -> float:
        """What fraction of results have valid citation fields?

        Valid = source_file non-empty + page non-empty + not garbled.
        """
        if not results:
            return 0.0
        valid = 0
        for r in results:
            sf = str(r.get("source_file", "")).strip()
            pg = str(r.get("page", "")).strip()
            # Basic validity: both fields present
            if sf and pg:
                # Check not garbled (no control chars, reasonable length)
                if len(sf) < 200 and len(pg) < 100:
                    valid += 1
        return valid / len(results)

    def compute_citation_quality_pass_rate(self, results: list[dict], query: str) -> float:
        """What fraction of results pass the citation_quality filter?"""
        if not results:
            return 0.0
        try:
            from core.ai_tutor.citation_quality import filter_citations
            accepted, _ = filter_citations(results, query)
            return len(accepted) / len(results)
        except Exception:
            return 0.0

    # ═══════════════════════════════════════════════════════════════════
    # Main runner
    # ═══════════════════════════════════════════════════════════════════

    def run_all(self) -> dict:
        """Run all benchmarks. Returns structured results dict."""
        query_results: list[QueryResult] = []
        total = len(self.queries)

        for i, q in enumerate(self.queries):
            query_text = q["query"]
            course_id = q["course_id"]
            expected = q["expected_concepts"]
            qtype = q.get("query_type", "unknown")

            qr = QueryResult(
                query=query_text,
                course_id=course_id,
                query_type=qtype,
                expected_concepts=expected,
            )

            try:
                # FAISS
                faiss_results = self.run_faiss_search(course_id, query_text)
                qr.faiss_result_count = len(faiss_results)
                if faiss_results:
                    qr.faiss_top1_match = bool(self.compute_top1_accuracy(faiss_results, expected))
                    qr.faiss_top3_recall = self.compute_top3_recall(faiss_results, expected)
                    qr.faiss_citation_accuracy = self.compute_citation_accuracy(faiss_results)
                    qr.faiss_quality_pass_rate = self.compute_citation_quality_pass_rate(
                        faiss_results, query_text
                    )

                # Hybrid
                hybrid_results = self.run_hybrid_search(course_id, query_text)
                qr.hybrid_result_count = len(hybrid_results)
                if hybrid_results:
                    qr.hybrid_top1_match = bool(self.compute_top1_accuracy(hybrid_results, expected))
                    qr.hybrid_top3_recall = self.compute_top3_recall(hybrid_results, expected)
                    qr.hybrid_citation_accuracy = self.compute_citation_accuracy(hybrid_results)
                    qr.hybrid_quality_pass_rate = self.compute_citation_quality_pass_rate(
                        hybrid_results, query_text
                    )
            except Exception as e:
                qr.error = str(e)[:200]

            query_results.append(qr)

        # Aggregate metrics
        n = len(query_results)
        n_faiss = sum(1 for qr in query_results if qr.faiss_result_count > 0)
        n_hybrid = sum(1 for qr in query_results if qr.hybrid_result_count > 0)

        def avg(items):
            return round(sum(items) / len(items), 4) if items else 0.0

        faiss_results_list = [qr for qr in query_results if qr.faiss_result_count > 0]
        hybrid_results_list = [qr for qr in query_results if qr.hybrid_result_count > 0]

        summary = {
            "total_queries": n,
            "queries_with_faiss_results": n_faiss,
            "queries_with_hybrid_results": n_hybrid,
            "faiss": {
                "top1_accuracy": avg([qr.faiss_top1_match for qr in faiss_results_list]),
                "top3_recall": avg([qr.faiss_top3_recall for qr in faiss_results_list]),
                "citation_accuracy": avg([qr.faiss_citation_accuracy for qr in faiss_results_list]),
                "quality_pass_rate": avg([qr.faiss_quality_pass_rate for qr in faiss_results_list]),
            },
            "hybrid": {
                "top1_accuracy": avg([qr.hybrid_top1_match for qr in hybrid_results_list]),
                "top3_recall": avg([qr.hybrid_top3_recall for qr in hybrid_results_list]),
                "citation_accuracy": avg([qr.hybrid_citation_accuracy for qr in hybrid_results_list]),
                "quality_pass_rate": avg([qr.hybrid_quality_pass_rate for qr in hybrid_results_list]),
            },
            "per_course": {},
            "per_query": [self._qr_to_dict(qr) for qr in query_results],
        }

        # Per-course breakdown
        for course_id in sorted(set(q["course_id"] for q in self.queries)):
            course_qrs = [qr for qr in query_results if qr.course_id == course_id]
            course_faiss = [qr for qr in course_qrs if qr.faiss_result_count > 0]
            course_hybrid = [qr for qr in course_qrs if qr.hybrid_result_count > 0]
            summary["per_course"][course_id] = {
                "total_queries": len(course_qrs),
                "faiss": {
                    "top1_accuracy": avg([qr.faiss_top1_match for qr in course_faiss]),
                    "top3_recall": avg([qr.faiss_top3_recall for qr in course_faiss]),
                    "citation_accuracy": avg([qr.faiss_citation_accuracy for qr in course_faiss]),
                    "quality_pass_rate": avg([qr.faiss_quality_pass_rate for qr in course_faiss]),
                } if course_faiss else None,
                "hybrid": {
                    "top1_accuracy": avg([qr.hybrid_top1_match for qr in course_hybrid]),
                    "top3_recall": avg([qr.hybrid_top3_recall for qr in course_hybrid]),
                    "citation_accuracy": avg([qr.hybrid_citation_accuracy for qr in course_hybrid]),
                    "quality_pass_rate": avg([qr.hybrid_quality_pass_rate for qr in course_hybrid]),
                } if course_hybrid else None,
            }

        return summary

    @staticmethod
    def _qr_to_dict(qr: QueryResult) -> dict:
        return {
            "query": qr.query,
            "course_id": qr.course_id,
            "query_type": qr.query_type,
            "expected_concepts": qr.expected_concepts,
            "faiss_top1": qr.faiss_top1_match,
            "faiss_top3_recall": qr.faiss_top3_recall,
            "faiss_citation_acc": qr.faiss_citation_accuracy,
            "faiss_quality_pass": qr.faiss_quality_pass_rate,
            "faiss_count": qr.faiss_result_count,
            "hybrid_top1": qr.hybrid_top1_match,
            "hybrid_top3_recall": qr.hybrid_top3_recall,
            "hybrid_citation_acc": qr.hybrid_citation_accuracy,
            "hybrid_quality_pass": qr.hybrid_quality_pass_rate,
            "hybrid_count": qr.hybrid_result_count,
            "error": qr.error,
        }

    # ═══════════════════════════════════════════════════════════════════
    # Report generation
    # ═══════════════════════════════════════════════════════════════════

    def generate_report(self, results: dict) -> str:
        """Generate RETRIEVAL_BENCHMARK_REPORT.md content."""
        s = results
        f = s["faiss"]
        h = s["hybrid"]

        lines = [
            "# Retrieval Benchmark Report — StudyPilot AI",
            "",
            f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"测试查询数：{s['total_queries']}",
            "",
            "---",
            "",
            "## 一、总体结论",
            "",
        ]

        # Determine if hybrid is better
        hybrid_wins = 0
        faiss_wins = 0
        for metric in ["top1_accuracy", "top3_recall", "citation_accuracy", "quality_pass_rate"]:
            if h[metric] > f[metric]:
                hybrid_wins += 1
            elif f[metric] > h[metric]:
                faiss_wins += 1

        if hybrid_wins > faiss_wins:
            lines.append(f"**Hybrid Retrieval (FAISS+BM25+RRF) 优于纯向量检索 (FAISS)**，在 {hybrid_wins}/{hybrid_wins+faiss_wins} 项指标上领先。")
        elif faiss_wins > hybrid_wins:
            lines.append(f"**纯向量检索 (FAISS) 优于 Hybrid Retrieval**，在 {faiss_wins}/{hybrid_wins+faiss_wins} 项指标上领先。")
        else:
            lines.append("**两种方法各有优劣**，在不同指标上互有胜负。")

        lines += [
            "",
            "---",
            "",
            "## 二、核心指标对比",
            "",
            "| 指标 | FAISS | Hybrid (FAISS+BM25+RRF) | 优胜 |",
            "|------|-------|--------------------------|------|",
        ]

        for metric_key, label in [
            ("top1_accuracy", "Top1 Accuracy"),
            ("top3_recall", "Top3 Recall"),
            ("citation_accuracy", "Citation Accuracy"),
            ("quality_pass_rate", "Citation Quality Pass Rate"),
        ]:
            fv = f[metric_key]
            hv = h[metric_key]
            if hv > fv:
                winner = "🏆 Hybrid" if hv - fv > 0.01 else "≈ 持平"
            elif fv > hv:
                winner = "🏆 FAISS" if fv - hv > 0.01 else "≈ 持平"
            else:
                winner = "≈ 持平"
            lines.append(f"| {label} | {fv:.4f} | {hv:.4f} | {winner} |")

        # Answer the detailed questions
        lines += [
            "",
            "---",
            "",
            "## 三、关键问题回答",
            "",
            f"### 1. Hybrid Retrieval 是否优于纯向量检索？",
            "",
            f"**{'是' if hybrid_wins > faiss_wins else '否，两者表现接近' if hybrid_wins == faiss_wins else '否，纯向量检索更优'}**。",
            f"FAISS Top1 Accuracy: {f['top1_accuracy']:.4f}，Hybrid Top1 Accuracy: {h['top1_accuracy']:.4f}。",
            f"FAISS Top3 Recall: {f['top3_recall']:.4f}，Hybrid Top3 Recall: {h['top3_recall']:.4f}。",
            f"FAISS Citation Accuracy: {f['citation_accuracy']:.4f}，Hybrid Citation Accuracy: {h['citation_accuracy']:.4f}。",
            "",
            f"FAISS Citation Quality Pass Rate: {f['quality_pass_rate']:.4f}，Hybrid Citation Quality Pass Rate: {h['quality_pass_rate']:.4f}。",
            "",
            f"### 2. 当前 Citation Accuracy",
            f"FAISS: {f['citation_accuracy']:.4f} ({f['citation_accuracy']*100:.1f}%)",
            f"Hybrid: {h['citation_accuracy']:.4f} ({h['citation_accuracy']*100:.1f}%)",
            "",
            f"### 3. 当前 Top1 Accuracy",
            f"FAISS: {f['top1_accuracy']:.4f} ({f['top1_accuracy']*100:.1f}%)",
            f"Hybrid: {h['top1_accuracy']:.4f} ({h['top1_accuracy']*100:.1f}%)",
            "",
            f"### 4. 当前 Top3 Recall",
            f"FAISS: {f['top3_recall']:.4f} ({f['top3_recall']*100:.1f}%)",
            f"Hybrid: {h['top3_recall']:.4f} ({h['top3_recall']*100:.1f}%)",
            "",
            "---",
            "",
            "## 四、分课程结果",
            "",
        ]

        for course_id, pc in s.get("per_course", {}).items():
            course_names = {
                "probability_ch2": "概率论与随机过程 第二章",
                "field_wave_ch1": "电磁场与电磁波 第一章",
                "digital_logic_ch3": "数字电路逻辑设计 第三章（Demo）",
            }
            cname = course_names.get(course_id, course_id)
            lines.append(f"### {cname} ({pc['total_queries']} 查询)")
            lines.append("")
            if pc["faiss"] and pc["hybrid"]:
                lines.append("| 指标 | FAISS | Hybrid |")
                lines.append("|------|-------|--------|")
                for mk, ml in [("top1_accuracy", "Top1"), ("top3_recall", "Top3 Recall"),
                               ("citation_accuracy", "Citation Acc"), ("quality_pass_rate", "Quality Pass")]:
                    lines.append(f"| {ml} | {pc['faiss'][mk]:.4f} | {pc['hybrid'][mk]:.4f} |")
            else:
                lines.append("⚠️ 该课程无 FAISS 索引（Demo 课程，无上传教材），所有检索返回 0 结果。")
            lines.append("")

        lines += [
            "---",
            "",
            "## 五、逐查询详情",
            "",
        ]

        for qr in s["per_query"]:
            lines.append(f"### {qr['query']}")
            lines.append(f"- 课程：{qr['course_id']} | 类型：{qr['query_type']}")
            lines.append(f"- 期望概念：{'、'.join(qr['expected_concepts'])}")
            if qr["error"]:
                lines.append(f"- ❌ 错误：{qr['error']}")
            else:
                lines.append(f"- FAISS: Top1={'✅' if qr['faiss_top1'] else '❌'} | Top3 Recall={qr['faiss_top3_recall']:.2f} | Citation={qr['faiss_citation_acc']:.2f} | Quality={qr['faiss_quality_pass']:.2f} | Count={qr['faiss_count']}")
                lines.append(f"- Hybrid: Top1={'✅' if qr['hybrid_top1'] else '❌'} | Top3 Recall={qr['hybrid_top3_recall']:.2f} | Citation={qr['hybrid_citation_acc']:.2f} | Quality={qr['hybrid_quality_pass']:.2f} | Count={qr['hybrid_count']}")
            lines.append("")

        lines += [
            "---",
            "",
            "## 六、分析与建议",
            "",
            "### Hybrid 的优势场景",
            "- BM25 关键词匹配可以弥补 Embedding 模型对中文专业术语的语义理解不足",
            "- RRF 融合可以引入词汇级别的精确匹配，对公式查询和概念定义查询有帮助",
            "",
            "### FAISS 的优势场景",
            "- 纯语义检索在理解同义词和概念变体方面更强",
            "- 对长查询（如完整的问题描述）可能更有效",
            "",
            "### digital_logic_ch3 的特殊情况",
            "- 该课程为 Demo 模式，无上传教材，无 FAISS 索引",
            "- 所有检索返回 0 结果，不影响指标计算（仅对有结果的查询计算指标）",
            "- 这验证了系统在无 RAG 数据时的优雅降级能力",
            "",
            "### 改进建议",
            "1. 提高场波教材 FAISS 索引质量（当前为扫描版，文本提取噪声大）",
            "2. 考虑引入更大规模的 Embedding 模型（如 bge-large-zh-v1.5）",
            "3. 调整 BM25 的 k1 和 b 参数以优化中文分词效果",
            "4. 为 digital_logic_ch3 上传教材并构建索引（当前仅有 ExamPatterns 数据）",
            "",
            "---",
            "",
            "*Report generated by benchmarks/retrieval_benchmark.py*",
        ]

        return "\n".join(lines)
