"""StudyPilot v3 lightweight knowledge graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceRef:
    source_id: str
    file_name: str
    page: str = ""
    note: str = ""


@dataclass
class KnowledgeNode:
    id: str
    display_name: str
    node_type: str
    source_refs: list[SourceRef] = field(default_factory=list)
    confidence: float = 0.8
    subject_type: str = "engineering"
    chapter: str = ""
    tags: list[str] = field(default_factory=list)
    user_visible_text: str = ""
    internal_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_refs"] = [asdict(ref) for ref in self.source_refs]
        return data


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[dict[str, str]] = []

    def add_concept(self, node: KnowledgeNode) -> None:
        self._add(node, "concept")

    def add_formula(self, node: KnowledgeNode, concept_id: str = "") -> None:
        self._add(node, "formula")
        if concept_id:
            self.edges.append({"from": concept_id, "to": node.id, "type": "has_formula"})

    def add_example(self, node: KnowledgeNode, concept_id: str = "") -> None:
        self._add(node, "example")
        if concept_id:
            self.edges.append({"from": concept_id, "to": node.id, "type": "has_example"})

    def add_exam_pattern(self, node: KnowledgeNode, concept_id: str = "") -> None:
        self._add(node, "exam_pattern")
        if concept_id:
            self.edges.append({"from": concept_id, "to": node.id, "type": "tested_by"})

    def add_diagram(self, node: KnowledgeNode, concept_id: str = "") -> None:
        self._add(node, "diagram")
        if concept_id:
            self.edges.append({"from": concept_id, "to": node.id, "type": "needs_diagram"})

    def get_concepts_by_chapter(self, chapter: str) -> list[KnowledgeNode]:
        return [n for n in self.nodes.values() if n.node_type == "concept" and n.chapter == chapter]

    def get_examples_by_concept(self, concept_id: str) -> list[KnowledgeNode]:
        return self._neighbors(concept_id, "has_example")

    def get_exam_patterns_by_concept(self, concept_id: str) -> list[KnowledgeNode]:
        return self._neighbors(concept_id, "tested_by")

    def get_formulas_by_concept(self, concept_id: str) -> list[KnowledgeNode]:
        return self._neighbors(concept_id, "has_formula")

    def export_json(self) -> dict[str, Any]:
        return {"nodes": {k: v.to_dict() for k, v in self.nodes.items()}, "edges": self.edges}

    def _add(self, node: KnowledgeNode, node_type: str) -> None:
        node.node_type = node_type
        self.nodes[node.id] = node

    def _neighbors(self, concept_id: str, edge_type: str) -> list[KnowledgeNode]:
        ids = [e["to"] for e in self.edges if e["from"] == concept_id and e["type"] == edge_type]
        return [self.nodes[i] for i in ids if i in self.nodes]
