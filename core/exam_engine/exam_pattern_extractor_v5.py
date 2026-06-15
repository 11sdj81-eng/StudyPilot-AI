"""Extract low-confidence exam patterns from DocumentBlocks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.document_intelligence_v5.document_blocks import DocumentParseResult


def extract_exam_patterns_v5(results: list[DocumentParseResult], output_path: str | Path = "data/outputs/v5_reports/exam_pattern_v5_report.json") -> dict:
    candidates = []
    for result in results:
        if "试卷" not in Path(result.file_path).name and "期末" not in Path(result.file_path).name:
            continue
        for page in result.pages:
            text = page.text or ""
            hits = re.findall(r"(?:^|\n)\s*(\d+)[\\.、]\s*([^\n]{8,120})", text)
            for no, body in hits[:10]:
                candidates.append(
                    {
                        "source_file": Path(result.file_path).name,
                        "page_number": page.page_number,
                        "question_no": no,
                        "question_preview": body,
                        "confidence": 0.35 if result.parser_name == "fallback" else 0.65,
                        "review_queue": True,
                        "reason": "fallback/low-confidence extraction; requires human review before use as high-confidence past paper pattern",
                    }
                )
    report = {
        "candidate_count": len(candidates),
        "high_confidence_count": sum(1 for c in candidates if c["confidence"] >= 0.7),
        "review_queue_count": sum(1 for c in candidates if c["review_queue"]),
        "candidates": candidates[:200],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
