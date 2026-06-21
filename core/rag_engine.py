"""v2.0 Step 2: RAG engine with hybrid retrieval (FAISS + BM25).

Returns (content, sources, figures) so the UI can render images separately.
Applies LaTeX cleaning before returning content.
"""

from core.config import DEFAULT_TOP_K
from core.content_utils import clean_latex
from core.deepseek_client import DeepSeekConfigError, call_deepseek
from core.figure_planner import plan_figures
from core.image_generator import safe_generate_figure
from core.prompt_templates import build_figure_plan_prompt, build_generation_prompt
from core.symbol_mapper import normalize_generated_content


def retrieve(course_id: str, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Hybrid retrieval: FAISS + BM25 → merge → rerank → top_k.

    Returns list of citation dicts with chunk_id, source_file, page, score, preview, text.
    """
    from core.hybrid_retrieval import hybrid_search
    return hybrid_search(course_id, query, top_k=top_k)


def generate_with_rag(
    task_type: str,
    user_request: str,
    course: dict,
    profile: dict,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[str, list[dict], list[dict]]:
    """Generate content with RAG and return (content, sources, figures).

    figures is a list of dicts: {title, caption, path, generated}
    """
    # 1. Retrieve
    chunks = retrieve(course["course_id"], user_request, top_k=top_k)

    # 2. Build prompt & call LLM
    prompt = build_generation_prompt(task_type, user_request, course, profile, chunks)
    content = call_deepseek(prompt)
    content = normalize_generated_content(content)

    # 3. Plan & generate teaching figures
    figure_prompt = build_figure_plan_prompt(content)
    figures = plan_figures(content, figure_prompt)

    generated_figures: list[dict] = []
    for idx, figure in enumerate(figures, start=1):
        filename = f"{course['course_id']}_{task_type}_{idx}.png"
        output_path = f"assets/generated/{filename}"
        generated = safe_generate_figure(figure, output_path)
        generated_figures.append({
            "title": figure.get("title", "教学示意图"),
            "caption": figure.get("caption", ""),
            "path": output_path,
            "generated": generated is not None,
            "template": figure.get("template", ""),
            "target_section": figure.get("target_section", ""),
        })

    # 4. Clean LaTeX for Streamlit
    content = clean_latex(content)

    return content, chunks, generated_figures


def generate_local_preview(
    task_type: str, user_request: str, course: dict, profile: dict
) -> tuple[str, list[dict], list[dict]]:
    content = f"""# StudyPilot AI 本地预览

未完成 DeepSeek 调用：{DeepSeekConfigError.__name__}

## 当前课程
{course.get("university", "")}《{course.get("course_name", "")}》

## 学习画像
目标：{profile.get("goal")}
基础：{profile.get("level")}
每日学习：{profile.get("daily_hours")} 小时
剩余天数：{profile.get("remaining_days")} 天

## 你的需求
{user_request}

## 下一步
请在 `.env` 中配置 `DEEPSEEK_API_KEY` 后重新生成。已上传资料仍可保存在本地资料库，并可建立课程级检索索引。
"""
    return content, [], []
