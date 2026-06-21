"""Small file-hash cache for PDF 2.0 structured content."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CACHE_DIR = Path("data/cache/pdf_content_v2")


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_key(paths: list[str | Path]) -> str:
    payload = []
    for path in sorted(Path(p) for p in paths if Path(p).exists()):
        payload.append({"path": str(path), "sha256": file_sha256(path)})
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cache(key: str) -> dict[str, Any] | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(key: str, data: dict[str, Any]) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
