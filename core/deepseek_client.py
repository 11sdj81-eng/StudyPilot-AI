import os

import certifi
import requests
from dotenv import load_dotenv

load_dotenv()


class DeepSeekConfigError(RuntimeError):
    pass


def call_deepseek(
    prompt: str,
    system_prompt: str = (
        "你是 StudyPilot AI，一名严谨、善于讲解的大学课程学习教练。"
        "你必须使用标准 Markdown LaTeX 书写所有数学公式：行内公式用 $...$，独立公式用 $$...$$。"
        "绝对不要使用 \\[ ... \\] 或裸露的 LaTeX 命令。"
        "输出风格应像正式大学期末复习讲义，不要写成聊天回答。"
    ),
    temperature: float = 0.4,
) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        raise DeepSeekConfigError("未配置 DEEPSEEK_API_KEY。请在 .env 中填写 DeepSeek API Key 后重试。")

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=90,
            verify=certifi.where(),
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.HTTPError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        raise RuntimeError(f"DeepSeek API 调用失败：{detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"DeepSeek API 调用异常：{exc}") from exc
