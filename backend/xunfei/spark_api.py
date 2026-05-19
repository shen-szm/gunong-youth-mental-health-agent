"""
讯飞MaaS精调模型 HTTP API 封装
服务名：咕哝
接口地址：https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions
"""
import httpx
from config import settings

API_URL = "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
MODEL_NAME = "xop3qwen32b"
LORA_ID = "2054785584107061248"


async def ask_spark(messages: list, max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """
    调用讯飞MaaS精调模型获取回复
    messages: [{"role": "user", "content": "..."}, ...]
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SPARK_API_PASSWORD}",
        "lora_id": LORA_ID,
    }

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(API_URL, headers=headers, json=payload)
            data = resp.json()

        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {data}")

        # 提取回复内容
        choices = data.get("choices", [])
        if choices:
            reply = choices[0].get("message", {}).get("content", "")
            return reply.strip()

        raise Exception(f"MaaS API返回异常: {data}")

    except Exception as e:
        print(f"MaaS API调用失败: {e}")
        return ""


def is_spark_available() -> bool:
    """检查MaaS API是否已配置"""
    return bool(settings.SPARK_API_PASSWORD)
