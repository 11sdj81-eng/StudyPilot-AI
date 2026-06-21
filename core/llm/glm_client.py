"""GLM Client — connects StudyPilot to ZhipuAI GLM models.

Supports: GLM-4-Flash, GLM-4, GLM-3-Turbo
Fallback: DeepSeek if GLM key missing, else rule-based.
Never pretends AI is enabled when no key is configured.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Status
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LLMStatus:
    provider: str = ""              # "glm" / "deepseek" / "none"
    model: str = ""
    available: bool = False
    reason: str = ""                # Why unavailable, if not available
    last_call_ms: float = 0
    total_calls: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "reason": self.reason,
            "last_call_ms": self.last_call_ms,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
        }

    @property
    def display_label(self) -> str:
        if self.available:
            return f"🟢 {self.provider.upper()} connected ({self.model})"
        elif "missing" in self.reason.lower():
            return f"🔴 LLM disabled: missing API key"
        else:
            return f"🟡 Rule-based fallback ({self.reason})"


# ═══════════════════════════════════════════════════════════════════════════
# Client
# ═══════════════════════════════════════════════════════════════════════════

class GLMClient:
    """Unified LLM client. Priority: GLM > DeepSeek > rule-based fallback.

    NEVER pretends AI is enabled when no key is configured.
    """

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    DEFAULT_MODEL = "glm-4-flash"
    SYSTEM_PROMPT = """你是 StudyPilot AI Tutor，一名严谨且亲切的大学课程讲师。

你的特点：
- 像真正的老师一样讲解，用"注意"、"考点"、"容易错"等口语化提醒
- 结合教材和真题来解释为什么考、怎么考、怎么拿分
- 给具体例子，不泛泛而谈
- 每个解释都标注来源（教材推导 / 真题改编 / AI生成）

禁止：
- 编造教材页码、真题年份、学校来源
- 空洞的套话如"该知识点很重要，建议掌握"
- 在非概率论课程中使用概率论术语，反之亦然"""

    def __init__(self):
        self.status = LLMStatus()
        self._detect_provider()
        self._session = None

    def _detect_provider(self) -> None:
        """Detect which LLM provider is available."""
        glm_key = os.environ.get("GLM_API_KEY") or os.environ.get("ZHIPUAI_API_KEY")
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

        if glm_key and glm_key not in ("", "YOUR_API_KEY_HERE", "sk-your-key"):
            self.status.provider = "glm"
            self.status.model = self.DEFAULT_MODEL
            self.status.available = True
            self._api_key = glm_key
        elif deepseek_key and deepseek_key not in ("", "YOUR_API_KEY_HERE", "sk-your-key"):
            self.status.provider = "deepseek"
            self.status.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
            self.status.available = True
            self._api_key = deepseek_key
        else:
            self.status.provider = "none"
            self.status.model = ""
            self.status.available = False
            self.status.reason = "LLM_DISABLED_MISSING_API_KEY"
            self._api_key = ""

    def _call(self, messages: list[dict], temperature: float = 0.4,
              max_tokens: int = 2048) -> dict:
        """Call the LLM API. Returns {"text": ..., "tokens": ...} or {"error": ...}."""
        if not self.status.available:
            return {"error": "LLM_DISABLED_MISSING_API_KEY", "text": ""}

        start = time.perf_counter()
        try:
            import requests

            if self.status.provider == "glm":
                url = self.BASE_URL
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": self.status.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            else:  # deepseek
                url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com") + "/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                body = {
                    "model": self.status.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }

            resp = requests.post(url, headers=headers, json=body, timeout=120)
            elapsed = (time.perf_counter() - start) * 1000
            self.status.last_call_ms = round(elapsed, 1)
            self.status.total_calls += 1

            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}", "text": ""}

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            tokens = data.get("usage", {}).get("total_tokens", 0)
            self.status.total_tokens += tokens

            return {"text": content.strip(), "tokens": tokens, "ms": round(elapsed, 1)}

        except Exception as e:
            return {"error": str(e), "text": ""}

    # ═══════════════════════════════════════════════════════════════════════
    # High-level generation methods
    # ═══════════════════════════════════════════════════════════════════════

    def generate_teacher_explanation(self, concept: str, course: str,
                                     context: str = "") -> dict:
        """Generate a teacher-style explanation for a concept."""
        if not self.status.available:
            return {
                "text": f"[RULE_BASED_FALLBACK] {concept}是{course}中的重要知识点。请参考教材获取详细讲解。",
                "source_level": "RULE_BASED_FALLBACK",
                "tokens": 0,
            }

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""你是{course}的讲师。请用老师口吻讲解以下知识点：

知识点：{concept}
参考资料：{context if context else '教材内容'}

要求：
1. 用"老师提醒"开头，口语化讲解
2. 说明为什么考试喜欢考这个点
3. 说明常见考法（题型、分值）
4. 提醒最容易错的地方
5. 给出一个具体的小例子
6. 150-300字，不要空洞套话"""},
        ]
        result = self._call(messages, temperature=0.5, max_tokens=1024)
        if result.get("error"):
            return {
                "text": f"[RULE_BASED_FALLBACK] {concept}讲解生成失败: {result['error'][:100]}",
                "source_level": "RULE_BASED_FALLBACK",
                "tokens": 0,
            }
        return {
            "text": result["text"],
            "source_level": "AI_DERIVED",
            "tokens": result.get("tokens", 0),
        }

    def generate_concept_summary(self, concept: str, course: str,
                                  key_points: list[str] | None = None) -> dict:
        """Generate a concise concept summary."""
        if not self.status.available:
            points_text = "；".join(key_points or [])
            return {
                "text": f"[RULE_BASED_FALLBACK] {concept}：{points_text or '请参考教材。'}",
                "source_level": "RULE_BASED_FALLBACK",
                "tokens": 0,
            }

        points_str = "\n".join(f"- {p}" for p in (key_points or []))
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""用3-5句话总结{course}中"{concept}"这个知识点。

