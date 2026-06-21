#!/usr/bin/env python3
"""Figure Generator System — generate and validate probability Ch2 figures."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    print("=" * 60)
    print("Figure Generator System — 概率论第二章")
    print("=" * 60)

    from core.pdf_content_v2.figures import (
        FigureRegistry, FigureGenerator, FigureSelector, FigureValidator,
    )
    from core.pdf_content_v2.figures.figure_cache import FigureCache

    # ── Load concepts ──
    cp = Path("data/golden_chapters/math/probability_random_var_ch2/concepts.json")
    concepts = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else []
    print(f"\n📚 {len(concepts)} concepts loaded")

    # ── 1. Select + Generate ──
    registry = FigureRegistry()
    generator = FigureGenerator(subject_type="math")
    selector = FigureSelector()
    cache = FigureCache()

    a_level_ids = selector.priority_concepts(concepts)
    print(f"⭐ A/B-level concepts needing figures: {a_level_ids}")

    generated = 0
    for c in concepts:
        cid = c.get("id", "")
        types = selector.select(cid, "math")
        for ftype in types:
            if not generator.can_generate(cid, ftype):
                continue
            cached_svg = cache.get(f"{cid}_{ftype}")
            fig = generator.generate(cid, ftype)
            if fig:
                if cached_svg:
                    fig.svg_content = cached_svg  # use cached version
                else:
                    cache.set(f"{cid}_{ftype}", fig.svg_content)
                registry.register(fig)
                generated += 1
                print(f"  ✅ {fig.figure_id}: {fig.title} ({ftype}) [{len(fig.svg_content)} bytes]")

    print(f"\n🎨 Generated {generated} figures ({registry.count()} in registry)")
    print(f"   Cache entries: {cache.count()}")

    # ── 2. Validate ──
    validator = FigureValidator()
    # Collect all generated figures from registry
    all_fig_ids = [
        "random_variable_pdf", "distribution_function_cdf",
        "discrete_random_variable_pdf", "continuous_random_variable_pdf",
        "common_discrete_distributions_pdf",
        "common_continuous_distributions_normal",
        "common_continuous_distributions_exponential",
        "common_continuous_distributions_uniform",
        "rv_function_distribution_pdf",
    ]
    all_figs = [f for fid in all_fig_ids if (f := registry.get(fid))]

    # A-level concepts: distribution_function, continuous_rv, normal, exponential, rv_transform
    high_priority = ["distribution_function", "continuous_random_variable",
                     "common_continuous_distributions", "rv_function_distribution"]
    report = validator.validate(all_figs, a_level_concept_ids=high_priority)
    rd = report.to_dict()
    print(f"\n📊 Figure Validation Report:")
    for k, v in rd.items():
        print(f"   {k}: {v}")

    # ── 3. Course-agnostic check ──
    print(f"\n🌐 Course-agnostic support:")
    for stype in ["math", "engineering", "digital_logic"]:
        types = registry.supported_types(stype)
        print(f"   {stype}: {types[:3]}...")

    # ── Save ──
    rp = Path("data/outputs/pdf_v2_probability_ch2/figure_report.json")
    rp.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
