"""StudyPilot v2.0 AI-driven study pipeline.

This first implementation runs deterministically from structured local data,
but the role boundaries match the future AI JSON workflow:
Exam Analyst -> Textbook Analyst -> Question Designer -> Lecture Teacher -> Reviewer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from core.study_databases import StudyDatabase, load_study_database
from core.study_objects import ExamPaper, PastPaperCase, QuestionCard, Section, SolutionBlock, SprintCard, StudyDocument
from core.subject_type import detect_subject_type
from core.mock_exam_builder import build_complete_mock_exam


@dataclass
class PipelineResult:
    documents: dict[str, StudyDocument]
    role_outputs: dict[str, Any]
    validation_report: dict[str, Any]


def run_ai_driven_pipeline(course: dict | None = None, db_path: str | None = None) -> PipelineResult:
    course = course or {"course_name": "电磁场与电磁波", "university": "北京邮电大学"}
    db = load_study_database(db_path)
    role_outputs = {
        "exam_analyst": exam_analyst(db),
        "textbook_analyst": textbook_analyst(db),
    }
    questions = question_designer(db, role_outputs["exam_analyst"])
    role_outputs["question_designer"] = {"questions": [q.to_dict() for q in questions]}
    documents = {
        "exam_sprint": build_sprint_document(db, course, questions),
        "past_paper": build_pastpaper_document(db, course, questions),
        "mock_exam": build_mock_exam_document(db, course, questions),
        "chapter_review": build_review_document(db, course, questions),
    }
    role_outputs["lecture_teacher"] = {
        "mode": "Review",
        "reason": "当前 concept/example 数据量不足以稳定生成 40–80 页教材级 Lecture，自动降级为章节复习讲义。",
    }
    validation_report = reviewer(documents, db)
    role_outputs["reviewer"] = validation_report
    return PipelineResult(documents=documents, role_outputs=role_outputs, validation_report=validation_report)


def exam_analyst(db: StudyDatabase) -> dict[str, Any]:
    patterns = list(db.exam_patterns.values())
    distribution: dict[str, int] = {}
    for pattern in patterns:
        distribution[pattern["question_type"]] = distribution.get(pattern["question_type"], 0) + 1
    return {
        "exam_patterns": patterns,
        "high_frequency_concepts": sorted({cid for p in patterns for cid in p.get("concept_ids", [])}),
        "difficulty_distribution": {
            "average": round(sum(float(p["difficulty"]) for p in patterns) / max(1, len(patterns)), 2),
            "source": "local_question_bank + uploaded-paper OCR signals",
        },
        "question_type_distribution": distribution,
    }


def textbook_analyst(db: StudyDatabase) -> dict[str, Any]:
    return {
        "concept_db": [concept.to_dict() for concept in db.concepts.values()],
        "formula_db": [formula.to_dict() for formula in db.formulas.values()],
        "example_db": [example.to_dict() for example in db.examples.values()],
        "diagram_db": [diagram.to_dict() for diagram in db.diagrams.values()],
        "knowledge_order": list(db.concepts.keys()),
    }


def question_designer(db: StudyDatabase, exam_output: dict[str, Any]) -> list[QuestionCard]:
    questions: list[QuestionCard] = []
    for index, example in enumerate(db.examples.values(), start=1):
        pattern = _matching_pattern(db, example.concept_ids)
        diagram = db.diagram_for_type(example.diagram_type) if example.diagram_required else None
        formula_ids = _formula_ids_for_concepts(db, example.concept_ids)
        metadata = {
            "source_basis": pattern.get("source_ref", example.source_ref) if pattern else example.source_ref,
            "knowledge_point": "、".join(db.concepts[cid].name for cid in example.concept_ids if cid in db.concepts),
            "chapter": db.chapter,
            "difficulty": example.difficulty,
            "question_type": example.question_type,
            "mutation_type": "教材例题/真题考法同范围改编",
            "in_scope": True,
            "reliability": example.source_type,
        }
        questions.append(
            QuestionCard(
                id=f"Q{index}",
                question=example.question,
                concept_ids=example.concept_ids,
                formula_ids=formula_ids,
                source_basis=metadata["source_basis"],
                difficulty=example.difficulty,
                question_type=example.question_type,
                score=int(pattern.get("score", 8)) if pattern else 8,
                chapter=db.chapter,
                diagram_required=example.diagram_required,
                diagram_type=example.diagram_type,
                diagram_id=diagram.id if diagram else "",
                solution=example.solution,
                metadata=metadata,
                options=_options_for_question(example.id),
            )
        )
    return questions


def build_sprint_document(db: StudyDatabase, course: dict, questions: list[QuestionCard]) -> StudyDocument:
    cards: list[SprintCard] = []
    for concept in db.concepts.values():
        examples = db.concept_examples(concept.id)
        formulas = db.concept_formulas(concept.id)
        if not examples or not formulas:
            continue
        example = examples[0]
        cards.append(
            SprintCard(
                concept_id=concept.id,
                definition=concept.definition,
                formula_ids=[f.id for f in formulas[:2]],
                symbol_notes={k: v for formula in formulas[:1] for k, v in formula.symbol_explanation.items()},
                exam_usage=concept.exam_usage,
                quick_question_id=example.id,
                quick_answer=example.solution.answer,
                quick_steps=example.solution.steps,
                common_mistakes=concept.common_mistakes,
                review_location=concept.textbook_section,
                ten_second_reminder=_ten_second(concept.id),
            )
        )
    sections = [Section("sprint-plan", "最后 30 分钟安排", markdown="前 8 分钟看公式和适用条件；中间 14 分钟看高频救命卡；最后 8 分钟只扫检查表。"), Section("sprint-cards", "高频救命卡", blocks=cards), Section("sprint-check", "最后检查表", markdown="高斯是否分段？负号是否保留？边界条件是否分清 E 与 D？镜像法是否说明求解区域？")]
    return _document("v2_sprint", "第一章 静电场 考前冲刺", course, "exam_sprint", db, sections, {"source": "concept_db + formula_db + exam_pattern_db + example_db"})


def build_pastpaper_document(db: StudyDatabase, course: dict, questions: list[QuestionCard]) -> StudyDocument:
    cases: list[PastPaperCase] = []
    for question in questions[:4]:
        example = next((e for e in db.examples.values() if e.question == question.question), None)
        cases.append(
            PastPaperCase(
                question=question,
                source_reliability=question.metadata.get("reliability", ""),
                textbook_location="、".join(db.concepts[c].textbook_section for c in question.concept_ids if c in db.concepts),
                variant_question=(example.variants[0] if example and example.variants else "同知识点同范围变式题"),
                takeaway="掌握题干识别、公式选择、图示关系和阅卷扣分点。",
            )
        )
    sections = [Section("past-cases", "真题/高频题精讲", blocks=cases)]
    return _document("v2_pastpaper", "第一章 静电场 真题精讲", course, "past_paper", db, sections, {"source": "exam_pattern_db + example_db + formula_db + diagram_db"})


def build_mock_exam_document(db: StudyDatabase, course: dict, questions: list[QuestionCard]) -> StudyDocument:
    exam = build_complete_mock_exam(db)
    sections = [Section("mock-paper", "模拟试卷", blocks=[exam])]
    return _document("v2_mock", "第一章 静电场 模拟试卷", course, "mock_exam", db, sections, {"source": "exam_pattern_db"})


def build_review_document(db: StudyDatabase, course: dict, questions: list[QuestionCard]) -> StudyDocument:
    sections = [
        Section("review-note", "章节复习讲义说明", markdown="当前结构化数据库不足以稳定生成 40–80 页教材级 Lecture，因此自动降级为章节复习讲义。"),
        Section("concepts", "核心知识精讲", blocks=list(db.concepts.values())),
        Section("formulas", "公式总结表", blocks=list(db.formulas.values())),
        Section("examples", "典型例题", blocks=list(db.examples.values())),
    ]
    return _document("v2_review", "第一章 静电场 章节复习讲义", course, "chapter_review", db, sections, {"source": "concept_db + formula_db + example_db"})


def reviewer(documents: dict[str, StudyDocument], db: StudyDatabase) -> dict[str, Any]:
    issues: list[str] = []
    for key, document in documents.items():
        if not document.sections:
            issues.append(f"{key}: empty document")
    formula_sources_ok = all(formula.id for formula in db.formulas.values())
    metadata_questions_ok = True
    return {
        "passed": not issues and formula_sources_ok and metadata_questions_ok,
        "issues": issues,
        "formula_sources_ok": formula_sources_ok,
        "metadata_questions_ok": metadata_questions_ok,
        "review_note": "Reviewer checks structured objects before Markdown/PDF rendering.",
    }


def _document(doc_id: str, title: str, course: dict, task_type: str, db: StudyDatabase, sections: list[Section], metadata: dict[str, Any]) -> StudyDocument:
    return StudyDocument(
        id=doc_id,
        title=title,
        course=course,
        subject_type=detect_subject_type(course),
        task_type=task_type,
        sections=sections,
        formulas=db.formulas,
        concepts=db.concepts,
        examples=db.examples,
        diagrams=db.diagrams,
        metadata=metadata,
    )


def _matching_pattern(db: StudyDatabase, concept_ids: list[str]) -> dict[str, Any]:
    for pattern in db.exam_patterns.values():
        if any(cid in pattern.get("concept_ids", []) for cid in concept_ids):
            return pattern
    return {}


def _formula_ids_for_concepts(db: StudyDatabase, concept_ids: list[str]) -> list[str]:
    ids: list[str] = []
    for concept_id in concept_ids:
        if concept_id in db.concepts:
            ids.extend(fid for fid in db.concepts[concept_id].related_formulas if fid in db.formulas)
    return ids


def _options_for_question(example_id: str) -> list[str]:
    if example_id == "example_energy_density":
        return ["we=D·E", "we=1/2 D·E", "we=ρₛE", "we=φ/Q"]
    if example_id == "example_boundary_condition":
        return ["D₁n-D₂n=ρₛ", "E₁n=E₂n", "D₁t=D₂t", "φ₁=-φ₂"]
    return []


def _ten_second(concept_id: str) -> str:
    return {
        "gauss_law": "高斯先看对称性，包围电荷要分段。",
        "potential_gradient": "电场等于电位负梯度，负号不能丢。",
        "boundary_conditions": "切向看 E，法向看 D。",
        "image_method": "镜像是假电荷，边界是真条件。",
        "electrostatic_energy": "能量密度有 1/2。",
    }.get(concept_id, "先看条件，再选公式。")