关键要点：
{points_str or '（从教材提取）'}

要求：简洁、准确、适合考前快速回顾。标注"AI生成总结"。"""},
        ]
        result = self._call(messages, temperature=0.3, max_tokens=512)
        if result.get("error"):
            return {"text": f"[RULE_BASED_FALLBACK] 总结生成失败", "source_level": "RULE_BASED_FALLBACK", "tokens": 0}
        return {"text": result["text"], "source_level": "AI_DERIVED", "tokens": result.get("tokens", 0)}

    def generate_exam_analysis(self, concept: str, course: str,
                               exam_data: str = "") -> dict:
        """Generate exam-focused analysis: why tested, how tested, scoring."""
        if not self.status.available:
            return {
                "why_tested": f"[RULE_BASED_FALLBACK] {concept}是基础考点。",
                "how_tested": "[RULE_BASED_FALLBACK] 通常以选择题/计算题形式出现。",
                "scoring_tips": "[RULE_BASED_FALLBACK] 掌握公式和适用条件即可得分。",
                "source_level": "RULE_BASED_FALLBACK",
            }

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""分析{course}中"{concept}"的考试情况。

已知真题数据：{exam_data if exam_data else '教材例题和课后题'}

请输出（每项2-3句话）：
1. 为什么考：这个知识点为什么是考试重点
2. 怎么考：常见题型和考法
3. 怎么拿分：评分要点和得分技巧
4. 怎么错：最常见的错误和避免方法"""},
        ]
        result = self._call(messages, temperature=0.4, max_tokens=1024)
        if result.get("error"):
            return {
                "why_tested": f"[RULE_BASED_FALLBACK] {concept}是重要考点。",
                "how_tested": "[RULE_BASED_FALLBACK] 多种题型均可能涉及。",
                "scoring_tips": "[RULE_BASED_FALLBACK] 注意公式适用条件。",
                "source_level": "RULE_BASED_FALLBACK",
            }

        text = result["text"]
        # Parse the LLM output into sections
        sections = {"source_level": "AI_DERIVED"}
        current_key = None
        for line in text.split("\n"):
            line = line.strip()
            if "为什么考" in line or "考试重点" in line:
                current_key = "why_tested"
            elif "怎么考" in line or "题型" in line:
                current_key = "how_tested"
            elif "怎么拿分" in line or "得分" in line or "评分" in line:
                current_key = "scoring_tips"
            elif "怎么错" in line or "错误" in line or "避免" in line:
                current_key = "common_mistakes"
            elif current_key and line:
                sections[current_key] = (sections.get(current_key, "") + line + " ").strip()

        return sections

    def generate_practice_questions(self, concept: str, course: str,
                                    count: int = 5, qtype: str = "mixed") -> dict:
        """Generate practice questions for a concept."""
        if not self.status.available:
            return {
                "questions": [
                    {
                        "stem": f"[RULE_BASED_FALLBACK] 关于{concept}，下列说法正确的是：",
                        "type": "选择题",
                        "answer": f"请参考{concept}的教材定义。",
                    }
                ],
                "source_level": "RULE_BASED_FALLBACK",
            }

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""为{course}中的"{concept}"生成{count}道练习题。

