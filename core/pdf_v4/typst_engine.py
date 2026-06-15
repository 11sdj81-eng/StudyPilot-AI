"""Typst compilation engine for StudyPilot PDF v4."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def typst_available() -> bool:
    return shutil.which("typst") is not None


def typst_version() -> str:
    if not typst_available():
        return ""
    result = subprocess.run(["typst", "--version"], text=True, capture_output=True, check=False)
    return result.stdout.strip() or result.stderr.strip()


def compile_typst(input_path: str | Path, output_path: str | Path) -> Path:
    src = Path(input_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["typst", "compile", "--root", str(Path.cwd()), str(src), str(out)], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Typst compile failed for {src}:\n{result.stdout}\n{result.stderr}")
    return out
