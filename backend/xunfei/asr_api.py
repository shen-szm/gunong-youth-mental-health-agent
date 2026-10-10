"""
讯飞语音转文字（实时语音识别 IAT API）
文档：https://www.xfyun.cn/doc/asr/voicedictation/API.html
使用 WebSocket 流式识别
"""
import json
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import urlencode
import websockets
from config import settings

# 每帧发送的音频数据大小（字节），约 40ms 的 16kHz 16bit 单声道音频
FRAME_SIZE = 1280


def _create_asr_auth_url():
    """生成语音识别WebSocket认证URL"""
    app_id = settings.XUNFEI_APP_ID
    api_key = settings.XUNFEI_API_KEY
    api_secret = settings.XUNFEI_API_SECRET
    host = "iat-api.xfyun.cn"
    path = "/v2/iat"

    now = datetime.utcnow()
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    signature_origin = f"host: {host}\n"
    signature_origin += f"date: {date}\n"
    signature_origin += f"GET {path} HTTP/1.1"

    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")

    authorization = base64.b64encode(
        f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'.encode("utf-8")
    ).decode("utf-8")

    return f"wss://{host}{path}?{urlencode({'authorization': authorization, 'date': date, 'host': host})}"


async def speech_to_text(audio_data: bytes) -> str:
    """
    将 PCM 音频数据转为文字
    audio_data: PCM音频二进制数据（16bit，16kHz，单声道）
    返回识别文本
    """
    if not audio_data:
        return ""

    ws_url = _create_asr_auth_url()
    result_text = ""

    try:
        async with websockets.connect(ws_url, ping_interval=None) as ws:
            # 分帧发送
            total_len = len(audio_data)
            frame_count = 0

            while frame_count * FRAME_SIZE < total_len:
                start = frame_count * FRAME_SIZE
                end = min(start + FRAME_SIZE, total_len)
                chunk = audio_data[start:end]
                is_last = (end >= total_len)

                frame_data = {
                    "common": {"app_id": settings.XUNFEI_APP_ID},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                        "vad_eos": 2000,
                        "dwa": "wpgs",
                    },
                    "data": {
                        "status": 2 if is_last else 0,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": base64.b64encode(chunk).decode("utf-8")
                    }
                }

                await ws.send(json.dumps(frame_data))
                response = await ws.recv()
                data = json.loads(response)

                if data.get("code") != 0:
                    print(f"ASR错误码: {data.get('code')}, 消息: {data.get('message')}")
                    break

                # 提取识别文字
                result = data.get("data", {}).get("result", {})
                if result:
                    ws_list = result.get("ws", [])
                    for ws_item in ws_list:
                        for cw in ws_item.get("cw", []):
                            result_text += cw.get("w", "")

                frame_count += 1

            # 发送结束帧（如果音频刚好是整数帧）
            if total_len > 0 and total_len % FRAME_SIZE == 0:
                end_frame = {
                    "common": {"app_id": settings.XUNFEI_APP_ID},
                    "business": {
                        "language": "zh_cn",
                        "domain": "iat",
                        "accent": "mandarin",
                    },
                    "data": {
                        "status": 2,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": ""
                    }
                }
                await ws.send(json.dumps(end_frame))

    except Exception as e:
        print(f"语音识别失败: {e}")

    return result_text.strip()
