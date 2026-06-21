"""Hybrid Retrieval: FAISS semantic + BM25 keyword → merge → dedup → rerank → top_k.

Every answer returns citations: source_file, page, chunk_id, score, preview.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

from core.config import VECTOR_DIR

# ═══════════════════════════════════════════════════════════════════════════
# BM25 Scorer
# ═══════════════════════════════════════════════════════════════════════════


class BM25Scorer:
    """Lightweight BM25 using numpy. No external deps beyond numpy.

    Tokenizes Chinese text via character bigrams for keyword-level matching.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._docs: list[str] = []
        self._tokens_per_doc: list[list[str]] = []
        self._doc_len: np.ndarray | None = None
        self._avgdl: float = 0.0
        self._N: int = 0
        self._df: Counter = Counter()
        self._idf: dict[str, float] = {}

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text for BM25: character bigrams cover Chinese keyword matching."""
        # Clean whitespace
        text = re.sub(r"\s+", " ", text.strip())
        # Character bigrams — good for matching Chinese terms
        bigrams = [text[i : i + 2] for i in range(len(text) - 1)]
        # Also keep longer n-grams for term matching
        trigrams = [text[i : i + 3] for i in range(len(text) - 2)]
        # Individual chars
        chars = list(text)
        return bigrams + trigrams + chars

    def index(self, documents: list[str]) -> None:
        """Build BM25 index from document texts."""
        self._docs = documents
        self._N = len(documents)
        self._tokens_per_doc = [self._tokenize(doc) for doc in documents]
        self._doc_len = np.array([len(tokens) for tokens in self._tokens_per_doc], dtype=np.float64)
        self._avgdl = float(self._doc_len.mean()) if self._N > 0 else 0.0

        # Document frequency
        self._df = Counter()
        for tokens in self._tokens_per_doc:
            unique = set(tokens)
            for token in unique:
                self._df[token] += 1

        # IDF
        self._idf = {}
        for token, df in self._df.items():
            self._idf[token] = math.log((self._N - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        """Search for query, return list of (doc_index, score) sorted by score descending."""
        if self._N == 0 or self._doc_len is None:
            return []

        query_tokens = self._tokenize(query)
        scores = np.zeros(self._N, dtype=np.float64)

        for token in query_tokens:
            if token not in self._idf:
                continue
            idf = self._idf[token]

            # Compute TF per document
            for i, tokens in enumerate(self._tokens_per_doc):
                tf = tokens.count(token)
                if tf == 0:
                    continue
                doc_len = float(self._doc_len[i])
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * doc_len / max(self._avgdl, 1.0))
                scores[i] += idf * numerator / denominator

        # Get top_k indices
        if top_k >= self._N:
            top_indices = list(range(self._N))
        else:
            top_indices = np.argpartition(-scores, top_k)[:top_k]
        top_indices = top_indices[np.argsort(-scores[top_indices])]

        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]


# ═══════════════════════════════════════════════════════════════════════════
# Reciprocal Rank Fusion
# ═══════════════════════════════════════════════════════════════════════════


def _rrf_merge(
    faiss_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Merge two ranked lists via Reciprocal Rank Fusion.

    RRF score = Σ 1/(k + rank_in_list) for each list the chunk appears in.
    """
    rrf_scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}

    for rank, chunk in enumerate(faiss_results, start=1):
        cid = chunk.get("chunk_id", "")
        if not cid:
            continue
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank)
        # Preserve FAISS score
        chunk_copy = dict(chunk)
        chunk_copy["faiss_score"] = chunk.get("score", 0.0)
        chunk_copy["faiss_rank"] = rank
        if cid not in chunk_map:
            chunk_map[cid] = chunk_copy

    for rank, chunk in enumerate(bm25_results, start=1):
        cid = chunk.get("chunk_id", "")
        if not cid:
            continue
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank)
        if cid not in chunk_map:
            chunk_copy = dict(chunk)
            chunk_copy["bm25_score"] = chunk.get("score", 0.0)
            chunk_copy["bm25_rank"] = rank
            chunk_map[cid] = chunk_copy
        else:
            chunk_map[cid]["bm25_score"] = chunk.get("score", 0.0)
            chunk_map[cid]["bm25_rank"] = rank

    # Sort by RRF score descending
    merged = []
    for cid, rrf_score in sorted(rrf_scores.items(), key=lambda x: -x[1]):
        chunk = chunk_map[cid]
        chunk["rrf_score"] = round(rrf_score, 6)
        chunk["score"] = round(rrf_score, 4)  # Use RRF as primary score
        merged.append(chunk)

    return merged


