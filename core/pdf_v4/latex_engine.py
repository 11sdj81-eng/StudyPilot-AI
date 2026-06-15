"""LaTeX fallback availability for StudyPilot PDF v4."""

from __future__ import annotations

import shutil


def latex_available() -> bool:
    return any(shutil.which(cmd) for cmd in ["xelatex", "pdflatex", "tectonic"])
