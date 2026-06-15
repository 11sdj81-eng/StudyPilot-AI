"""StudyPilot AI — Natural-language goal parser.

Parses free-text Agent input into structured learning goals.
Rule-based for now; LLM interface reserved for future upgrade.
"""

from __future__ import annotations

import re

# ── Keyword sets ────────────────────────────────────────────────────────────

TIME_PATTERNS = [
    (r"(\d+)\s*小时", lambda m: f"{m.group(1)}小时"),
    (r"(\d+)\s*分钟", lambda m: f"{m.group(1)}分钟"),
    (r"(\d+)\s*天", lambda m: f"{m.group(1)}天"),
    (r"明天", lambda _: "1天"),
    (r"今天", lambda _: "几小时"),
    (r"还有\s*(\d+)", lambda m: f"{m.group(1)}小时"),
    (r"只剩\s*(\d+)", lambda m: f"{m.group(1)}小时"),
]

SCORE_PATTERNS = [
    (r"90\+", "90+"),
    (r"85\+", "85+"),
    (r"80\+", "80+"),
    (r"75\+", "75+"),
    (r"及格|60分|不挂科|能过", "及格"),
    (r"满分|100", "90+"),
]

MODE_PATTERNS = [
    (r"从头|系统学|精讲|复习|章节", "systematic_study"),
    (r"冲刺|快速|过一遍|抱佛脚|临时|着急|30分钟|半小时|考前", "exam_sprint"),
    (r"模拟|自测|查漏|检查|试卷", "mock_exam"),
    (r"真题|高频|往年|老师.*考|怎么考|考法", "past_paper"),
]

# Known EM / physics weak-point keywords
WEAK_POINT_KEYWORDS = [
    "高斯定理", "高斯", "通量",
    "镜像法", "镜像", "导体",
    "边界条件", "边界", "分界面",
    "电位", "电势", "电压",
    "静电场", "电场", "场强",
    "电容", "电介质", "介质",
    "安培", "环路", "磁场",
    "法拉第", "电磁感应", "感应",
    "麦克斯韦", "maxwell",
    "极化", "磁化",
    "散度", "旋度", "梯度",
    "泊松", "拉普拉斯", "laplace",
    "分离变量", "唯一性",
    "库仑", "毕奥", "萨伐尔",
]


def parse_goal_input(text: str) -> dict:
    """Parse free-text Agent input into structured learning goals.

    Args:
        text: User's natural-language input, e.g.
              "明天考电磁场，我只有3小时，高斯定理和镜像法不稳，帮我安排复习。"

    Returns:
        dict with keys:
            remaining_time (str | None)
            target_score (str | None)
            course (str | None)
            chapter (str | None)
            weak_points (list[str])
            mode (str | None)  — one of systematic_study / exam_sprint / mock_exam / past_paper
            raw_input (str)    — original text
    """
    result: dict = {
        "remaining_time": None,
        "target_score": None,
        "course": None,
        "chapter": None,
        "weak_points": [],
        "mode": None,
        "raw_input": text.strip(),
    }

    if not text or not text.strip():
        return result

    text_lower = text.lower().replace(" ", "")

    # ── remaining time ──
    for pattern, extractor in TIME_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            result["remaining_time"] = extractor(match)
            break

    # ── target score ──
    for pattern, score in SCORE_PATTERNS:
        if re.search(pattern, text_lower):
            result["target_score"] = score
            break

    # ── mode ──
    for pattern, mode in MODE_PATTERNS:
        if re.search(pattern, text_lower):
            result["mode"] = mode
            break

    # ── weak points ──
    for kw in WEAK_POINT_KEYWORDS:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            if kw not in result["weak_points"]:
                result["weak_points"].append(kw)

    # ── course detection ──
    course_map = [
        (r"电磁场|场波|电磁波|电动力学", "电磁场与电磁波"),
        (r"随机过程|概率", "随机过程"),
        (r"信号|系统分析|信号与系统", "信号与系统"),
        (r"数电|数字电路|数字电子", "数字电子技术"),
        (r"模电|模拟电路|模拟电子", "模拟电子技术"),
    ]
    for pattern, course_name in course_map:
        if re.search(pattern, text_lower):
            result["course"] = course_name
            break

    # ── chapter detection ──
    chapter_map = [
        (r"第一[章节]|静电场|静电", "第一章 静电场"),
        (r"第二[章节]|恒定电场|恒定电流|稳恒", "第二章 恒定电场"),
        (r"第三[章节]|恒定磁场|静磁|稳恒磁场", "第三章 恒定磁场"),
        (r"第四[章节]|时变|电磁感应|法拉第", "第四章 时变电磁场"),
        (r"第五[章节]|平面波|均匀平面", "第五章 均匀平面波"),
    ]
    for pattern, chapter_name in chapter_map:
        if re.search(pattern, text_lower):
            result["chapter"] = chapter_name
            break

    return result


# ── Reserved: LLM-backed parser interface ──────────────────────────────────

def parse_goal_input_llm(text: str, api_key: str | None = None) -> dict:
    """Reserved: Use DeepSeek to parse goal input with higher accuracy.

    Not yet implemented — falls back to rule-based parsing.
    """
    return parse_goal_input(text)
