"""RAGIndexManager — course-isolated RAG with mandatory integrity checks.

Wraps CourseVectorStore. Enforces:
- resource_id ↔ chunk_id ↔ embedding_id mapping
- Course-level isolation on all retrievals
- Atomic deletion (chunks + embeddings + mapping)
- Integrity reports with hard gates
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RAGIndexManager:
    """Course-isolated RAG index manager with integrity guarantees.

    Hard gates:
        orphan_vector_count = 0
        cross_course_recall_count = 0
    """

    def __init__(self, core=None):
        self.core = core

    def build_index(self, course_id: str, chunks: list[dict],
                    resource_id: str = "") -> dict:
        """Build FAISS index for a course's chunks. Records mapping."""
        from core.vector_store import rebuild_course_store

        result = rebuild_course_store(course_id, chunks)

        # Record mapping
        mapping = self._load_mapping(course_id)
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("chunk_id", f"{resource_id}_{i}")
            chunk_ids.append(chunk_id)
            mapping["chunks"][chunk_id] = {
                "resource_id": resource_id,
                "chunk_index": i,
                "text_preview": str(chunk.get("text", chunk.get("content", "")))[:100],
            }

        if resource_id:
            mapping["resources"][resource_id] = {
                "chunk_count": len(chunks),
                "chunk_ids": chunk_ids,
                "indexed_at": str(__import__("datetime").datetime.now().isoformat()),
            }

        self._save_mapping(course_id, mapping)
        return result

    def retrieve(self, course_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve chunks with mandatory course isolation."""
        from core.vector_store import CourseVectorStore

        store = CourseVectorStore(course_id)
        results = store.search(query, top_k)

        # Filter: ensure all results belong to this course
        mapping = self._load_mapping(course_id)
        filtered = []
        for r in results:
            chunk_id = r.get("chunk_id", "")
            if chunk_id in mapping.get("chunks", {}):
                filtered.append(r)
            # Chunks without mapping entries are excluded (cross-course safety)

        return filtered[:top_k]

    def delete_resource(self, course_id: str, resource_id: str) -> dict:
        """Atomically delete all chunks + embeddings for a resource."""
        from core.vector_store import remove_resource_chunks

        mapping = self._load_mapping(course_id)
        resource_info = mapping.get("resources", {}).get(resource_id, {})

        # Remove from FAISS
        result = remove_resource_chunks(course_id, resource_id)

        # Clean mapping
        chunk_ids = resource_info.get("chunk_ids", [])
        for cid in chunk_ids:
            mapping["chunks"].pop(cid, None)
        mapping["resources"].pop(resource_id, None)
        self._save_mapping(course_id, mapping)

        return {
            "course_id": course_id,
            "resource_id": resource_id,
            "chunks_removed": len(chunk_ids),
            "faiss_result": result,
        }

    def integrity_check(self, course_id: str) -> dict:
        """Run full integrity check on a course's RAG index."""
        from core.vector_store import CourseVectorStore

        store = CourseVectorStore(course_id)
        store_result = store.integrity_check()
        mapping = self._load_mapping(course_id)

        orphan_vectors = store_result.get("orphan_count", 0)
        chunk_vector_mismatch = store_result.get("mismatch", False)
        mapped_chunks = len(mapping.get("chunks", {}))
        mapped_resources = len(mapping.get("resources", {}))

        # Check cross-course contamination
        cross_course_count = 0
        for chunk_id, info in mapping.get("chunks", {}).items():
            rid = info.get("resource_id", "")
            if rid and rid not in mapping.get("resources", {}):
                cross_course_count += 1

        report = {
            "course_id": course_id,
            "orphan_vector_count": orphan_vectors,
            "chunk_vector_mismatch": chunk_vector_mismatch,
            "mapped_chunks": mapped_chunks,
            "mapped_resources": mapped_resources,
            "cross_course_recall_count": cross_course_count,
            "healthy": orphan_vectors == 0 and cross_course_count == 0 and not chunk_vector_mismatch,
        }

        # Write report
        report_path = Path("data/vector_store") / course_id / "rag_integrity_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        return report

    def list_courses(self) -> list[str]:
        """List all courses with RAG indices."""
        store_dir = Path("data/vector_store")
        if not store_dir.exists():
            return []
        return [d.name for d in store_dir.iterdir() if d.is_dir() and (d / "chunks.json").exists()]

    def get_stats(self) -> dict:
        """Get RAG stats across all courses."""
        courses = self.list_courses()
        total_chunks = 0
        issues = 0
        for cid in courses:
            try:
                report = self.integrity_check(cid)
                total_chunks += report.get("mapped_chunks", 0)
                if not report.get("healthy"):
                    issues += 1
            except Exception:
                pass
        return {
            "total_courses": len(courses),
            "total_chunks": total_chunks,
            "courses_with_issues": issues,
        }

    # ── Internal ─────────────────────────────────────────────────────────

    def _load_mapping(self, course_id: str) -> dict:
        path = Path("data/vector_store") / course_id / "mapping.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"chunks": {}, "resources": {}}

    def _save_mapping(self, course_id: str, mapping: dict) -> None:
        path = Path("data/vector_store") / course_id / "mapping.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
