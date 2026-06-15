"""Load StudyPilot v2.0 structured study databases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import ROOT_DIR
from core.formula_service import validate_formula_db
from core.study_objects import ConceptCard, DiagramBlock, ExampleCard, FormulaCard, SolutionBlock


DEFAULT_BANK = ROOT_DIR / "data" / "local_question_bank" / "engineering" / "electromagnetic_static.json"


class StudyDatabase:
    def __init__(self, raw: dict[str, Any], path: Path) -> None:
        self.raw = raw
        self.path = path
        self.subject_type = raw.get("subject_type", "engineering")
        self.course_name = raw.get("course_name", "")
        self.chapter = raw.get("chapter", "")
        self.concepts = {item["id"]: ConceptCard(**item) for item in raw.get("concept_db", [])}
        self.formulas = {item["id"]: FormulaCard(**item) for item in raw.get("formula_db", [])}
        validate_formula_db(self.formulas)
        self.examples = {
            item["id"]: ExampleCard(
                id=item["id"],
                source_type=item["source_type"],
                source_ref=item["source_ref"],
                concept_ids=item["concept_ids"],
                question_type=item["question_type"],
                difficulty=float(item["difficulty"]),
                question=item["question"],
                diagram_required=bool(item["diagram_required"]),
                diagram_type=item.get("diagram_type", ""),
                solution=SolutionBlock(
                    steps=list(item.get("solution_steps", [])),
                    answer=item.get("answer", ""),
                    common_mistakes=list(item.get("common_mistakes", [])),
                ),
                variants=list(item.get("variants", [])),
                required_formulas=list(item.get("required_formulas", [])),
            )
            for item in raw.get("example_db", [])
        }
        self.exam_patterns = {item["id"]: item for item in raw.get("exam_pattern_db", [])}
        self.diagrams = {item["id"]: DiagramBlock(**item) for item in raw.get("diagram_db", [])}

    def concept_formulas(self, concept_id: str) -> list[FormulaCard]:
        concept = self.concepts[concept_id]
        return [self.formulas[fid] for fid in concept.related_formulas if fid in self.formulas]

    def concept_examples(self, concept_id: str) -> list[ExampleCard]:
        return [example for example in self.examples.values() if concept_id in example.concept_ids]

    def diagram_for_type(self, diagram_type: str) -> DiagramBlock | None:
        for diagram in self.diagrams.values():
            if diagram.diagram_type == diagram_type:
                return diagram
        return None


def load_study_database(path: str | Path | None = None) -> StudyDatabase:
    db_path = Path(path) if path else DEFAULT_BANK
    raw = json.loads(db_path.read_text(encoding="utf-8"))
    return StudyDatabase(raw, db_path)
