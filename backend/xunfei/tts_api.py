"""
讯飞文字转语音（在线语音合成 API）
文档：https://www.xfyun.cn/doc/tts/online_tts.html
使用 WebSocket API，返回音频二进制数据
"""
import json
import base64
import hashlib
import hmac
import time
import websocket
import threading
from config import settings

TTS_URL = "wss://tts-api.xfyun.cn/v2/tts"


def text_to_speech(text: str, voice: str = "x4_yezi", speed: int = 50) -> bytes:
    """
    将文字转为语音，返回 MP3 二进制数据
    voice: xiaoyan（女声）/ xiaofeng（男声）等
    speed: 0-100，50为正常语速
    返回: 音频bytes，失败返回空bytes
    """
    app_id = settings.XUNFEI_APP_ID
    api_key = settings.XUNFEI_API_KEY
    api_secret = settings.XUNFEI_API_SECRET

    # 生成鉴权URL
    auth_url = _build_auth_url(TTS_URL, api_key, api_secret)

    # 构造请求数据
    req_data = {
        "common": {"app_id": app_id},
        "business": {
            "aue": "lame",        # lame=MP3格式
            "sfl": 1,             # 开启流式返回
            "auf": "audio/L16;rate=16000",
            "vcn": voice,         # 发音人（注意是vcn不是voice_name）
            "speed": speed,
            "volume": 50,
            "pitch": 50,
            "bgs": 0,
            "tte": "UTF8"
        },
        "data": {
            "status": 2,          # 2=一次性发送完毕
            "text": base64.b64encode(text.encode("utf-8")).decode("utf-8")
        }
    }

    audio_chunks = []
    result_event = threading.Event()
    error_msg = [None]

    def on_message(ws, message):
        try:
            data = json.loads(message)
            code = data.get("code", -1)
            if code != 0:
                error_msg[0] = data.get("message", "未知错误")
                result_event.set()
                return
            audio_b64 = data.get("data", {}).get("audio", "")
            if audio_b64:
                audio_chunks.append(base64.b64decode(audio_b64))
            # status=2 表示合成完成
            if data.get("data", {}).get("status") == 2:
                result_event.set()
        except Exception as e:
            error_msg[0] = str(e)
            result_event.set()

    def on_error(ws, error):
        error_msg[0] = str(error)
        result_event.set()

    def on_close(ws, close_status_code, close_msg):
        result_event.set()

    def on_open(ws):
        ws.send(json.dumps(req_data))

    ws = websocket.WebSocketApp(
        auth_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # 在后台线程运行 WebSocket
    ws_thread = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10})
    ws_thread.start()

    # 等待结果，最多30秒
    result_event.wait(timeout=30)
    ws.close()
    ws_thread.join(timeout=5)

    if error_msg[0]:
        print(f"TTS错误: {error_msg[0]}")
        return b""

    if audio_chunks:
        return b"".join(audio_chunks)

    return b""


def _build_auth_url(url: str, api_key: str, api_secret: str) -> str:
    """
    构建带鉴权参数的 WebSocket URL
    参考讯飞开放平台鉴权文档
    """
    from datetime import datetime
    from urllib.parse import urlencode

    host = "tts-api.xfyun.cn"
    path = "/v2/tts"

    now = datetime.utcnow()
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 构建签名原文（与讯飞官方示例一致）
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

    # HMAC-SHA256 签名
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")

    # 构建 authorization
    authorization = base64.b64encode(
        f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'.encode("utf-8")
    ).decode("utf-8")

    # 拼接 URL
    return f"wss://{host}{path}?{urlencode({'authorization': authorization, 'date': date, 'host': host})}"
