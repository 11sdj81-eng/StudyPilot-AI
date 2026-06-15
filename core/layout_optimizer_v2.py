"""Layout policy metadata for v1.1 rebuilt PDFs."""

from __future__ import annotations


def layout_policy_v2(task_type: str) -> dict:
    return {
        "task_type": task_type,
        "keep_question_figure_solution_together": True,
        "avoid_large_blank_page": True,
        "avoid_lonely_figures": True,
        "table_wrap": True,
        "callout_colors": {
            "技巧": "blue",
            "易错": "red",
            "考试提醒": "orange",
        },
        "goodnotes_friendly": True,
        "notes": "题目之后立即配图，配图之后进入思路和标准答案；长表格自动换行。",
    }
