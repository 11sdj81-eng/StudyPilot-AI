"""StudyPilot v5.2 — DI Worker client for the main project (Python 3.14).

Calls the DI Worker (Python 3.11) via subprocess and reads standard
document.json output.  If the worker fails, falls back gracefully.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.config import ROOT_DIR

WORKER_DIR = ROOT_DIR / "tools" / "document_intelligence_worker"
WORKER_VENV = WORKER_DIR / ".venv-di"
WORKER_PYTHON = WORKER_VENV / "bin" / "python"
PARSE_SCRIPT = WORKER_DIR / "parse_document.py"


def check_worker_available() -> dict[str, Any]:
    """Check if the DI Worker environment is set up."""
    result: dict[str, Any] = {
        "available": False,
        "python_path": str(WORKER_PYTHON),
        "python_version": None,
        "venv_exists": WORKER_VENV.exists(),
        "parse_script_exists": PARSE_SCRIPT.exists(),
        "errors": [],
    }

    if not WORKER_VENV.exists():
        result["errors"].append("Worker venv not found. Run: bash tools/document_intelligence_worker/setup_worker_env.sh")
        return result

    if not PARSE_SCRIPT.exists():
        result["errors"].append("parse_document.py not found in worker directory.")
        return result

    try:
        proc = subprocess.run(
            [str(WORKER_PYTHON), "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            result["python_version"] = proc.stdout.strip() or proc.stderr.strip()
            result["available"] = True
        else:
            result["errors"].append(f"Worker python check failed: {proc.stderr}")
    except FileNotFoundError:
        result["errors"].append(f"Worker python not found at {WORKER_PYTHON}")
    except Exception as e:
        result["errors"].append(str(e))

    return result


def parse_with_worker(
    file_path: str | Path,
    output_dir: str | Path | None = None,
    mode: str = "auto",
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Parse a document using the DI Worker.

    Args:
        file_path: Path to input PDF/PPTX.
        output_dir: Output directory (auto-generated if None).
        mode: One of auto, fallback, paddleocr, marker, mineru, doclayout.
        max_pages: Max pages to process (default 5 for auto, 10 otherwise).

    Returns:
        The document.json content as a dict, or a dict with ``success: False``.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    if output_dir is None:
        slug = file_path.stem[:30].replace(" ", "_")
        output_dir = Path(f"data/parsed/v5_worker/{slug}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if max_pages is None:
        max_pages = 5 if mode == "auto" else 10

    cmd = [
        str(WORKER_PYTHON),
        str(PARSE_SCRIPT),
        "--input", str(file_path),
        "--output", str(output_dir),
        "--mode", mode,
        "--max-pages", str(max_pages),
        "--save-images", "true",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
            cwd=str(WORKER_DIR),
        )

        doc_path = output_dir / "document.json"
        if doc_path.exists():
            doc = json.loads(doc_path.read_text(encoding="utf-8"))
            doc["_worker_stdout"] = proc.stdout[-500:]
            doc["_worker_stderr"] = proc.stderr[-500:]
            doc["_worker_returncode"] = proc.returncode
            return doc
        else:
            return {
                "success": False,
                "error": f"Worker produced no document.json. returncode={proc.returncode}",
                "stdout": proc.stdout[-1000:],
                "stderr": proc.stderr[-1000:],
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Worker timed out (>600s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_to_document_blocks(file_path: str | Path, output_dir: str | Path | None = None, mode: str = "auto") -> list[dict[str, Any]]:
    """Parse a document and return DocumentBlocks for downstream systems."""
    doc = parse_with_worker(file_path, output_dir, mode=mode)
    blocks: list[dict[str, Any]] = []

    if not doc.get("success"):
        return blocks

    for page in doc.get("pages", []):
        for block in page.get("blocks", []):
            blocks.append({
                "block_id": block.get("block_id", ""),
                "block_type": block.get("block_type", "text"),
                "source_file": Path(file_path).name,
                "source_page": page.get("page_number"),
                "parser": doc.get("parser_used", "unknown"),
                "content": block.get("text", ""),
                "bbox": block.get("bbox"),
                "confidence": block.get("confidence", 0.0),
                "image_path": block.get("asset_path", ""),
            })

    return blocks
