"""Run the complete Figure Engine extraction pipeline on existing materials.

Usage: python -m core.figure_engine.run_extraction
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on the path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.figure_engine.pdf_figure_extractor import PdfFigureExtractor
from core.figure_engine.ppt_figure_extractor import PptFigureExtractor
from core.figure_engine.figure_bank import FigureBank
from core.figure_engine.figure_matcher import FigureMatcher
from core.figure_engine.figure_ranker import FigureRanker
from core.figure_engine.figure_selector import FigureSelector
from core.figure_engine.figure_rewriter import FigureRewriter
from core.figure_engine.figure_quality_gate import FigureQualityGate
from core.figure_engine.figure_engine_report import FigureEngineReport
from core.figure_engine.figure_objects import FigureObject, SourceType, ConceptId


def main():
    print("=" * 60)
    print("StudyPilot Figure Engine v1.0 — Extraction Pipeline")
    print("=" * 60)

    # --- Paths ---
    upload_dir = ROOT / "data" / "uploads" / "course_bb15e787"
    teaching_dir = ROOT / "data" / "teaching_assets"
    pre_extracted_dir = ROOT / "data" / "assets" / "course_bb15e787" / "figures"
    bank_root = ROOT / "data" / "figure_bank"
    extracted_dir = bank_root / "_extracted"
    reports_dir = bank_root / "_reports"

    all_figures: list[FigureObject] = []

    # ================================================================
    # Step 1: PDF Extraction
    # ================================================================
    print("\n[1/6] Extracting images from PDFs...")
    extractor = PdfFigureExtractor(output_dir=extracted_dir)

    # Only extract from source materials (textbook + past papers), not our own outputs
    source_pdfs = sorted(upload_dir.rglob("*.pdf"))
    source_pdfs = [p for p in source_pdfs if "概率论" not in p.name]  # skip unrelated

    print(f"  Found {len(source_pdfs)} source PDF(s):")
    for p in source_pdfs:
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"    - {p.name} ({size_mb:.1f} MB)")

    extraction_summary: dict = {"pdfs_processed": 0, "pdfs_failed": 0, "total_figures": 0}

    for pdf_path in source_pdfs:
        fname = pdf_path.name.lower()
        if "电磁场与电磁波" in fname and "期末" not in fname:
            source_type = SourceType.TEXTBOOK
        elif "期末" in fname or "试卷" in fname:
            source_type = SourceType.PAST_PAPER
        else:
            source_type = SourceType.UNKNOWN

        print(f"\n  Processing: {pdf_path.name} (source_type={source_type})")
        try:
            figures = extractor.extract_from_file(pdf_path, source_type=source_type)
            all_figures.extend(figures)
            extraction_summary["pdfs_processed"] += 1
            extraction_summary["total_figures"] += len(figures)

            # Count by type
            scanned = sum(1 for f in figures if f.source_type == SourceType.SCANNED_PAGE)
            embedded = len(figures) - scanned
            print(f"    Extracted {len(figures)} figures (embedded={embedded}, scanned_pages={scanned})")
        except Exception as e:
            print(f"    FAILED: {e}")
            extraction_summary["pdfs_failed"] += 1

    # Generate extraction report
    extraction_report = extractor.generate_extraction_report(
        reports_dir / "figure_extraction_report.json"
    )
    print(f"\n  Extraction summary: {extraction_summary}")

    # ================================================================
    # Step 2: PPT Extraction (no PPTX files expected, but check)
    # ================================================================
    print("\n[2/6] Checking for PPT/PPTX files...")
    ppt_extractor = PptFigureExtractor(output_dir=extracted_dir)

    ppt_available = PptFigureExtractor.check_availability()
    print(f"  python-pptx available: {ppt_available}")

    pptx_files = list(ROOT.rglob("*.pptx")) + list(ROOT.rglob("*.ppt"))
    if pptx_files:
        print(f"  Found {len(pptx_files)} PPT file(s)")
        for pptx_path in pptx_files:
            ppt_figures = ppt_extractor.extract_from_file(pptx_path)
            all_figures.extend(ppt_figures)
            print(f"    Extracted {len(ppt_figures)} figures from {pptx_path.name}")
    else:
        print("  No PPT/PPTX files found in project.")

    # ================================================================
    # Step 3: Ingest pre-existing extracted figures
    # ================================================================
    print("\n[3/6] Ingesting pre-existing extracted figures...")
    pre_existing_count = 0

    if pre_extracted_dir.exists():
        existing_images = sorted(pre_extracted_dir.glob("*.png"))
        print(f"  Found {len(existing_images)} pre-existing image(s)")

        for img_path in existing_images:
            # Determine if it's a page capture or a cropped figure
            fname = img_path.name
            is_page = "page" in fname.lower() or "figure_page" in fname.lower()

            # Try to extract page number from filename
            page_num = None
            parts = fname.replace(".png", "").split("_")
            for part in parts:
                try:
                    page_num = int(part)
                    break
                except ValueError:
                    continue

            figure = FigureObject(
                figure_id=f"existing_{img_path.stem}",
                concept_id=None,  # will be matched later
                source_type=SourceType.SCANNED_PAGE if is_page else SourceType.TEXTBOOK,
                source_file="电磁场与电磁波.pdf",
                source_page=page_num,
                bbox=None,
                image_path=str(img_path.resolve()),
                caption=None,
                ocr_text=None,
                tags=["pre_existing"] + (["scanned_page"] if is_page else []),
                width=None,
                height=None,
                has_text_overlap_risk=is_page,
                has_low_resolution_risk=False,
                has_noise_risk=is_page,
                metadata={
                    "source": "pre_extracted",
                    "is_full_page": is_page,
                    "needs_manual_crop": is_page,
                },
            )
            all_figures.append(figure)
            pre_existing_count += 1
    else:
        print("  No pre-existing figures directory found.")

    print(f"  Ingested {pre_existing_count} pre-existing figures")
    print(f"  Total figures so far: {len(all_figures)}")

    # ================================================================
    # Step 4: Match and Rank
    # ================================================================
    print("\n[4/6] Matching figures to concepts and ranking...")
    matcher = FigureMatcher()
    ranker = FigureRanker()

    all_figures = matcher.match_all(all_figures)
    all_figures = ranker.rank_all(all_figures)

    matched = sum(1 for f in all_figures if f.concept_id)
    print(f"  Matched: {matched}/{len(all_figures)} figures to concepts")

    # ================================================================
    # Step 5: Build FigureBank and add programmatic fallbacks
    # ================================================================
    print("\n[5/6] Building FigureBank and adding programmatic fallbacks...")
    bank = FigureBank(bank_root=bank_root)
    rewriter = FigureRewriter(output_dir=bank_root / "_processed")

    # Add all extracted figures to bank
    for fig in all_figures:
        bank.add_figure(fig)

    # Add programmatic fallback figures from existing SVGs
    prog_dir = ROOT / "data" / "teaching_assets" / "engineering" / "electromagnetic_static_chapter1" / "programmatic"
    prog_figures_added = 0

    prog_concept_map = {
        "gauss": ConceptId.GAUSS_LAW,
        "image": ConceptId.MIRROR_METHOD,
        "boundary": ConceptId.BOUNDARY_CONDITION,
        "potential": ConceptId.POTENTIAL_GRADIENT,
        "point_charge": ConceptId.ELECTRIC_FIELD,
        "electrostatic_energy": ConceptId.ELECTROSTATIC_ENERGY,
    }

    if prog_dir.exists():
        for svg_file in sorted(prog_dir.glob("*.svg")):
            fname = svg_file.name.lower()
            concept_id = None
            for key, cid in prog_concept_map.items():
                if key in fname:
                    concept_id = cid
                    break

            prog_fig = rewriter.build_programmatic_fallback(
                concept_id=concept_id or ConceptId.ELECTRIC_FIELD,
                svg_path=svg_file,
                caption=svg_file.stem.replace("_", " "),
            )
            bank.add_figure(prog_fig)
            prog_figures_added += 1

    print(f"  Added {prog_figures_added} programmatic fallback figures")
    print(f"  Bank total: {bank.count()} figures")

    # ================================================================
    # Step 6: Generate Reports
    # ================================================================
    print("\n[6/6] Generating reports...")

    all_bank_figures = bank.list_figures()

    # Run quality gate
    gate = FigureQualityGate()
    quality_results = gate.check(all_bank_figures)

    # Run selector to get fallback log
    selector = FigureSelector()
    for cid in ConceptId.ALL:
        for pdf_type in ["sprint", "pastpaper", "mockexam", "review"]:
            selector.select_figure(all_bank_figures, cid, pdf_type, "full_explanation", allow_fallback=True)

    # Generate all reports
    reporter = FigureEngineReport(reports_dir=reports_dir)
    report_paths = reporter.generate_all(
        figures=all_bank_figures,
        extraction_summary=extraction_summary,
        match_log=matcher.get_match_log(),
        fallback_log=selector.get_fallback_log(),
        extraction_report=extraction_report,
    )

    # Save bank index
    index_path = bank.save_index()
    print(f"  Bank index saved: {index_path}")

    # Save review queue
    review_path = bank_root / "review_queue.json"
    review_data = reporter._build_review_queue(all_bank_figures, quality_results)
    review_path.write_text(json.dumps(review_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Review queue: {review_path}")

    # ================================================================
    # Summary
    # ================================================================
    print("\n" + "=" * 60)
    print("EXTRACTION PIPELINE COMPLETE")
    print("=" * 60)

    # Count by source
    by_source: dict[str, int] = {}
    by_concept: dict[str, int] = {}
    for f in all_bank_figures:
        by_source[f.source_type] = by_source.get(f.source_type, 0) + 1
        cid = f.concept_id or "unmatched"
        by_concept[cid] = by_concept.get(cid, 0) + 1

    print(f"\nTotal figures in bank: {bank.count()}")
    print(f"\nBy source type:")
    for st, count in sorted(by_source.items()):
        print(f"  {st}: {count}")

    print(f"\nBy concept:")
    for cid, count in sorted(by_concept.items()):
        label = ConceptId.LABELS.get(cid, cid)
        print(f"  {label} ({cid}): {count}")

    print(f"\nQuality gate:")
    print(f"  Recommend use in PDF: {quality_results.get('recommend_use_in_pdf', False)}")
    print(f"  Issues: {len(quality_results.get('issues', []))}")
    for issue in quality_results.get("issues", []):
        print(f"    ⚠ {issue}")
    print(f"  Warnings: {len(quality_results.get('warnings', []))}")
    for warn in quality_results.get("warnings", [])[:5]:
        print(f"    ⚡ {warn}")

    print(f"\nReports generated:")
    for name, path in report_paths.items():
        print(f"  {name}: {path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
