"""
对话API路由 - 倾诉对话核心功能
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import ChatMessage, MoodRecord
from xunfei.spark_api import ask_spark
from xunfei.asr_api import speech_to_text
from xunfei.tts_api import text_to_speech

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: int
    message: str
    input_type: str = "text"


class ChatResponse(BaseModel):
    reply: str
    emotion: str = ""


@router.post("/send", response_model=ChatResponse)
async def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    """发送消息并获取AI回复"""
    # 保存用户消息
    user_msg = ChatMessage(user_id=req.user_id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()

    # 获取历史对话（最近10条）
    history = db.query(ChatMessage).filter(
        ChatMessage.user_id == req.user_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    history.reverse()

    spark_messages = [{"role": m.role, "content": m.content} for m in history]

    # 加入情绪引导的系统提示
    system_prompt = {
        "role": "system",
        "content": "你是一个温暖、善解人意的AI情绪陪伴助手，名字叫「咕哝」。你的目标是帮助用户表达情绪、缓解压力。回答要简洁温暖，不超过150字。"
    }
    spark_messages.insert(0, system_prompt)

    # 调用星火大模型
    reply = await ask_spark(spark_messages)

    # 简单情绪识别（关键词匹配，后期可接入讯飞情绪分析）
    emotion = _detect_emotion(req.message)

    # 保存AI回复
    ai_msg = ChatMessage(user_id=req.user_id, role="assistant", content=reply, emotion=emotion)
    db.add(ai_msg)

    # 记录情绪
    mood_labels = {"开心": (7, 10), "平静": (5, 7), "焦虑": (3, 5), "难过": (2, 4), "愤怒": (1, 3)}
    score_range = mood_labels.get(emotion, (5, 7))
    import random
    mood_score = random.uniform(score_range[0], score_range[1])

    mood_record = MoodRecord(
        user_id=req.user_id,
        mood_score=mood_score,
        mood_label=emotion,
        content=req.message[:200],
        input_type=req.input_type
    )
    db.add(mood_record)
    db.commit()

    return ChatResponse(reply=reply, emotion=emotion)


@router.post("/asr")
async def audio_to_text(request: Request):
    """语音识别接口 - 接收PCM音频，返回文字"""
    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="未收到音频数据")

    text = await speech_to_text(audio)
    if not text:
        raise HTTPException(status_code=500, detail="语音识别失败，请重试")

    return {"text": text}


@router.get("/tts")
@router.post("/tts")
async def get_tts_audio(text: str = ""):
    """语音合成接口 - 接收文字，返回MP3音频"""
    if not text:
        raise HTTPException(status_code=400, detail="未收到文字")

    audio_data = text_to_speech(text)
    if not audio_data:
        raise HTTPException(status_code=500, detail="语音合成失败，请重试")

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=tts.mp3"}
    )


def _detect_emotion(text: str) -> str:
    """简单关键词情绪识别"""
    text = text.lower()
    keywords = {
        "开心": ["开心", "高兴", "快乐", "满足", "幸福", "棒", "好"],
        "难过": ["难过", "伤心", "失落", "沮丧", "哭", "痛苦"],
        "焦虑": ["焦虑", "紧张", "担心", "害怕", "压力", "烦"],
        "愤怒": ["生气", "愤怒", "烦躁", "讨厌", "恶心", "气"],
    }
    for label, words in keywords.items():
        if any(w in text for w in words):
            return label
    return "平静"


@router.get("/history")
async def get_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """获取对话历史"""
    msgs = db.query(ChatMessage).filter(
        ChatMessage.user_id == user_id
    ).order_by(ChatMessage.created_at.asc()).limit(limit).all()
    return [{"role": m.role, "content": m.content, "emotion": m.emotion, "time": m.created_at.isoformat()} for m in msgs]
