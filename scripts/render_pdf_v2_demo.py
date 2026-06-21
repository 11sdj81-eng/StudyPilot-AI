"""Generate StudyPilot PDF 2.0 demo artifacts for chapter 1 electrostatics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pdf_content_v2.renderer import render_all_pdf_v2


def main() -> None:
    outputs = render_all_pdf_v2()
    print(json.dumps(outputs["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
