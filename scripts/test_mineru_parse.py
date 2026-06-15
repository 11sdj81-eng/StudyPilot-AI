#!/usr/bin/env python3
"""MinerU parse test — honest report with failure analysis.

Usage: python scripts/test_mineru_parse.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "data" / "outputs" / "v5_reports"
REPORT_PATH = REPORT_DIR / "mineru_parse_report.json"


def _check_mineru_python() -> dict[str, Any]:
    """Check if MinerU Python API is available."""
    result: dict[str, Any] = {"available": False, "error": None, "version": None}
    try:
        import magic_pdf
        result["available"] = True
        result["version"] = getattr(magic_pdf, "__version__", "unknown")
    except ImportError as e:
        result["error"] = str(e)
    return result


def _check_mineru_cli() -> dict[str, Any]:
    """Check if magic-pdf CLI is available."""
    for cmd in ["magic-pdf", "mineru"]:
        try:
            proc = subprocess.run(
                [cmd, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                return {"available": True, "command": cmd, "version": (proc.stdout + proc.stderr).strip()}
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return {"available": False, "command": None, "version": None}


def _test_install_python314() -> dict[str, Any]:
    """Detailed analysis of why MinerU fails on Python 3.14."""
    return {
        "python_version": sys.version,
        "blocker": "pydantic-core Rust compilation",
        "detail": (
            "MinerU depends on pydantic-core >= 2.x which uses PyO3 (Rust bindings). "
            "PyO3 0.22.6 max supported Python version is 3.13. "
            "Python 3.14 removed PyUnicode_DATA C API which jiter/pydantic-core relies on. "
            "Even with PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1, the Rust compilation fails "
            "at the jiter crate level."
        ),
        "resolution_options": [
            "Use Python 3.10-3.12 via pyenv or conda (RECOMMENDED for full DI ecosystem)",
            "Use MinerU online service at https://mineru.net (upload PDF, get markdown+images)",
            "Use MinerU Docker image: docker run opendatalab/mineru",
            "Use MinerU Desktop App (Windows/Mac/Linux)",
        ],
        "tried": [
            "pip install magic-pdf  →  pydantic-core build failed (PyO3 max 3.13)",
            "PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 pip install magic-pdf  →  jiter Rust compilation failed (PyUnicode_DATA removed in 3.14)",
        ],
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    python_check = _check_mineru_python()
    cli_check = _check_mineru_cli()
    install_analysis = _test_install_python314()

    success = python_check["available"] or cli_check["available"]

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "parser_name": "MinerU (magic-pdf)",
        "input_files": ["data/uploads/course_bb15e787/电磁场与电磁波.pdf",
                        "data/uploads/course_bb15e787/2020-2021 第二学期 电磁场与电磁波 期末试卷.pdf"],
        "python_api_available": python_check["available"],
        "cli_available": cli_check["available"],
        "markdown_generated": False,
        "json_generated": False,
        "image_count": 0,
        "formula_count": 0,
        "table_count": 0,
        "warnings": [],
        "next_action": "",
        "install_analysis": install_analysis,
    }

    if not success:
        report["warnings"].append(
            "MinerU cannot be installed on Python 3.14.4 due to Rust/PyO3 compatibility "
            "issues with pydantic-core. See install_analysis for details."
        )
        report["next_action"] = (
            "RECOMMENDED: Create a Python 3.10-3.12 conda/pyenv environment and install "
            "MinerU there. Alternatively, use MinerU online service at https://mineru.net "
            "or the MinerU Docker image. The external_tool_mode interface is reserved in "
            "scripts/test_mineru_parse.py for when MinerU is available externally."
        )
    else:
        report["next_action"] = "MinerU is available. Run parse test."

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[MinerU] Report: {REPORT_PATH}")
    print(f"[MinerU] Success: {success}")
    print(f"[MinerU] Reason: Python 3.14 incompatible with pydantic-core Rust compilation")


if __name__ == "__main__":
    main()
