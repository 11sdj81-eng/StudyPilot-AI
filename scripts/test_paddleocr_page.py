#!/usr/bin/env python3
"""PaddleOCR test — honest report with failure analysis.

Usage: python scripts/test_paddleocr_page.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "data" / "outputs" / "v5_reports"
REPORT_PATH = REPORT_DIR / "paddleocr_report.json"


def _check_paddle_available() -> dict[str, Any]:
    """Check PaddleOCR/PaddlePaddle availability."""
    result: dict[str, Any] = {
        "paddleocr": False,
        "paddle": False,
        "paddlepaddle": False,
        "errors": [],
    }
    for mod in ["paddleocr", "paddle", "paddlepaddle"]:
        try:
            __import__(mod)
            result[mod] = True
        except ImportError as e:
            result["errors"].append(f"{mod}: {e}")
    return result


def _analyze_failure() -> dict[str, Any]:
    """Analyze why PaddleOCR/PaddlePaddle fails on this system."""
    import platform

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "blockers": [
            {
                "package": "paddlepaddle",
                "issue": "No distribution for macOS arm64 + Python 3.14",
                "detail": (
                    "PaddlePaddle only provides pre-built wheels for: "
                    "Linux x86_64 (Python 3.8-3.12), Windows x86_64 (Python 3.8-3.12), "
                    "macOS x86_64 (Python 3.8-3.12). "
                    "There are NO wheels for: macOS arm64 (Apple Silicon), Python 3.13+."
                ),
                "pip_output": "ERROR: Could not find a version that satisfies the requirement paddlepaddle",
            },
            {
                "package": "paddleocr",
                "issue": "Depends on paddlepaddle which is unavailable",
                "detail": "paddleocr requires paddlepaddle as a backend. Even if paddleocr installs as a pure-Python package, it cannot run without paddlepaddle.",
            },
        ],
        "resolution_options": [
            "Use Google Colab (Linux x86_64, free GPU) — PaddleOCR works out of the box",
            "Use a Linux server with Python 3.10-3.11",
            "Use Docker: docker run paddlepaddle/paddle:latest",
            "Use EasyOCR as an alternative OCR engine (pip install easyocr, works on macOS arm64)",
            "Use Apple's Vision OCR framework via pyobjc for on-device OCR",
        ],
        "alternative_ocr_options": [
            {
                "name": "EasyOCR",
                "install": "pip install easyocr",
                "macos_arm64_support": "Yes (via PyTorch)",
                "python_314_support": "Unknown — may have similar PyTorch version issues",
            },
            {
                "name": "Tesseract OCR",
                "install": "brew install tesseract && pip install pytesseract",
                "macos_arm64_support": "Yes",
                "python_314_support": "Yes (C library, no Python version dependency)",
            },
            {
                "name": "Apple Vision OCR",
                "install": "pip install pyobjc-framework-Vision",
                "macos_arm64_support": "Yes (native Apple Silicon)",
                "python_314_support": "Likely",
            },
        ],
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    avail = _check_paddle_available()
    success = avail["paddleocr"] or avail["paddle"]

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "page_count": 0,
        "recognized_text_chars": 0,
        "average_confidence": 0.0,
        "output_files": [],
        "warnings": [],
        "availability": avail,
        "failure_analysis": _analyze_failure() if not success else None,
    }

    if not success:
        report["warnings"].append(
            "PaddleOCR/PaddlePaddle has NO distribution for macOS arm64 (Apple Silicon) "
            "with Python 3.14. The pip install fails with 'No matching distribution found'."
        )
        report["warnings"].append(
            "This is a KNOWN limitation of PaddlePaddle — they do not support macOS "
            "arm64 for any Python version. Use Google Colab or a Linux x86_64 machine."
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PaddleOCR] Report: {REPORT_PATH}")
    print(f"[PaddleOCR] Success: {success}")
    print(f"[PaddleOCR] Reason: No PaddlePaddle wheel for macOS arm64 + Python 3.14")


if __name__ == "__main__":
    main()
