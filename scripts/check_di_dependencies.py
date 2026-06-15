#!/usr/bin/env python3
"""StudyPilot v5.1 — Document Intelligence dependency checker.

Detects availability of MinerU, PaddleOCR, DocLayout-YOLO, Marker,
and other DI-relevant packages.  Outputs a structured JSON report.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_DIR = Path("data/outputs/v5_reports")
REPORT_PATH = REPORT_DIR / "dependency_check_v51.json"


def _try_import(module: str) -> dict[str, Any]:
    """Try importing a module and return structured result."""
    result: dict[str, Any] = {
        "module": module,
        "available": False,
        "version": None,
        "import_error": None,
    }
    try:
        mod = importlib.import_module(module)
        result["available"] = True
        result["version"] = getattr(mod, "__version__", "unknown")
    except ImportError as e:
        result["import_error"] = str(e)
    except Exception as e:
        result["import_error"] = f"Unexpected: {e}"
    return result


def _try_cli(command: str, args: list[str] | None = None) -> dict[str, Any]:
    """Check if a CLI command is available."""
    result: dict[str, Any] = {
        "command": command,
        "available": False,
        "version_output": None,
        "error": None,
        "install_hint": None,
    }
    try:
        cmd = [command] + (args or ["--version"])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            result["available"] = True
            result["version_output"] = (proc.stdout + proc.stderr).strip()
        else:
            result["error"] = proc.stderr.strip() or proc.stdout.strip()
    except FileNotFoundError:
        result["error"] = f"Command '{command}' not found in PATH"
    except subprocess.TimeoutExpired:
        result["error"] = "Command timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


def _install_hint(package: str) -> str:
    hints = {
        "mineru": "pip install magic-pdf  (or use MinerU online: https://mineru.net)",
        "magic_pdf": "pip install magic-pdf",
        "paddleocr": "pip install paddleocr paddlepaddle  (note: arm64 macOS may need special install)",
        "paddle": "pip install paddlepaddle",
        "paddlepaddle": "pip install paddlepaddle",
        "doclayout_yolo": "pip install doclayout-yolo ultralytics",
        "ultralytics": "pip install ultralytics",
        "marker": "pip install marker-pdf",
        "marker_pdf": "pip install marker-pdf",
        "opencv": "pip install opencv-python",
        "cv2": "pip install opencv-python",
        "python-pptx": "pip install python-pptx",
        "fitz": "pip install PyMuPDF",
        "PyMuPDF": "pip install PyMuPDF",
    }
    return hints.get(package, f"pip install {package}")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "check_time": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": sys.platform,
        "architecture": {"machine": __import__("platform").machine(),
                         "processor": __import__("platform").processor()},
        "python_compatibility_note": "",
        "packages": {},
        "cli_tools": {},
        "overall_status": {
            "any_parser_available": False,
            "any_ocr_available": False,
            "any_layout_available": False,
            "fitz_available": False,
            "pillow_available": False,
        },
        "install_suggestions": [],
    }

    # Python version check
    major, minor = sys.version_info[:2]
    if minor >= 13:
        report["python_compatibility_note"] = (
            f"Python {major}.{minor} is very new. Many ML packages (MinerU, PaddleOCR, "
            "PaddlePaddle, Marker) may not have pre-built wheels for this Python version "
            "or for macOS arm64. Consider using Python 3.10–3.12 via conda/pyenv for "
            "best compatibility with the DI ecosystem."
        )

    # ---- Python packages ----
    packages_to_check = [
        # Core DI tools
        "magic_pdf",
        "mineru",
        "paddleocr",
        "paddle",
        "doclayout_yolo",
        "marker",
        "marker_pdf",
        # Support libraries
        "ultralytics",
        "cv2",
        "fitz",
        "pptx",
        "PIL",
        "numpy",
        "torch",
        "transformers",
    ]

    for pkg in packages_to_check:
        result = _try_import(pkg)
        clean_name = pkg.replace(".", "_")
        report["packages"][pkg] = {
            "available": result["available"],
            "version": result["version"],
        }
        if not result["available"]:
            report["packages"][pkg]["error"] = result.get("import_error")
            report["packages"][pkg]["install_hint"] = _install_hint(pkg)

    # ---- CLI tools ----
    cli_tools = [
        ("mineru", ["--version"]),
        ("magic-pdf", ["--version"]),
        ("marker", ["--version"]),
        ("marker_single", ["--help"]),
        ("paddleocr", ["--version"]),
        ("magic-pdf", ["--help"]),
    ]
    for cmd, args in cli_tools:
        result = _try_cli(cmd, args)
        report["cli_tools"][cmd] = {
            "available": result["available"],
            "version": result.get("version_output"),
        }
        if not result["available"]:
            report["cli_tools"][cmd]["error"] = result.get("error")
            report["cli_tools"][cmd]["install_hint"] = _install_hint(cmd.replace("magic-pdf", "magic_pdf"))

    # ---- Overall status ----
    report["overall_status"]["fitz_available"] = report["packages"].get("fitz", {}).get("available", False)
    report["overall_status"]["pillow_available"] = report["packages"].get("PIL", {}).get("available", False)

    # Check parsers
    mineru_ok = bool(
        report["packages"].get("magic_pdf", {}).get("available")
        or report["cli_tools"].get("magic-pdf", {}).get("available")
    )
    report["overall_status"]["any_parser_available"] = mineru_ok

    # Check OCR
    ocr_ok = bool(report["packages"].get("paddleocr", {}).get("available"))
    report["overall_status"]["any_ocr_available"] = ocr_ok

    # Check layout
    layout_ok = bool(
        report["packages"].get("doclayout_yolo", {}).get("available")
        or report["packages"].get("ultralytics", {}).get("available")
    )
    report["overall_status"]["any_layout_available"] = layout_ok

    # Build install suggestions
    if not mineru_ok:
        report["install_suggestions"].append({
            "tool": "MinerU",
            "command": "pip install magic-pdf",
            "alternative": "Use MinerU online service at https://mineru.net (upload PDF, download markdown+images)",
            "python_version_note": "Requires Python 3.8–3.12; you are on 3.14 — may fail to install.",
        })
    if not ocr_ok:
        report["install_suggestions"].append({
            "tool": "PaddleOCR",
            "command": "pip install paddleocr paddlepaddle",
            "note": "arm64 macOS may not have PaddlePaddle wheels. Use Google Colab or Linux server as alternative.",
            "python_version_note": "Requires Python 3.8–3.11; you are on 3.14 — likely will NOT install.",
        })
    if not layout_ok:
        report["install_suggestions"].append({
            "tool": "DocLayout-YOLO",
            "command": "pip install doclayout-yolo ultralytics",
            "note": "Requires PyTorch; may work on Python 3.14 but untested.",
        })

    marker_ok = bool(
        report["packages"].get("marker", {}).get("available")
        or report["packages"].get("marker_pdf", {}).get("available")
    )
    if not marker_ok:
        report["install_suggestions"].append({
            "tool": "Marker",
            "command": "pip install marker-pdf",
            "python_version_note": "Requires Python 3.9–3.12; you are on 3.14 — may fail to install.",
        })

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dependency check report written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
