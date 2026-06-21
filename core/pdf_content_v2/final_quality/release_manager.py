"""ReleaseManager — Official vs Draft PDF management."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.pdf_content_v2.final_quality.final_quality_gate import FinalQualityReport


@dataclass
class ReleaseResult:
    course_name: str = ""
    chapter_name: str = ""
    pdf_type: str = ""
    release_level: str = "FAILED"
    official_path: str = ""
    draft_path: str = ""
    report_path: str = ""

    def to_dict(self) -> dict:
        return {
            "course_name": self.course_name, "chapter_name": self.chapter_name,
            "pdf_type": self.pdf_type, "release_level": self.release_level,
            "official_path": self.official_path, "draft_path": self.draft_path,
            "report_path": self.report_path,
        }


class ReleaseManager:
    """Manage Official and Draft PDF outputs."""

    def __init__(self, output_dir: str = "data/outputs/release"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def release(self, source_pdf: str | Path, report: FinalQualityReport,
                course_name: str = "", chapter_name: str = "",
                pdf_type: str = "Review") -> ReleaseResult:
        """Copy source PDF to Official or Draft path based on quality report."""
        source = Path(source_pdf)
        result = ReleaseResult(
            course_name=course_name, chapter_name=chapter_name,
            pdf_type=pdf_type, release_level=report.release_level,
        )

        safe_course = course_name.replace(" ", "_").replace("·", "")
        safe_chapter = chapter_name.replace(" ", "_").replace("：", "_")
        base_name = f"{safe_course}_{safe_chapter}_{pdf_type}"

        if not source.exists():
            return result

        if report.release_level == "RELEASE_READY":
            dest_name = f"{base_name}_Official.pdf"
            dest = self.output_dir / dest_name
            shutil.copy2(source, dest)
            result.official_path = str(dest)
        elif report.release_level in ("MANUAL_REVIEW", "DRAFT"):
            dest_name = f"{base_name}_Draft.pdf"
            dest = self.output_dir / dest_name
            shutil.copy2(source, dest)
            result.draft_path = str(dest)

        return result

    def release_all(self, pdf_map: dict[str, Path],
                     report: FinalQualityReport,
                     course_name: str = "",
                     chapter_name: str = "") -> list[ReleaseResult]:
        """Release all PDF types with the same quality report."""
        results = []
        for pdf_type, path in pdf_map.items():
            r = self.release(path, report, course_name, chapter_name, pdf_type)
            results.append(r)
        return results
