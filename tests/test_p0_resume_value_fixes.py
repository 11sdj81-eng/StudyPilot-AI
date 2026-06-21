import json
from pathlib import Path

from core.ai_tutor.citation_quality import filter_citations, score_citation
from core.ai_tutor.intent_router import Intent, IntentResult
from core.ai_tutor.orchestrator import AITutorOrchestrator


class FakeStatus:
    available = True


class FakeLLM:
    def __init__(self, responses):
        self.status = FakeStatus()
        self.responses = list(responses)
        self.calls = []

    def _call(self, messages, temperature=0.5, max_tokens=1024):
        self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        return {"text": self.responses.pop(0), "tokens": 100}


def test_citation_quality_rejects_directory_garbled_low_score_and_off_topic():
    directory = {"text": "封面 书名 版权 前言 目录 第1章 概率论的基本概念", "score": 0.12}
    garbled = {"text": "2 2 2 0 0 0 / ( ) η π µε ∂ ∇  ϕ =====", "score": 0.12}
    low_score = {"text": "镜像法通过镜像电荷满足接地导体平面的边界条件。", "score": 0.005}
    off_topic = {"text": "高斯定理用于对称电荷分布的电场计算。", "score": 0.12}
    accepted = {"text": "镜像法通过设置镜像电荷来满足接地导体边界条件。", "score": 0.12}

    assert score_citation(directory, "镜像法是什么")["reason"] == "directory"
    assert score_citation(garbled, "镜像法是什么")["reason"] == "garbled"
    assert score_citation(low_score, "镜像法是什么")["reason"] == "low_score"
    assert score_citation(off_topic, "镜像法是什么")["reason"] == "off_topic"
    assert score_citation(accepted, "镜像法是什么")["accepted"] is True

    good, rejected = filter_citations([directory, garbled, low_score, off_topic, accepted], "镜像法是什么")
    assert len(good) == 1
    assert {r["reason"] for r in rejected} == {"directory", "garbled", "low_score", "off_topic"}


def test_quiz_prompt_binds_first_two_questions_to_weak_points(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    Path("data/student_profile.json").write_text(
        json.dumps({"field_wave_ch1": {"weak_points": ["镜像法"]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    content = "\n".join(
        [
            "题目1：镜像法是什么？\n答案：A\n评分点：镜像法",
            "题目2：镜像法如何设置镜像电荷？\n答案：B\n评分点：镜像法",
            "题目3：高斯定理\n答案：C\n评分点：高斯定理",
            "题目4：电位\n答案：D\n评分点：电位",
            "题目5：边界条件\n答案：E\n评分点：边界条件",
            "END_OF_QUIZ",
        ]
    )
    tutor = AITutorOrchestrator()
    tutor._llm = FakeLLM([content])
    ctx = {
        "course_id": "field_wave_ch1",
        "course_name": "电磁场与电磁波 第一章 静电场",
        "course_topics": ["镜像法", "高斯定理"],
        "rag_context": "",
        "seed_context": "",
        "has_materials": False,
        "weak_points": tutor._load_weak_points("field_wave_ch1"),
    }
    result = tutor._try_llm("给我出5道题", IntentResult(Intent.QUIZ, 0.8, False, "test"), ctx, None)

    prompt = tutor._llm.calls[0]["messages"][-1]["content"]
    assert "学生薄弱点：镜像法" in prompt
    assert "前2道题必须围绕学生薄弱点：镜像法" in prompt
    assert "END_OF_QUIZ" not in result["content"]
    assert result["content"].count("题目") >= 5


def test_mock_exam_auto_continues_until_complete():
    first = "一、选择题\n1. 镜像法用于什么？\n答案：B\n二、填空题\n1. 镜像电荷为"
    second = (
        "-q\n三、计算题\n1. 点电荷镜像法计算。\n解：设置镜像电荷。\n"
        "四、综合题\n1. 接地平面镜像法综合题。\n解：写出电位并验证边界。\n"
        "五、参考答案\n选择题：B。填空题：-q。计算题和综合题见解答。\nEND_OF_EXAM"
    )
    tutor = AITutorOrchestrator()
    tutor._llm = FakeLLM([first, second])
    ctx = {
        "course_id": "field_wave_ch1",
        "course_name": "电磁场与电磁波 第一章 静电场",
        "course_topics": ["镜像法", "高斯定理"],
        "rag_context": "",
        "seed_context": "",
        "has_materials": False,
        "weak_points": ["镜像法"],
    }
    result = tutor._try_llm("生成模拟卷", IntentResult(Intent.MOCK_EXAM, 0.85, False, "test"), ctx, None)

    assert len(tutor._llm.calls) == 2
    assert "四、综合题" in result["content"]
    assert "五、参考答案" in result["content"]
    assert "END_OF_EXAM" not in result["content"]


def test_no_accepted_citations_marks_llm_general():
    class FakeContextBuilder:
        def build(self, course_id, user_input):
            return {
                "course_id": course_id,
                "course_name": "电磁场与电磁波 第一章 静电场",
                "course_topics": ["镜像法"],
                "rag_context": "",
                "seed_context": "",
                "has_materials": False,
            }

        def get_citations(self):
            return []

        def get_rejected_citations(self):
            return [{"reason": "garbled", "preview": "2 2 2 ∇ "}]

    tutor = AITutorOrchestrator()
    tutor.context_builder = FakeContextBuilder()
    tutor._llm = FakeLLM(["① 一句话理解：镜像法。\n② 为什么重要：重要。\n③ 教材/资料怎么说：通用AI讲解。"])

    result = tutor.handle("镜像法是什么", "field_wave_ch1", "电磁场与电磁波")
    assert result["source"] == "LLM_GENERAL"
    assert result["citations"] == []
    assert result["rejected_citations"][0]["reason"] == "garbled"
