"""
音乐代理 API - 提供网易云歌曲播放能力
方案：
1. /api/music/url - 返回歌曲可播放的真实 URL（通过本地 NeteaseCloudMusicApi 服务）
2. /api/music/play - 直接代理播放（流式转发音频数据）
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
import os

router = APIRouter(prefix="/api/music", tags=["music"])

# 本地 NeteaseCloudMusicApi Node 服务地址（部署在服务器上，端口 3000）
# 如果未部署，则回退到直接返回网易云网页链接
LOCAL_API = os.environ.get("NETEASE_API_URL", "http://127.0.0.1:3000")

# 网易云官方 API（weapi，需要加密参数，无 cookie 时可能无法获取）
# 这里用一个公共的免费 API 代理（如果可用）
PUBLIC_NETEASE_API = "https://neteasecloudmusicapi.vercel.app"


@router.get("/url")
async def get_song_url(song_id: int = Query(..., description="网易云歌曲 ID")):
    """
    获取歌曲播放 URL。
    优先尝试本地 NeteaseCloudMusicApi 服务，失败则返回网易云网页链接。
    """
    # 尝试本地 NeteaseCloudMusicApi 服务
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{LOCAL_API}/song/url/v1",
                params={"id": song_id, "level": "standard"},
            )
            data = r.json()
            if data.get("data") and data["data"][0].get("url"):
                return {"url": data["data"][0]["url"], "song_id": song_id}
    except Exception:
        pass

    # 尝试公开 API（Vercel 免费服务，可能限速或不可用）
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{PUBLIC_NETEASE_API}/song/url/v1",
                params={"id": song_id, "level": "standard"},
            )
            data = r.json()
            if data.get("data") and data["data][0].get("url"]:
                return {"url": data["data"][0]["url"], "song_id": song_id}
    except Exception:
        pass

    # 全部失败：返回网易云网页链接，前端引导用户跳转
    return {
        "url": f"https://music.163.com/song?id={song_id}",
        "song_id": song_id,
        "need_external": True,
        "message": "需要跳转到网易云音乐网页播放"
    }


@router.get("/play")
async def play_song(song_id: int = Query(..., description="网易云歌曲 ID"), req: Request = None):
    """
    直接代理播放：流式转发音频数据到前端。
    先获取真实音频 URL，然后流式返回给前端 <audio> 元素。
    """
    # 获取真实音频 URL
    real_url = None

    # 方法1：本地 NeteaseCloudMusicApi
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{LOCAL_API}/song/url/v1",
                params={"id": song_id, "level": "standard"},
            )
            data = r.json()
            if data.get("data") and data["data"][0].get("url"):
                real_url = data["data"][0]["url"]
    except Exception:
        pass

    # 方法2：公开 API
    if not real_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{PUBLIC_NETEASE_API}/song/url/v1",
                    params={"id": song_id, "level": "standard"},
                )
                data = r.json()
                if data.get("data") and data["data"][0].get("url"):
                    real_url = data["data"][0]["url"]
        except Exception:
            pass

    if not real_url:
        return JSONResponse(
            status_code=404,
            content={"detail": "无法获取播放链接，请前往网易云音乐网页播放", "web_url": f"https://music.163.com/song?id={song_id}"}
        )

    # 流式代理音频
    async def _stream():
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://music.163.com/",
        }
        range_header = req.headers.get("range") if req else None
        if range_header:
            headers["Range"] = range_header

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            async with client.stream("GET", real_url, headers=headers) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    if chunk:
                        yield chunk

    mime = "audio/mpeg"
    if real_url.endswith(".flac"):
        mime = "audio/flac"

    return StreamingResponse(
        _stream(),
        media_type=mime,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        },
    )
