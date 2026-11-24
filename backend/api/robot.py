"""Account-bound OpenDeskBot voice gateway.

Only the student's authorized desktop client receives a link token. The
gateway reuses the existing student chat path so safety handling, consent,
session ownership, and stored records have one implementation.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.chat import ChatRequest, send_message
from auth import get_current_user
from database import get_db
from models import RobotLink, User

router = APIRouter(prefix="/api/robot", tags=["robot"])
MODEL_ID = "guunoo-companion"
VOICE_MARKER = "guunoo-robot-voice-v1"
TOKEN_LIFETIME = timedelta(days=90)


def _link_info(link: RobotLink | None) -> dict[str, Any]:
    if link is None or link.expires_at <= datetime.utcnow():
        return {"linked": False}
    return {
        "linked": True,
        "token_hint": link.token_hint,
        "created_at": link.created_at.isoformat(),
        "expires_at": link.expires_at.isoformat(),
        "last_used_at": link.last_used_at.isoformat() if link.last_used_at else None,
    }


def _student_link(db: Session, user: User) -> RobotLink | None:
    return db.query(RobotLink).filter(RobotLink.user_id == user.id).first()


def _require_registered_student(user: User) -> None:
    if int(user.is_admin or 0) != 0 or user.username.startswith(("guest_", "demo_")):
        raise HTTPException(status_code=403, detail="请使用正式学生账号连接机器人")


@router.get("/link")
def get_link(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_registered_student(user)
    return _link_info(_student_link(db, user))


@router.post("/link")
def create_link(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Rotate any prior credential. Raw token is returned only this once."""
    _require_registered_student(user)
    prior = _student_link(db, user)
    if prior:
        db.delete(prior)
        db.flush()
    token = "gnrb_" + secrets.token_urlsafe(32)
    now = datetime.utcnow()
    link = RobotLink(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        token_hint=token[-6:],
        created_at=now,
        expires_at=now + TOKEN_LIFETIME,
    )
    db.add(link)
    db.commit()
    return {**_link_info(link), "token": token, "base_url": "/api/robot/v1", "model": MODEL_ID}


@router.delete("/link")
def revoke_link(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_registered_student(user)
    link = _student_link(db, user)
    if link:
        db.delete(link)
        db.commit()
    return {"linked": False}


def _robot_user(authorization: str | None, db: Session) -> tuple[User, RobotLink]:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.startswith("gnrb_") or len(token) > 128:
        raise HTTPException(status_code=401, detail="机器人连接密钥无效")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    link = db.query(RobotLink).filter(RobotLink.token_hash == token_hash).first()
    if not link or link.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="机器人连接已过期或撤销")
    user = db.query(User).filter(User.id == link.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="关联账号不存在")
    _require_registered_student(user)
    return user, link


class VoiceMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str
    content: Any = None


class VoiceCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    model: str
    messages: list[VoiceMessage] = Field(min_length=1, max_length=60)
    stream: bool = False
    tool_choice: Any = None


def _user_text(messages: list[VoiceMessage]) -> str:
    if not any(
        msg.role in {"system", "developer"} and isinstance(msg.content, str) and VOICE_MARKER in msg.content
        for msg in messages
    ):
        raise HTTPException(status_code=422, detail="请使用咕哝机器人语音模式")
    latest = messages[-1]
    if latest.role != "user":
        raise HTTPException(status_code=422, detail="仅接受用户主动发起的语音对话")
    content = latest.content
    if isinstance(content, list):
        if any(not isinstance(part, dict) or part.get("type") != "text" for part in content):
            raise HTTPException(status_code=422, detail="机器人陪伴模式仅接受转写文本")
        content = "".join(str(part.get("text") or "") for part in content)
    if not isinstance(content, str) or not content.strip() or len(content) > 2000:
        raise HTTPException(status_code=422, detail="语音转写文本长度无效")
    text = content.strip()
    if text.startswith(("[系统", "【系统", "[工具", "【工具")):
        raise HTTPException(status_code=422, detail="系统发起内容不进入学生倾诉记录")
    return text


@router.post("/v1/chat/completions")
async def voice_completion(
    payload: VoiceCompletionRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if payload.model != MODEL_ID:
        raise HTTPException(status_code=422, detail="模型名称应为 guunoo-companion")
    if payload.tool_choice == "required":
        raise HTTPException(status_code=422, detail="陪伴模式不执行机器人工具")
    user, link = _robot_user(authorization, db)
    text = _user_text(payload.messages)
    # This request never sends bot prompts or old client history to the site.
    # The site's student chat endpoint owns its account-scoped conversation.
    result = await send_message(ChatRequest(message=text, input_type="voice"), db, user)
    link.last_used_at = datetime.utcnow()
    db.commit()
    completion_id = "chatcmpl-" + secrets.token_hex(12)
    created = int(time.time())
    if not payload.stream:
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": MODEL_ID,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result.reply}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "guunoo": {"risk_level": result.risk_level, "session_id": result.session_id},
        }

    def events():
        for delta, finish in (({"role": "assistant"}, None), ({"content": result.reply}, None), ({}, "stop")):
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": MODEL_ID,
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }
            yield "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
