"""Vector store with FAISS index integrity — SP-008 fix.

remove_chunks_by_resource() now rebuilds the FAISS index immediately.
No ghost chunks can survive resource deletion.
"""

import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.config import EMBEDDING_MODEL_NAME, VECTOR_DIR

_MODEL = None


def get_model():
    """返回 SentenceTransformer 单例，整个进程只加载一次模型。"""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _MODEL


class CourseVectorStore:
    def __init__(self, course_id: str):
        self.course_id = course_id
        self.store_dir = VECTOR_DIR / course_id
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.store_dir / "chunks.json"
        self.backend_path = self.store_dir / "backend.json"
        self.tfidf_path = self.store_dir / "tfidf.pkl"
        self.faiss_index_path = self.store_dir / "index.faiss"

    def build(self, chunks: list[dict]) -> str:
        if not chunks:
            raise ValueError("没有可写入向量库的文本块。")
        self.meta_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        texts = [chunk["text"] for chunk in chunks]
        try:
            from faiss import IndexFlatIP, write_index

            model = get_model()
            embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            embeddings = np.asarray(embeddings, dtype="float32")
            index = IndexFlatIP(embeddings.shape[1])
            index.add(embeddings)
            write_index(index, str(self.faiss_index_path))
            self.backend_path.write_text(
                json.dumps({"backend": "faiss", "model": EMBEDDING_MODEL_NAME}, ensure_ascii=False),
                encoding="utf-8",
            )
            return "faiss"
        except Exception as exc:
            vectorizer = TfidfVectorizer(max_features=8000)
            matrix = vectorizer.fit_transform(texts)
            with self.tfidf_path.open("wb") as file:
                pickle.dump({"vectorizer": vectorizer, "matrix": matrix}, file)
            self.backend_path.write_text(
                json.dumps({"backend": "tfidf", "reason": str(exc)}, ensure_ascii=False),
                encoding="utf-8",
            )
            return "tfidf"

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.meta_path.exists() or not self.backend_path.exists():
            return []
        chunks = json.loads(self.meta_path.read_text(encoding="utf-8"))
        if not chunks:
            return []
        backend = json.loads(self.backend_path.read_text(encoding="utf-8")).get("backend")
        if backend == "faiss" and self.faiss_index_path.exists():
            try:
                from faiss import read_index

                model = get_model()
                query_vec = model.encode([query], normalize_embeddings=True)
                query_vec = np.asarray(query_vec, dtype="float32")
                faiss_index = read_index(str(self.faiss_index_path))
                # Guard: if index size != chunks count, index is stale
                if faiss_index.ntotal != len(chunks):
                    # Auto-rebuild to fix the mismatch
                    return self._rebuild_and_search(chunks, query, top_k)
                scores, indexes = faiss_index.search(query_vec, min(top_k, len(chunks)))
                return [
                    {**chunks[int(idx)], "score": float(scores[0][rank])}
                    for rank, idx in enumerate(indexes[0])
                    if 0 <= idx < len(chunks)
                ]
            except Exception:
                pass
        if self.tfidf_path.exists():
            with self.tfidf_path.open("rb") as file:
                saved = pickle.load(file)
            query_vec = saved["vectorizer"].transform([query])
            scores = cosine_similarity(query_vec, saved["matrix"]).ravel()
            indexes = scores.argsort()[::-1][:top_k]
            return [{**chunks[int(idx)], "score": float(scores[int(idx)])} for idx in indexes]
        return []

    def _rebuild_and_search(self, chunks: list[dict], query: str, top_k: int) -> list[dict]:
        """Emergency rebuild when FAISS index is out of sync with chunks."""
        try:
            self.build(chunks)
            return self.search(query, top_k)
        except Exception:
            return []

    def remove_chunks_by_resource(self, resource_id: str) -> list[dict]:
        """Delete all chunks for a resource AND rebuild the FAISS index immediately.

        SP-008 fix: previously only removed from chunks.json, leaving ghost vectors
        in the FAISS index. Now rebuilds the index after every deletion.
        """
        if not self.meta_path.exists():
            return []
        all_chunks = json.loads(self.meta_path.read_text(encoding="utf-8"))
        remaining = [c for c in all_chunks if c.get("resource_id") != resource_id]
        removed_count = len(all_chunks) - len(remaining)
        if removed_count > 0:
            # Write updated metadata
            self.meta_path.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
            # Rebuild FAISS index to remove ghost vectors
            if remaining:
                try:
                    self.build(remaining)
                except Exception:
                    pass  # metadata is already updated; index will self-heal on next search
            else:
                # No chunks left — remove index files
                self._clean_index_files()
        return remaining

    def _clean_index_files(self) -> None:
        """Remove all index files for this course."""
        for p in [self.faiss_index_path, self.tfidf_path]:
            if p.exists():
                p.unlink()

    def integrity_check(self) -> dict:
        """Check that FAISS index and chunks.json are in sync. Returns report."""
        report = {
            "course_id": self.course_id,
            "resource_count": 0,
            "chunk_count": 0,
            "vector_count": 0,
            "orphan_vector_count": 0,
            "index_exists": False,
            "in_sync": False,
        }
        if not self.meta_path.exists():
            return report

        try:
            chunks = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return report

        report["chunk_count"] = len(chunks)
        resource_ids = set(c.get("resource_id", "") for c in chunks)
        report["resource_count"] = len(resource_ids)

        if self.faiss_index_path.exists():
            report["index_exists"] = True
            try:
                from faiss import read_index
                faiss_index = read_index(str(self.faiss_index_path))
                report["vector_count"] = faiss_index.ntotal
                report["orphan_vector_count"] = max(0, faiss_index.ntotal - len(chunks))
                report["in_sync"] = report["orphan_vector_count"] == 0
            except Exception:
                report["orphan_vector_count"] = -1  # unreadable
        else:
            report["vector_count"] = 0
            report["in_sync"] = len(chunks) == 0  # sync if both are empty

        return report


