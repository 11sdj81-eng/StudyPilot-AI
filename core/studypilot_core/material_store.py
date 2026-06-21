"""MaterialStore — file-safe material management with hash dedup and metadata."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

MATERIALS_DIR = Path("data/materials")


class MaterialStore:
    """Safe material storage with hash-based dedup and path sanitization."""

    ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".docx", ".png", ".jpg",
                          ".jpeg", ".txt", ".md", ".zip"}
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

    def __init__(self, core=None):
        self.core = core
        MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

    def ingest(self, file_path: str | Path, course_id: str = "",
               workspace_id: str = "") -> dict:
        """Ingest a file: hash dedup, safe copy, record metadata."""
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": "FILE_NOT_FOUND", "path": str(file_path)}

        # Safety checks
        ext = file_path.suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return {"error": "UNSUPPORTED_TYPE", "ext": ext}

        size = file_path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            return {"error": "FILE_TOO_LARGE", "size_mb": round(size / 1024 / 1024, 1)}

        # Hash dedup
        file_hash = self._hash_file(file_path)
        existing = self._find_by_hash(file_hash)
        if existing:
            return {"status": "duplicate", "existing_id": existing["resource_id"],
                    "hash": file_hash}

        # Safe filename
        safe_name = self._safe_filename(file_path.name)
        resource_id = f"res_{uuid.uuid4().hex[:8]}"

        # Copy to materials store
        dest_dir = MATERIALS_DIR / resource_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / safe_name
        shutil.copy2(file_path, dest_path)

        # Record metadata
        metadata = {
            "resource_id": resource_id,
            "original_name": file_path.name,
            "safe_name": safe_name,
            "ext": ext,
            "size": size,
            "hash": file_hash,
            "course_id": course_id,
            "workspace_id": workspace_id,
            "ingested_at": datetime.now().isoformat(),
            "path": str(dest_path.resolve()),
        }
        meta_path = dest_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        # Record in workspace
        if workspace_id and self.core:
            self.core.workspace.add_material(workspace_id, resource_id)

        return {"status": "ingested", "resource_id": resource_id, **metadata}

    def get(self, resource_id: str) -> dict | None:
        """Get material metadata."""
        path = MATERIALS_DIR / resource_id / "metadata.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def delete(self, resource_id: str) -> dict:
        """Delete a material and its files."""
        dest_dir = MATERIALS_DIR / resource_id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
            return {"status": "deleted", "resource_id": resource_id}
        return {"status": "not_found", "resource_id": resource_id}

    def list_by_course(self, course_id: str) -> list[dict]:
        """List all materials for a course."""
        materials = []
        for d in MATERIALS_DIR.iterdir():
            if d.is_dir():
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("course_id") == course_id:
                        materials.append(meta)
        return materials

    def _hash_file(self, path: Path) -> str:
        """SHA256 hash of file contents."""
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _find_by_hash(self, file_hash: str) -> dict | None:
        """Find existing material by hash."""
        for d in MATERIALS_DIR.iterdir():
            if d.is_dir():
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("hash") == file_hash:
                        return meta
        return None

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Sanitize filename for safe storage."""
        import re
        name = name.replace(" ", "_")
        safe = re.sub(r'[<>:"/\\|?*]', '', name)
        return safe[:200] if len(safe) > 200 else safe
