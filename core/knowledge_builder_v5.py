"""Build a lightweight KnowledgeGraph v5 from DocumentBlocks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.document_intelligence_v5.document_blocks import DocumentParseResult


CONCEPT_KEYWORDS = {
    "electric_field": ["电场强度", "场强"],
    "gauss_law": ["高斯", "通量"],
    "potential_gradient": ["电位", "梯度"],
    "boundary_conditions": ["边界条件", "分界面"],
    "image_method": ["镜像法", "镜像电荷"],
    "electrostatic_energy": ["静电能", "能量密度"],
}


def build_knowledge_graph_v5(results: list[DocumentParseResult], output_path: str | Path = "data/outputs/v5_reports/knowledge_graph_v5_report.json") -> dict:
    nodes = []
    edges = []
    for result in results:
        for page in result.pages:
            text = page.text or ""
            for concept_id, keywords in CONCEPT_KEYWORDS.items():
                if any(k in text for k in keywords):
                    node_id = f"{result.document_id}:p{page.page_number}:{concept_id}"
                    nodes.append(
                        {
                            "node_id": node_id,
                            "node_type": "concept_evidence",
                            "concept_id": concept_id,
                            "source_file": Path(result.file_path).name,
                            "page_number": page.page_number,
                            "parser_name": result.parser_name,
                            "confidence": 0.45 if result.parser_name == "fallback" else 0.75,
                            "snippet": text[:260],
                        }
                    )
            for match in re.finditer(r"(第?\s*\d+\s*题|\\b\\d+[\\.、])", text):
                nodes.append(
                    {
                        "node_id": f"{result.document_id}:p{page.page_number}:q{match.start()}",
                        "node_type": "question_candidate",
                        "source_file": Path(result.file_path).name,
                        "page_number": page.page_number,
                        "parser_name": result.parser_name,
                        "confidence": 0.35,
                    }
                )
    report = {"node_count": len(nodes), "edge_count": len(edges), "nodes": nodes[:500], "edges": edges}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/knowledge_graph/v5").mkdir(parents=True, exist_ok=True)
    Path("data/knowledge_graph/v5/knowledge_graph_v5.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
