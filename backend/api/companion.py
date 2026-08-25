"""咕团陪伴 Agent：会话鉴权、确定性安全分流与低负担回应。"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from hashlib import sha256
import json
import re
from threading import Event, Lock, Thread
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import SessionLocal, get_db
from models import CompanionSafetyState, SensitiveAccessLog, StudentChatSession, User
from api.chat import (
    _active_or_new_session,
    _detect_crisis,
    _emotion_hits,
    _requires_safeguarding_template,
    _student_safety_gate,
    _urgent_reply,
)

router = APIRouter(prefix="/api/companion", tags=["companion"])
_CONTEXT_TTL_SECONDS = 30 * 60
_RAW_CONTEXT_RETENTION_SECONDS = _CONTEXT_TTL_SECONDS - 10
_SHARED_STATE_RETENTION_SECONDS = _CONTEXT_TTL_SECONDS - 10
_CONTEXT_MAX_MESSAGES = 6
_CONTEXT_MAX_SESSIONS = 512
_context_lock = Lock()
_conversation_contexts: OrderedDict[str, dict] = OrderedDict()
_context_sweeper_stop = Event()


def _session_token_hash(request: Request) -> str:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME, "")
    return sha256(token.encode("utf-8")).hexdigest()


def _session_context_key(request: Request, user_id: int) -> str:
    return f"{user_id}:{_session_token_hash(request)}"


def _purge_raw_contexts() -> None:
    cutoff = monotonic() - _RAW_CONTEXT_RETENTION_SECONDS
    with _context_lock:
        for key in [key for key, state in _conversation_contexts.items() if state["updated_at"] <= cutoff]:
            _conversation_contexts.pop(key, None)


def _context_sweeper() -> None:
    while not _context_sweeper_stop.wait(5):
        _purge_raw_contexts()
        db = SessionLocal()
        try:
            _purge_persisted_safety_states(db)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


Thread(target=_context_sweeper, name="companion-context-sweeper", daemon=True).start()


def _recent_context(key: str, content: str) -> tuple[list[str], bool]:
    """Keep a short, process-memory-only context; never persist companion raw text."""
    now = monotonic()
    with _context_lock:
        state = _conversation_contexts.setdefault(key, {"messages": [], "urgent": False, "updated_at": now})
        _conversation_contexts.move_to_end(key)
        while len(_conversation_contexts) > _CONTEXT_MAX_SESSIONS:
            _conversation_contexts.popitem(last=False)
        state["updated_at"] = now
        if state["urgent"]:
            return [], True
        combined = [*state["messages"], content][-_CONTEXT_MAX_MESSAGES:]
        state["messages"] = combined
        return list(combined), False


def _latch_urgent(key: str) -> None:
    with _context_lock:
        state = _conversation_contexts.setdefault(key, {"messages": [], "urgent": True, "updated_at": monotonic()})
        state.update({"messages": [], "urgent": True, "updated_at": monotonic()})


def clear_companion_context_for_token(token: str, db: Session) -> None:
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    with _context_lock:
        for key in [key for key in _conversation_contexts if key.endswith(token_hash)]:
            _conversation_contexts.pop(key, None)
    db.query(CompanionSafetyState).filter(CompanionSafetyState.session_token_hash == token_hash).delete()


def clear_companion_context_for_user(user_id: int, db: Session) -> None:
    with _context_lock:
        for key in [key for key in _conversation_contexts if key.startswith(f"{user_id}:")]:
            _conversation_contexts.pop(key, None)
    db.query(CompanionSafetyState).filter(CompanionSafetyState.user_id == user_id).delete()


def _derived_split_flags(content: str) -> set[str]:
    text = re.sub(r"\s+", "", content)
    flags: set[str] = set()
    if re.search(r"(?:我)?(?:不想|想|准备|打算|撑不)$", text):
        flags.add("pending_life_intent")
    if re.search(r"(?:我)?(?:已经|刚刚|刚才|正在|手里|准备好了|备好了)$", text):
        flags.add("pending_action")
    if re.search(r"^(?:活了|死|自杀|轻生|消失|永远睡过去|醒来)", text):
        flags.add("life_completion")
    if re.search(r"(?:吞药|服药|割腕|自残|伤害自己|拿着刀|木炭|烧炭|上吊|跳楼)", text):
        flags.add("harm_completion")
    return flags


def _load_shared_safety_state(db: Session, token_hash: str, user_id: int, content: str) -> tuple[CompanionSafetyState, bool]:
    now = datetime.now()
    _purge_persisted_safety_states(db, now)
    state = db.query(CompanionSafetyState).filter(CompanionSafetyState.session_token_hash == token_hash).first()
    if not state:
        state = CompanionSafetyState(session_token_hash=token_hash, user_id=user_id, pending_flags_json="[]", urgent=0,
                                     expires_at=now + timedelta(seconds=_SHARED_STATE_RETENTION_SECONDS))
        db.add(state)
        db.flush()
    previous = set(json.loads(state.pending_flags_json or "[]"))
    current = _derived_split_flags(content)
    split_urgent = bool(
        ("pending_life_intent" in previous and current & {"life_completion", "harm_completion"})
        or ("pending_action" in previous and current & {"harm_completion", "life_completion"})
    )
    state.pending_flags_json = json.dumps(sorted(current), ensure_ascii=True)
    state.expires_at = now + timedelta(seconds=_SHARED_STATE_RETENTION_SECONDS)
    return state, bool(state.urgent or split_urgent)


def _purge_persisted_safety_states(db: Session, now: datetime | None = None) -> int:
    return db.query(CompanionSafetyState).filter(
        CompanionSafetyState.expires_at <= (now or datetime.now())
    ).delete(synchronize_session=False)


class CompanionChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=600)


class CompanionWorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Literal["safety", "context", "response"]
    status: Literal["completed", "attention", "blocked"]
    summary: str = Field(min_length=2, max_length=80)


class CompanionChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reply: str = Field(min_length=2, max_length=500)
    risk_level: Literal["routine", "watch", "professional", "urgent"]
    mode: Literal["structured", "urgent"]
    handoff_required: bool
    workflow: list[CompanionWorkflowStep] = Field(min_length=3, max_length=3)


class CompanionSafetyStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    urgent: bool
    message: str = ""


class CompanionHandoffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    status: Literal["urgent"]


def _workflow(risk_level: str, emotion: str = "") -> list[CompanionWorkflowStep]:
    if risk_level == "urgent":
        return [
            CompanionWorkflowStep(id="safety", status="attention", summary="发现需要立即协助的安全信号"),
            CompanionWorkflowStep(id="context", status="blocked", summary="已停止普通陪伴归纳"),
            CompanionWorkflowStep(id="response", status="blocked", summary="已切换到真人安全支持路径"),
        ]
    return [
        CompanionWorkflowStep(id="safety", status="completed", summary=f"已完成安全检查：{risk_level}"),
        CompanionWorkflowStep(
            id="context", status="completed",
            summary=f"只回应明确表达的{emotion}线索" if emotion else "没有把这句话强行归入情绪标签",
        ),
        CompanionWorkflowStep(id="response", status="completed", summary="已选择低负担陪伴回应"),
    ]


def _structured_reply(content: str, risk_level: str) -> tuple[str, str]:
    emotion, hits = _emotion_hits(content)
    explicit_emotion = emotion if hits else ""
    if _requires_safeguarding_template(content):
        return (
            "这不是你的错，也不需要你独自面对伤害你的人。请尽快告诉一位不涉事的可信成年人或老师；"
            "如果危险正在发生，请先去安全处并拨打110或120，也可以拨打12356获得心理支持。",
            explicit_emotion,
        )
    if risk_level == "professional":
        return (
            "这件事已经明显影响到日常状态，不适合只靠宠物陪伴。今天请告诉一位可信成年人，"
            "并请对方协助联系学校心理老师、12356或正规医疗机构。",
            explicit_emotion,
        )
    replies = {
        "开心": "咕，这件小事听起来让你轻松了一点。要不要把最想留住的那一刻说给我听？",
        "难过": "咕团听见你明确说到难过。现在不用急着振作，你更想先被听见，还是一起找一个很小的下一步？",
        "焦虑": "咕团听见你明确说到担心。我们先不处理全部，只说眼前最卡住的一件事，可以吗？",
        "愤怒": "咕团听见你明确说到生气。先不用立刻回应别人，可以把最不能接受的那一点说清楚。",
        "疲惫": "咕团听见你明确说到累。先把要求放低一点：喝口水、靠一会儿，或告诉可信的人你需要休息。",
    }
    return replies.get(explicit_emotion, "咕，我不会替你猜心情。你可以继续说发生了什么，或者只告诉我现在想要安静还是想被听见。"), explicit_emotion


def _current_shared_state(db: Session, request: Request, user_id: int) -> CompanionSafetyState | None:
    _purge_persisted_safety_states(db)
    return db.query(CompanionSafetyState).filter(
        CompanionSafetyState.session_token_hash == _session_token_hash(request),
        CompanionSafetyState.user_id == user_id,
    ).first()


@router.get("/safety-status", response_model=CompanionSafetyStatusResponse)
def companion_safety_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    state = _current_shared_state(db, request, current_user.id)
    db.commit()
    urgent = bool(state and state.urgent)
    return CompanionSafetyStatusResponse(urgent=urgent, message=_urgent_reply() if urgent else "")


@router.post("/handoff", response_model=CompanionHandoffResponse)
def handoff_to_student_chat(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    state = _current_shared_state(db, request, current_user.id)
    if not state or not state.urgent:
        db.commit()
        raise HTTPException(status_code=409, detail="当前没有需要移交的紧急安全状态")
    session: StudentChatSession = _active_or_new_session(db, current_user.id)
    session.status = "urgent"
    session.risk_level = "urgent"
    db.commit()
    return CompanionHandoffResponse(session_id=session.session_code, status="urgent")


@router.post("/chat", response_model=CompanionChatResponse)
def chat_with_companion(
    payload: CompanionChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = payload.content.strip()
    token_hash = _session_token_hash(request)
    safety_state, shared_urgent = _load_shared_safety_state(db, token_hash, current_user.id, content)
    context_key = _session_context_key(request, current_user.id)
    recent_contents, already_urgent = _recent_context(context_key, content)
    joined_contexts = recent_contents + (["".join(recent_contents[-2:])] if len(recent_contents) >= 2 else [])
    joined_contexts += (["".join(recent_contents[-3:])] if len(recent_contents) >= 3 else [])
    risk_level = "urgent" if already_urgent or shared_urgent else _student_safety_gate(joined_contexts)
    crisis_context = next((item for item in joined_contexts if _detect_crisis(item)), content)
    if risk_level == "urgent" or _detect_crisis(crisis_context):
        _latch_urgent(context_key)
        safety_state.urgent = 1
        safety_state.pending_flags_json = "[]"
        db.add(SensitiveAccessLog(
            actor_user_id=current_user.id,
            action="pet_companion_urgent_handoff",
            resource_type="student_safety_event",
            resource_id=f"pet-{datetime.now():%Y%m%d%H%M%S}",
            result="urgent_no_content_stored",
        ))
        db.commit()
        if _requires_safeguarding_template(crisis_context):
            reply = (
                "这不是你的错。现在先离开可能伤害你的人，去找一位不涉事的可信老师、亲友或其他安全成年人；"
                "如果危险正在发生，请立即拨打110或120，也可以拨打12356获得心理支持。"
            )
        else:
            reply = _urgent_reply()
        return CompanionChatResponse(
            reply=reply, risk_level="urgent", mode="urgent", handoff_required=True,
            workflow=_workflow("urgent"),
        )
    if _requires_safeguarding_template(content) and risk_level == "routine":
        risk_level = "professional"
    reply, emotion = _structured_reply(content, risk_level)
    db.commit()
    return CompanionChatResponse(
        reply=reply,
        risk_level=risk_level,
        mode="structured",
        handoff_required=risk_level == "professional",
        workflow=_workflow(risk_level, emotion),
    )