# ═══════════════════════════════════════════════════════════════════════════
# Vector Garbage Collector
# ═══════════════════════════════════════════════════════════════════════════

class VectorGarbageCollector:
    """Scan all course vector stores and repair orphan vectors on startup."""

    def __init__(self):
        self.store_dir = VECTOR_DIR

    def scan_all(self) -> list[dict]:
        """Scan all courses, return integrity reports, auto-repair orphans."""
        reports = []
        if not self.store_dir.exists():
            return reports

        for course_dir in sorted(self.store_dir.iterdir()):
            if not course_dir.is_dir():
                continue
            course_id = course_dir.name
            store = CourseVectorStore(course_id)
            report = store.integrity_check()
            reports.append(report)

            # Auto-repair: if index has more vectors than chunks, rebuild
            if report["orphan_vector_count"] > 0 and report["chunk_count"] > 0:
                try:
                    chunks = json.loads(store.meta_path.read_text(encoding="utf-8"))
                    store.build(chunks)
                    report["auto_repaired"] = True
                    report["orphan_vector_count"] = 0
                    report["in_sync"] = True
                except Exception:
                    report["auto_repaired"] = False
            elif report["chunk_count"] == 0 and report["vector_count"] > 0:
                # Orphan index with no chunks — clean up
                store._clean_index_files()
                report["auto_repaired"] = True
                report["vector_count"] = 0
                report["in_sync"] = True

        return reports

    def generate_report(self) -> dict:
        """Generate vector_integrity_report.json."""
        reports = self.scan_all()
        total_orphans = sum(r.get("orphan_vector_count", 0) for r in reports if r.get("orphan_vector_count", 0) > 0)
        return {
            "courses_scanned": len(reports),
            "total_orphan_vector_count": total_orphans,
            "all_clean": total_orphans == 0,
            "course_reports": reports,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def rebuild_course_store(course_id: str, chunks: list[dict]) -> str:
    return CourseVectorStore(course_id).build(chunks)


def remove_resource_chunks(course_id: str, resource_id: str) -> list[dict]:
    """Delete chunks for a resource AND rebuild FAISS index. No ghost vectors."""
    return CourseVectorStore(course_id).remove_chunks_by_resource(resource_id)


def run_garbage_collector() -> dict:
    """Run vector garbage collector and return integrity report."""
    gc = VectorGarbageCollector()
    return gc.generate_report()
