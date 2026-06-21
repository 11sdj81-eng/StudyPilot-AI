#!/usr/bin/env python3
"""SP-008: Cross-contamination test — verify zero ghost chunks after deletion."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def make_chunks(course_id: str, resource_name: str, texts: list[str]) -> list[dict]:
    return [
        {
            "resource_id": f"{course_id}_{resource_name}",
            "text": t,
            "source": resource_name,
        }
        for t in texts
    ]


def search_contains_term(results: list[dict], term: str) -> bool:
    return any(term in r.get("text", "") for r in results)


def main():
    print("=" * 60)
    print("SP-008: Cross-Contamination Test — FAISS Ghost Chunks")
    print("=" * 60)

    from core.vector_store import (
        CourseVectorStore, VectorGarbageCollector, run_garbage_collector,
    )

    test_course = "test_cross_contamination"

    # ── Step 1: Upload probability materials ──
    prob_chunks = make_chunks(test_course, "prob_resource", [
        "随机变量是样本空间到实数的映射",
        "分布函数 F(x)=P{X≤x} 满足单调不减和右连续",
        "二项分布 B(n,p) 的期望为 np，方差为 np(1-p)",
        "泊松分布 P(λ) 的期望和方差均为 λ",
        "正态分布 N(μ,σ²) 标准化为 Z=(X-μ)/σ",
    ])

    store = CourseVectorStore(test_course)
    store.build(prob_chunks)
    print(f"\n1️⃣  Uploaded probability: {len(prob_chunks)} chunks")

    # Verify probability content is searchable
    r1 = store.search("二项分布", top_k=3)
    has_prob = search_contains_term(r1, "二项分布")
    print(f"   Search '二项分布': {'✅ found' if has_prob else '❌ not found'}")

    # ── Step 2: Delete probability resource ──
    store.remove_chunks_by_resource(f"{test_course}_prob_resource")
    print(f"\n2️⃣  Deleted probability resource")

    # Verify chunks.json is empty
    chunks_after_delete = json.loads(store.meta_path.read_text(encoding="utf-8"))
    print(f"   Remaining chunks in metadata: {len(chunks_after_delete)}")

    # Verify FAISS index is rebuilt
    integrity = store.integrity_check()
    print(f"   Integrity: orphans={integrity['orphan_vector_count']}, in_sync={integrity['in_sync']}")
    assert integrity["orphan_vector_count"] == 0, f"ORPHAN VECTORS: {integrity['orphan_vector_count']}"

    # ── Step 3: Upload field wave materials ──
    fw_chunks = make_chunks(test_course, "fw_resource", [
        "电场强度 E 是单位正电荷所受的力",
        "高斯定理：闭合曲面电位移通量等于包围自由电荷",
        "电位与电场关系：E = -∇φ",
    ])
    store.build(fw_chunks)
    print(f"\n3️⃣  Uploaded field wave: {len(fw_chunks)} chunks")

    # ── Step 4: CRITICAL CHECK — search should NOT return probability ──
    r2 = store.search("随机变量 分布函数 泊松", top_k=3)
    prob_leak = search_contains_term(r2, "随机变量") or search_contains_term(r2, "泊松")
    print(f"\n4️⃣  Cross-contamination check:")
    print(f"   Search for probability terms: {'❌ LEAKED!' if prob_leak else '✅ Clean (no probability)'}")

    r3 = store.search("电场 高斯", top_k=3)
    has_fw = search_contains_term(r3, "高斯") or search_contains_term(r3, "电场")
    print(f"   Search for field wave terms: {'✅ found' if has_fw else '❌ missing'}")

    # ── Step 5: Delete field wave → upload digital logic ──
    store.remove_chunks_by_resource(f"{test_course}_fw_resource")
    dl_chunks = make_chunks(test_course, "dl_resource", [
        "组合逻辑电路输出仅取决于当前输入",
        "卡诺图用于化简逻辑函数",
        "D触发器的次态等于当前输入D",
    ])
    store.build(dl_chunks)
    print(f"\n5️⃣  Replaced field wave with digital logic: {len(dl_chunks)} chunks")

    r4 = store.search("高斯 电场 电位", top_k=3)
    fw_leak = search_contains_term(r4, "高斯") or search_contains_term(r4, "电场")
    print(f"   Field wave leak check: {'❌ LEAKED!' if fw_leak else '✅ Clean (no field wave)'}")

    r5 = store.search("D触发器 卡诺图", top_k=3)
    has_dl = search_contains_term(r5, "卡诺图") or search_contains_term(r5, "D触发器")
    print(f"   Digital logic present: {'✅ found' if has_dl else '❌ missing'}")

    # ── Step 6: Run garbage collector ──
    gc_report = run_garbage_collector()
    test_report = next((r for r in gc_report["course_reports"] if r["course_id"] == test_course), {})
    print(f"\n6️⃣  Garbage Collector Report:")
    print(f"   Courses scanned: {gc_report['courses_scanned']}")
    print(f"   Total orphans: {gc_report['total_orphan_vector_count']}")
    print(f"   Test course: orphans={test_report.get('orphan_vector_count', '?')}, sync={test_report.get('in_sync', '?')}")

    # ── Clean up test data ──
    import shutil
    shutil.rmtree(store.store_dir, ignore_errors=True)

    # ── Final verdict ──
    all_clean = (not prob_leak and not fw_leak and integrity["orphan_vector_count"] == 0)
    print(f"\n{'='*60}")
    print(f"SP-008: {'✅ FIXED' if all_clean else '❌ STILL BROKEN'}")
    if prob_leak:
        print(f"  FAIL: Probability leaked after deletion")
    if fw_leak:
        print(f"  FAIL: Field wave leaked after deletion")
    if integrity["orphan_vector_count"] > 0:
        print(f"  FAIL: {integrity['orphan_vector_count']} orphan vectors")
    print(f"{'='*60}")
    return 0 if all_clean else 1


if __name__ == "__main__":
    sys.exit(main())