# ═══════════════════════════════════════════════════════════════════════════
# Main Hybrid Search
# ═══════════════════════════════════════════════════════════════════════════


def hybrid_search(
    course_id: str,
    query: str,
    top_k: int = 5,
    faiss_candidate_k: int = 20,
    bm25_candidate_k: int = 20,
) -> list[dict]:
    """Hybrid retrieval: FAISS + BM25 → merge (RRF) → re-rank → top_k.

    Returns list of dicts with citation fields:
        chunk_id, source_file, page, score, preview, source_type

    Args:
        course_id: Course identifier (e.g. 'probability_ch2')
        query: User query in natural language
        top_k: Number of final results to return
        faiss_candidate_k: FAISS candidate pool size
        bm25_candidate_k: BM25 candidate pool size

    Returns:
        List of citation dicts, each with:
        - chunk_id: unique chunk identifier
        - source_file: original file name
        - page: page number (if available)
        - score: RRF combined score
        - preview: first 150 chars of chunk text
        - text: full chunk text
        - faiss_score, bm25_score, faiss_rank, bm25_rank (if available)
    """
    meta_path = VECTOR_DIR / course_id / "chunks.json"
    backend_path = VECTOR_DIR / course_id / "backend.json"

    if not meta_path.exists() or not backend_path.exists():
        return []

    import json

    try:
        all_chunks = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    if not all_chunks:
        return []

    # ── 1. FAISS semantic search ──
    faiss_results: list[dict] = []
    try:
        from core.vector_store import CourseVectorStore
        store = CourseVectorStore(course_id)
        faiss_results = store.search(query, top_k=min(faiss_candidate_k, len(all_chunks)))
    except Exception:
        pass

    # ── 2. BM25 keyword search ──
    bm25_results: list[dict] = []
    try:
        texts = [chunk.get("text", "") for chunk in all_chunks]
        bm25 = BM25Scorer()
        bm25.index(texts)
        bm25_hits = bm25.search(query, top_k=min(bm25_candidate_k, len(all_chunks)))
        for idx, score in bm25_hits:
            if 0 <= idx < len(all_chunks):
                chunk = dict(all_chunks[idx])
                chunk["score"] = round(score, 4)
                bm25_results.append(chunk)
    except Exception:
        pass

    # ── 3. Merge via RRF ──
    if faiss_results and bm25_results:
        merged = _rrf_merge(faiss_results, bm25_results)
    elif faiss_results:
        merged = faiss_results
    elif bm25_results:
        merged = bm25_results
    else:
        return []

    # ── 4. Deduplicate by chunk_id (already done by RRF merge, but be safe) ──
    seen = set()
    deduped = []
    for chunk in merged:
        cid = chunk.get("chunk_id", "")
        if cid and cid not in seen:
            seen.add(cid)
            deduped.append(chunk)

    # ── 5. Format citations ──
    results = []
    for chunk in deduped[:top_k]:
        text = chunk.get("text", "")
        citation = {
            "chunk_id": chunk.get("chunk_id", ""),
            "source_file": chunk.get("filename", chunk.get("source", "")),
            "page": chunk.get("page", ""),
            "score": chunk.get("score", 0.0),
            "preview": text[:150].replace("\n", " ").strip(),
            "text": text,
            "resource_type": chunk.get("resource_type", ""),
            "resource_id": chunk.get("resource_id", ""),
        }
        # Preserve per-backend scores for diagnostics
        if "faiss_score" in chunk:
            citation["faiss_score"] = chunk["faiss_score"]
            citation["faiss_rank"] = chunk.get("faiss_rank", -1)
        if "bm25_score" in chunk:
            citation["bm25_score"] = chunk["bm25_score"]
            citation["bm25_rank"] = chunk.get("bm25_rank", -1)
        if "rrf_score" in chunk:
            citation["rrf_score"] = chunk["rrf_score"]

        results.append(citation)

    return results
