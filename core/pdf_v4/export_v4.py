"""Public export entrypoint for StudyPilot PDF v4."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.pdf_v4.pdf_v4_renderer import render_all_v4_pdfs


def export_v4_all(output_dir: str | Path = "data/outputs/pdf_v4") -> dict[str, Any]:
    return render_all_v4_pdfs(output_dir)
