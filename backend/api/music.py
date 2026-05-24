"""
音乐代理 API - 代理网易云音频直链，绕过前端 Referer 限制
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
import httpx

router = APIRouter(prefix="/api/music", tags=["music"])

# 网易云直链 API（302 重定向到 CDN）
NETEASE_AUDIO_URL = "https://music.163.com/song/media/outer/url?id={song_id}.mp3"

@router.get("/proxy")
async def proxy_audio(song_id: int = Query(..., description="网易云歌曲 ID")):
    """
    代理网易云音频：请求直链并返回 302 重定向，或返回音频流。
    前端 <audio> 请求此接口即可播放，不受 Referer 限制。
    """
    url = NETEASE_AUDIO_URL.format(song_id=song_id)
    headers = {
        "Referer": "https://music.163.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
        try:
            resp = await client.head(url, headers=headers)
        except Exception:
            raise HTTPException(status_code=502, detail="无法连接到网易云")

    if resp.status_code == 302 and "Location" in resp.headers:
        real_url = resp.headers["Location"]
        # 如果网易云返回 404，说明这首歌没版权或 ID 无效
        if "/404" in real_url or real_url.endswith("/404"):
            raise HTTPException(status_code=404, detail="歌曲暂不可用（无版权或ID无效）")
        return RedirectResponse(url=real_url, status_code=302)

    # 兜底：直接流式返回
    async with httpx.AsyncClient(timeout=30.0) as client:
        stream_resp = await client.get(url, headers=headers)
    if stream_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="歌曲暂不可用")
    return Response(
        content=stream_resp.content,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"},
    )
