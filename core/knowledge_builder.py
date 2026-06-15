"""Build KnowledgeGraph from parser results or golden chapter data."""

from __future__ import annotations

import json
from pathlib import Path

from core.knowledge_graph import KnowledgeGraph, KnowledgeNode, SourceRef


def build_graph_from_golden_chapter(chapter_dir: str | Path) -> KnowledgeGraph:
    base = Path(chapter_dir)
    graph = KnowledgeGraph()
    concepts = _load(base / "concepts.json")
    formulas = _load(base / "formulas.json")
    examples = _load(base / "examples.json")
    patterns = _load(base / "exam_patterns.json")
    diagrams = _load(base / "diagrams.json")
    for concept in concepts:
        graph.add_concept(_node(concept, "concept", concept["id"], concept["name"]))
    for formula in formulas:
        node = _node(formula, "formula", formula["id"], formula["display_name"])
        graph.add_formula(node, formula.get("concept_id", ""))
    for example in examples:
        node = _node(example, "example", example["id"], example["display_name"])
        for cid in example.get("concept_ids", []):
            graph.add_example(node, cid)
    for pattern in patterns:
        node = _node(pattern, "exam_pattern", pattern["id"], pattern["display_name"])
        for cid in pattern.get("concept_ids", []):
            graph.add_exam_pattern(node, cid)
    for diagram in diagrams:
        node = _node(diagram, "diagram", f"diagram:{diagram['id']}", diagram["display_name"])
        for cid in diagram.get("linked_concept_ids", []):
            graph.add_diagram(node, cid)
    return graph


def _node(item: dict, node_type: str, node_id: str, display_name: str) -> KnowledgeNode:
    refs = [
        SourceRef(
            source_id=str(ref.get("source_id", "")),
            file_name=str(ref.get("file_name", "")),
            page=str(ref.get("page", "")),
            note=str(ref.get("note", "")),
        )
        for ref in item.get("source_refs", [])
    ]
    return KnowledgeNode(
        id=node_id,
        display_name=display_name,
        node_type=node_type,
        source_refs=refs,
        confidence=float(item.get("confidence", 0.85)),
        subject_type=item.get("subject_type", "engineering"),
        chapter=item.get("chapter", "第一章 静电场"),
        tags=list(item.get("tags", [])),
        user_visible_text=item.get("user_visible_text", item.get("definition", "")),
        internal_metadata=item.get("internal_metadata", {}),
    )


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
