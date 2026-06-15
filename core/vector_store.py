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
        backend = json.loads(self.backend_path.read_text(encoding="utf-8")).get("backend")
        if backend == "faiss" and self.faiss_index_path.exists():
            try:
                from faiss import read_index

                model = get_model()
                query_vec = model.encode([query], normalize_embeddings=True)
                query_vec = np.asarray(query_vec, dtype="float32")
                scores, indexes = read_index(str(self.faiss_index_path)).search(query_vec, top_k)
                return [
                    {**chunks[int(idx)], "score": float(scores[0][rank])}
                    for rank, idx in enumerate(indexes[0])
                    if idx >= 0
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


    def remove_chunks_by_resource(self, resource_id: str) -> list[dict]:
        """删除指定 resource 的所有 chunks，返回剩余的 chunks。"""
        if not self.meta_path.exists():
            return []
        all_chunks = json.loads(self.meta_path.read_text(encoding="utf-8"))
        remaining = [c for c in all_chunks if c.get("resource_id") != resource_id]
        removed_count = len(all_chunks) - len(remaining)
        if removed_count > 0:
            self.meta_path.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
        return remaining


def rebuild_course_store(course_id: str, chunks: list[dict]) -> str:
    return CourseVectorStore(course_id).build(chunks)


def remove_resource_chunks(course_id: str, resource_id: str) -> list[dict]:
    """删除指定 resource 的 chunks 并返回剩余 chunks，供调用方决定是否重建索引。"""
    return CourseVectorStore(course_id).remove_chunks_by_resource(resource_id)