题型分布：{qtype}（选择题:填空题:计算题=2:2:1）

要求：
- 每道题必须有：题干、标准答案、评分点
- 题目必须是具体计算/判断，不能是"设与XX相关的场景，写出公式"
- 概率论用具体分布和数字，如"设X~B(10,0.2)，求P(X=2)"
- 场波用具体电荷/电场场景，如"半径为a的均匀带电球体，总电荷Q"
- 数电用具体逻辑表达式，如"用卡诺图化简F(A,B,C,D)=Σm(0,2,5,7,8,10,13,15)"
- 标注每道题的来源为AI_GENERATED

输出格式：每道题一行，格式为"题号|题型|题干|答案|评分点" """},
        ]
        result = self._call(messages, temperature=0.5, max_tokens=2048)
        if result.get("error"):
            return {
                "questions": [{"stem": f"[RULE_BASED_FALLBACK] {concept}练习题", "type": "选择题", "answer": "见教材"}],
                "source_level": "RULE_BASED_FALLBACK",
            }

        # Parse questions from LLM output
        questions = []
        for line in result["text"].split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("输出"):
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                questions.append({
                    "stem": parts[2].strip() if len(parts) > 2 else "",
                    "type": parts[1].strip() if len(parts) > 1 else "选择题",
                    "answer": parts[3].strip() if len(parts) > 3 else "",
                    "grading": parts[4].strip() if len(parts) > 4 else "",
                    "source_level": "AI_GENERATED",
                })

        return {
            "questions": questions[:count] if questions else [
                {"stem": f"[PARSE_FALLBACK] {result['text'][:200]}", "type": "简答题", "answer": "见上文"}
            ],
            "source_level": "AI_DERIVED",
        }

    def review_pdf_content(self, content: str, course: str) -> dict:
        """Review and improve PDF content with AI."""
        if not self.status.available:
            return {
                "text": content,
                "improvements": [],
                "source_level": "RULE_BASED_FALLBACK",
            }

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""审阅以下{course}讲义内容，提出改进建议：

{content[:3000]}

检查：
1. 是否像老师在讲课，还是像教材摘要？
2. 是否有空洞套话？
3. 是否有跨课程污染（出现其他课程术语）？
4. 是否有模板化题目？
5. 排版和可读性如何？

输出：
- 改进后的版本（保持原长度）
- 3-5条具体改进建议"""},
        ]
        result = self._call(messages, temperature=0.3, max_tokens=2048)
        if result.get("error"):
            return {"text": content, "improvements": [], "source_level": "RULE_BASED_FALLBACK"}

        return {
            "text": result["text"],
            "improvements": ["AI reviewed — see revised text"],
            "source_level": "AI_REVIEWED",
        }


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

_glm: GLMClient | None = None


def get_llm() -> GLMClient:
    global _glm
    if _glm is None:
        _glm = GLMClient()
    return _glm


def get_llm_status() -> LLMStatus:
    return get_llm().status
