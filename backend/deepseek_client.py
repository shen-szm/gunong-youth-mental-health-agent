"""DeepSeek OpenAI 兼容接口封装。

与星火客户端不同：这里失败时显式抛异常，让上层能区分网络失败和模型返回空内容，
从而决定是重试、兜底还是降级，而不是静默返回空字符串。
"""
import httpx

from config import settings


class DeepSeekError(RuntimeError):
    """请求失败、鉴权失败或返回结构异常。"""


class DeepSeekEmptyResponse(DeepSeekError):
    """接口成功但 content 为空。"""


def is_deepseek_configured() -> bool:
    return bool(settings.DEEPSEEK_API_KEY)


async def ask_deepseek(messages: list, max_tokens: int = 1600, temperature: float = 0.85) -> str:
    if not settings.DEEPSEEK_API_KEY:
        raise DeepSeekError("DeepSeek API key is not configured")

    url = settings.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise DeepSeekError(f"DeepSeek request failed: {exc}") from exc

    if response.status_code != 200:
        raise DeepSeekError(f"DeepSeek HTTP {response.status_code}")

    try:
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content")
    except (ValueError, AttributeError, IndexError, TypeError) as exc:
        raise DeepSeekError("DeepSeek returned an unexpected payload") from exc

    if not isinstance(content, str) or not content.strip():
        finish_reason = choice.get("finish_reason")
        raise DeepSeekEmptyResponse(f"DeepSeek returned empty content (finish_reason={finish_reason})")
    return content.strip()
