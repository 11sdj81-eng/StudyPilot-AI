#!/usr/bin/env python3
"""StudyPilot Final — Real Study Pipeline.

End-to-end: OCR → DocumentBlocks → KnowledgeGraph → ExamPattern → RealDemo PDF.

Usage:
  python scripts/run_real_study_pipeline.py \
    --textbook data/uploads/course_bb15e787/电磁场与电磁波.pdf \
    --exam "data/uploads/course_bb15e787/2023 电磁场与电磁波 期末试卷.pdf" \
    --course "电磁场与电磁波" \
    --chapter "第一章 静电场" \
    --max-pages 10
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "data" / "outputs" / "final_demo"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Real Study Pipeline")
    parser.add_argument("--textbook", required=True, help="Path to textbook PDF")
    parser.add_argument("--exam", required=True, help="Path to exam PDF")
    parser.add_argument("--course", default="电磁场与电磁波", help="Course name")
    parser.add_argument("--chapter", default="第一章 静电场", help="Chapter name")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages per PDF")
    parser.add_argument("--target-score", default="85+", help="Target score")
    parser.add_argument("--weak-points", default="高斯定理,镜像法", help="Comma-separated weak points")
    args = parser.parse_args()

    print("=" * 60)
    print("StudyPilot Final — Real Study Pipeline")
    print("=" * 60)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "course": args.course,
        "chapter": args.chapter,
        "target_score": args.target_score,
        "weak_points": [w.strip() for w in args.weak_points.split(",")],
        "textbook_path": args.textbook,
        "exam_path": args.exam,
        "textbook_parse": {},
        "exam_parse": {},
        "ocr_total_chars": 0,
        "concept_evidence": [],
        "exam_questions": [],
        "knowledge_nodes": [],
        "demo_generated": False,
        "errors": [],
    }

    # ---- Step 1: Parse with DI Worker ----
    print("\n[1/5] Parsing with DI Worker (PaddleOCR)...")
    try:
        from core.document_intelligence_v5.worker_client import parse_with_worker, parse_to_document_blocks, check_worker_available

        worker_status = check_worker_available()
        if not worker_status["available"]:
            report["errors"].append(f"Worker unavailable: {worker_status.get('errors')}")
            print(f"  ❌ Worker unavailable")
        else:
            # Parse textbook
            print(f"  Parsing textbook: {Path(args.textbook).name}")
            textbook_doc = parse_with_worker(args.textbook, OUTPUT_DIR / "textbook_parse", mode="paddleocr", max_pages=args.max_pages)
            report["textbook_parse"] = {
                "success": textbook_doc.get("success"),
                "pages": len(textbook_doc.get("pages", [])),
                "chars": sum(len(p.get("text", "")) for p in textbook_doc.get("pages", [])),
            }
            chars_tb = report["textbook_parse"]["chars"]
            print(f"    {'✅' if textbook_doc.get('success') else '❌'} {chars_tb} OCR chars")

            # Parse exam
            print(f"  Parsing exam: {Path(args.exam).name}")
            exam_doc = parse_with_worker(args.exam, OUTPUT_DIR / "exam_parse", mode="paddleocr", max_pages=args.max_pages)
            report["exam_parse"] = {
                "success": exam_doc.get("success"),
                "pages": len(exam_doc.get("pages", [])),
                "chars": sum(len(p.get("text", "")) for p in exam_doc.get("pages", [])),
            }
            chars_exam = report["exam_parse"]["chars"]
            print(f"    {'✅' if exam_doc.get('success') else '❌'} {chars_exam} OCR chars")

            report["ocr_total_chars"] = chars_tb + chars_exam

            # Convert to blocks — read saved document.json directly instead of re-parsing
            textbook_blocks = _read_blocks_from_doc(OUTPUT_DIR / "textbook_parse" / "document.json")
            exam_blocks = _read_blocks_from_doc(OUTPUT_DIR / "exam_parse" / "document.json")
    except Exception as e:
        report["errors"].append(f"Worker step failed: {e}")
        print(f"  ❌ {e}")
        _write_report(report)
        return

    # ---- Step 2: Extract evidence ----
    print("\n[2/5] Extracting concept evidence & exam questions...")
    try:
        from core.real_content_builder import (
            RealConceptEvidence, RealExamQuestionCandidate, RealSourceRef,
            extract_concept_evidence, extract_exam_questions,
            extract_real_source_refs, build_review_sections, clean_ocr_text,
        )

        # Fake a profile for weak point matching
        class FakeProfile:
            weak_points = report["weak_points"]

        all_blocks = textbook_blocks + exam_blocks
        concept_evidence = extract_concept_evidence(all_blocks, source_file="textbook+exam")
        exam_questions = extract_exam_questions(exam_blocks, source_file=Path(args.exam).name)
        source_refs = extract_real_source_refs(all_blocks, source_file="combined")

        report["concept_evidence"] = [
            {"concept_id": ev.concept_id, "concept_name": ev.concept_name,
             "source_file": ev.source_file, "page": ev.page_number,
             "snippet": ev.evidence_text[:120], "keywords": ev.matched_keywords}
            for ev in concept_evidence
        ]
        report["exam_questions"] = [
            {"question_id": q.question_id, "type": q.inferred_question_type,
             "text": q.raw_text[:200], "concepts": q.inferred_concepts}
            for q in exam_questions
        ]

        seen_concepts = set(ev.concept_id for ev in concept_evidence)
        report["knowledge_nodes"] = list(seen_concepts)
        print(f"  Concepts: {len(concept_evidence)} evidence items, {len(seen_concepts)} unique")
        print(f"  Questions: {len(exam_questions)} candidates")
        print(f"  Source refs: {len(source_refs)}")

        # Build review sections
        review_sections = build_review_sections(concept_evidence, FakeProfile())
        print(f"  Review sections: {len(review_sections)}")
    except Exception as e:
        report["errors"].append(f"Evidence extraction failed: {e}")
        print(f"  ❌ {e}")
        _write_report(report)
        return

    # ---- Step 3: Generate Real Demo ----
    print("\n[3/5] Generating v5 Real Demo...")
    demo_md = _build_demo_markdown(args, report, concept_evidence, exam_questions, review_sections, source_refs)
    demo_path = OUTPUT_DIR / "StudyPilot_v5_Review_RealDemo.md"
    demo_path.write_text(demo_md.decode("utf-8") if isinstance(demo_md, bytes) else demo_md, encoding="utf-8")
    report["demo_generated"] = True
    report["demo_path"] = str(demo_path)
    print(f"  ✅ {demo_path} ({len(demo_md)} chars)")

    # ---- Step 4: Save reports ----
    print("\n[4/5] Saving reports...")
    for name, data in [
        ("parsed_textbook_summary.json", report["textbook_parse"]),
        ("parsed_exam_summary.json", report["exam_parse"]),
        ("knowledge_graph_real.json", {"nodes": report["knowledge_nodes"], "evidence": report["concept_evidence"]}),
        ("exam_patterns_real.json", {"candidates": report["exam_questions"]}),
    ]:
        p = OUTPUT_DIR / name
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ {p}")

    # ---- Step 5: Write final report ----
    print("\n[5/5] Writing pipeline report...")
    _write_report(report)

    print(f"\n{'='*60}")
    print(f"✅ Pipeline complete!")
    print(f"   OCR: {report['ocr_total_chars']} chars")
    print(f"   Concepts: {len(report['knowledge_nodes'])}")
    print(f"   Questions: {len(report['exam_questions'])}")
    print(f"   Demo: {report['demo_path']}")
    print(f"{'='*60}")


def _build_demo_markdown(args, report, concept_evidence, exam_questions, review_sections, source_refs) -> str:
    """Build the v5 Real Demo Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"""# StudyPilot v5 — 真实可用版 Review Demo

**生成时间:** {now}
**解析引擎:** PaddleOCR v3.7 (Python 3.11 DI Worker)
**课程:** {args.course} · {args.chapter}

---

## 用户画像

- 目标分数: {args.target_score}
- 薄弱点: {', '.join(report['weak_points'])}
- 推荐: Sprint → PastPaper → MockExam

---

## 教材 OCR 解析结果

| 指标 | 数值 |
|------|------|
| 教材 | {Path(args.textbook).name} |
| 解析页数 | {report['textbook_parse'].get('pages', 0)} |
| OCR 字符数 | {report['textbook_parse'].get('chars', 0)} |
| 真题 | {Path(args.exam).name} |
| 解析页数 | {report['exam_parse'].get('pages', 0)} |
| OCR 字符数 | {report['exam_parse'].get('chars', 0)} |
| 总 OCR 字符 | {report['ocr_total_chars']} |

---

## 从 OCR 中识别的核心知识点

"""

    seen_concepts = set()
    for ev in concept_evidence:
        if ev.concept_id not in seen_concepts:
            seen_concepts.add(ev.concept_id)
            weak_tag = ""
            if ev.concept_name in report.get("weak_points", []):
                weak_tag = " ⚠️ 薄弱点"
            md += f"### {ev.concept_name}{weak_tag}\n\n"
            md += f"**来源:** {ev.source_file} 第 {ev.page_number + 1} 页\n\n"
            md += f"**证据:** \"{ev.evidence_text[:150]}\"\n\n"
            md += f"**关键词:** {', '.join(ev.matched_keywords)}\n\n"

    md += "---\n\n## 真题题型候选\n\n"

    for q in exam_questions[:8]:
        md += f"### {q.inferred_question_type.upper()} 题 (P{q.page_number + 1})\n\n"
        md += f"```\n{q.raw_text[:300]}\n```\n\n"
        if q.inferred_concepts:
            labels = []
            for c in q.inferred_concepts:
                from core.real_content_builder import CONCEPT_KEYWORDS
                labels.append(CONCEPT_KEYWORDS.get(c, {}).get("name", c))
            md += f"**涉及概念:** {', '.join(labels)}\n\n"

    md += """---

## 来源引用

"""

    for ref in source_refs[:10]:
        md += f"- [{ref.source_file} P{ref.page_number + 1}] {ref.snippet}\n"

    md += """

---

## 当前限制说明

- **OCR 引擎:** PaddleOCR v3.7 (PP-OCRv6 模型)
- **自动裁图:** 未启用 (DocLayout-YOLO 权重不可用)
- **教材插图:** 使用 v4.1 程序化 SVG (fallback)
- **MinerU:** 已安装但未用于本次 Demo
- **完整 PDF:** 需要 Typst CLI (`brew install typst`)

---

> ✅ 本 Demo 中的知识点证据均来自真实 OCR 结果。
> 来源标注了教材/真题的页码。
> 未裁剪的扫描整页图未作为教材插图使用。

*StudyPilot v5.2 — Real Demo Pipeline*
"""

    return md


def _read_blocks_from_doc(doc_path: Path) -> list[dict[str, Any]]:
    """Read blocks from a saved document.json."""
    if not doc_path.exists():
        return []
    try:
        doc = json.loads(doc_path.read_text(encoding="utf-8"))
        blocks = []
        for page in doc.get("pages", []):
            for b in page.get("blocks", []):
                blocks.append({
                    "block_id": b.get("block_id", ""),
                    "block_type": b.get("block_type", "text"),
                    "text": b.get("text", ""),
                    "content": b.get("text", ""),
                    "source_file": doc.get("file_path", ""),
                    "source_page": page.get("page_number", 0),
                    "page_number": page.get("page_number", 0),
                    "confidence": b.get("confidence", 0.0),
                })
        return blocks
    except Exception:
        return []


def _write_report(report: dict) -> None:
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    (OUTPUT_DIR / "full_real_pipeline_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
