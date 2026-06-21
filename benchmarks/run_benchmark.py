#!/usr/bin/env python3
"""Run retrieval benchmark and output RETRIEVAL_BENCHMARK_REPORT.md."""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.retrieval_benchmark import RetrievalBenchmark


def main():
    print("=" * 60)
    print("StudyPilot Retrieval Benchmark")
    print("=" * 60)

    benchmark = RetrievalBenchmark()
    print(f"Loaded {len(benchmark.queries)} test queries")

    print("\nRunning benchmarks (this may take 30-60 seconds)...")
    results = benchmark.run_all()

    print(f"\nResults Summary:")
    print(f"  Total queries: {results['total_queries']}")
    f = results["faiss"]
    h = results["hybrid"]
    print(f"  FAISS   - Top1: {f['top1_accuracy']:.4f}, Top3: {f['top3_recall']:.4f}, "
          f"Citation: {f['citation_accuracy']:.4f}, Quality: {f['quality_pass_rate']:.4f}")
    print(f"  Hybrid  - Top1: {h['top1_accuracy']:.4f}, Top3: {h['top3_recall']:.4f}, "
          f"Citation: {h['citation_accuracy']:.4f}, Quality: {h['quality_pass_rate']:.4f}")

    # Per course
    for cid, pc in results.get("per_course", {}).items():
        print(f"  {cid}: {pc['total_queries']} queries")
        if pc["faiss"]:
            print(f"    FAISS  Top1={pc['faiss']['top1_accuracy']:.4f}  Top3={pc['faiss']['top3_recall']:.4f}")
        if pc["hybrid"]:
            print(f"    Hybrid Top1={pc['hybrid']['top1_accuracy']:.4f}  Top3={pc['hybrid']['top3_recall']:.4f}")

    # Generate report
    print("\nGenerating RETRIEVAL_BENCHMARK_REPORT.md...")
    report = benchmark.generate_report(results)
    output_path = Path("RETRIEVAL_BENCHMARK_REPORT.md")
    output_path.write_text(report, encoding="utf-8")
    print(f"✅ Report written to {output_path.resolve()}")

    # Also save raw results JSON for final report
    json_path = Path("benchmarks/benchmark_results.json")
    json_path.write_text(
        __import__("json").dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Raw results saved to {json_path.resolve()}")


if __name__ == "__main__":
    main()
