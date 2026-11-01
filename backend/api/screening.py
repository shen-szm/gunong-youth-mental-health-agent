"""学生标准筛查（PHQ-9）API：本地确定性计分，不调用外部模型。"""

from __future__ import annotations

import json
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

import screening_engine
from app_time import china_now_naive
from auth import get_current_user
from config import settings
from database import get_db
from models import SensitiveAccessLog, StudentChatSession, StudentScreeningRun, User
from student_ai_authorization import student_ai_governance_version


router = APIRouter(prefix="/api/screening", tags=["student-screening"])


class ScreeningSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: dict[str, int]
    disclosure_ack: bool = False

    @field_validator("answers", mode="before")
    @classmethod
    def validate_raw_answers(cls, value):
        if not isinstance(value, dict):
            raise ValueError("筛查答案格式不正确")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in value.values()):
            raise ValueError("筛查选项必须是整数")
        return value

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value):
        expected = {str(item["id"]) for item in screening_engine.ITEMS}
        if set(value) != expected:
            raise ValueError("筛查题目不完整或包含多余题目")
        if any(isinstance(item, bool) or not 0 <= item <= 3 for item in value.values()):
            raise ValueError("筛查选项必须在 0 到 3 之间")
        return {key: int(value[key]) for key in sorted(expected, key=int)}


class ScreeningAcknowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contacted_trusted_adult: bool = False


def _require_enabled() -> None:
    if not settings.STUDENT_SCREENING_ENABLED:
        raise HTTPException(status_code=404, detail="功能未启用")


def _audit(db: Session, user_id: int, action: str, resource_id: str, result: str) -> None:
    db.add(SensitiveAccessLog(
        actor_user_id=user_id,
        action=action,
        resource_type="student_screening",
        resource_id=resource_id,
        result=result,
    ))


def _urgent_session(db: Session, user_id: int) -> tuple[StudentChatSession, bool]:
    active = db.query(StudentChatSession).filter(
        StudentChatSession.user_id == user_id,
        StudentChatSession.status.in_(["active", "urgent"]),
    ).order_by(StudentChatSession.started_at.desc()).first()
    if active:
        active.status = "urgent"
        active.risk_level = "urgent"
        if not active.external_ai_consent_version:
            active.external_ai_consent_version = student_ai_governance_version(db, user_id)
        db.flush()
        return active, False
    row = StudentChatSession(
        session_code=f"SC-{china_now_naive():%Y%m%d}-{secrets.token_hex(4).upper()}",
        user_id=user_id,
        status="urgent",
        risk_level="urgent",
        external_ai_consent_version=student_ai_governance_version(db, user_id),
    )
    db.add(row)
    db.flush()
    return row, True


def _linked_session_code(db: Session, row: StudentScreeningRun) -> str | None:
    if not row.linked_session_id:
        return None
    session = db.query(StudentChatSession).filter(
        StudentChatSession.id == row.linked_session_id,
        StudentChatSession.user_id == row.user_id,
        StudentChatSession.status == "urgent",
    ).first()
    return session.session_code if session else None


def _latest_payload(db: Session, row: StudentScreeningRun) -> dict:
    return screening_engine.to_student_payload(
        row, urgent_session_id=_linked_session_code(db, row))


@router.get("/schema")
def screening_schema(current_user: User = Depends(get_current_user)):
    _require_enabled()
    return {
        "instrument": screening_engine.INSTRUMENT,
        "instrument_version": screening_engine.INSTRUMENT_VERSION,
        "title": "最近两周状态筛查",
        "period": "过去两周",
        "intro": "9 个问题，帮你更清楚地看看最近两周的状态。可以跳过，也可以随时删除结果。",
        "boundary": screening_engine.BOUNDARY,
        "disclosure": screening_engine.DISCLOSURE,
        "scoring_note": "每题按过去两周出现的天数计 0~3 分，总分 0~27；分数只用于支持分流。",
        "retention_days": screening_engine.RETENTION_DAYS,
        "active_days": screening_engine.ACTIVE_DAYS,
        "options": screening_engine.OPTIONS,
        "items": screening_engine.ITEMS,
    }


@router.post("/submit", status_code=201)
def submit_screening(payload: ScreeningSubmitRequest, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    _require_enabled()
    if not payload.disclosure_ack:
        raise HTTPException(status_code=400, detail="请先阅读并确认数据说明")
    screening_engine.cleanup_expired(db, current_user.id)
    total = screening_engine.score(payload.answers)
    band, _label = screening_engine.band_for(total)
    item9_positive = screening_engine.item9_answered(payload.answers)
    risk = screening_engine.risk_for(total, item9_positive)
    now = china_now_naive()
    run_code = f"SCR-{now:%Y%m%d}-{secrets.token_hex(4).upper()}"

    session = None
    if item9_positive:
        session, _created = _urgent_session(db, current_user.id)

    row = StudentScreeningRun(
        run_code=run_code,
        user_id=current_user.id,
        instrument=screening_engine.INSTRUMENT,
        instrument_version=screening_engine.INSTRUMENT_VERSION,
        answers_json=_answers_json(payload.answers),
        total_score=total,
        band=band,
        risk_level=risk,
        item9_positive=int(item9_positive),
        safety_flag_active=int(item9_positive),
        linked_session_id=session.id if session else None,
        created_at=now,
        expires_at=now + timedelta(days=screening_engine.RETENTION_DAYS),
    )
    db.add(row)
    _audit(db, current_user.id, "create_student_screening", run_code, "recorded")
    if session is not None:
        db.add(SensitiveAccessLog(
            actor_user_id=current_user.id,
            action="create_student_screening_safety_handoff",
            resource_type="student_chat_session",
            resource_id=session.session_code,
            result="urgent_session",
        ))
    db.commit()
    db.refresh(row)
    return screening_engine.to_student_payload(
        row, urgent_session_id=session.session_code if session else None)


@router.get("/latest")
def latest_screening(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_enabled()
    screening_engine.cleanup_expired(db, current_user.id)
    row = screening_engine.latest_screening(db, current_user.id)
    db.commit()
    return {"screening": _latest_payload(db, row) if row else None}


@router.post("/acknowledge")
def acknowledge_screening(payload: ScreeningAcknowledgeRequest, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """保留筛查结果，只记录学生已联系可信成年人；专业级风险随后降为持续留意。"""
    _require_enabled()
    if not payload.contacted_trusted_adult:
        raise HTTPException(status_code=400, detail="请先确认已联系可信成年人")
    screening_engine.cleanup_expired(db, current_user.id)
    row = screening_engine.latest_screening(db, current_user.id)
    if not row:
        raise HTTPException(status_code=404, detail="没有可确认的筛查结果")
    if screening_engine.safety_active(row):
        raise HTTPException(status_code=409, detail="请先完成安全交接，再确认筛查影响")
    if row.acknowledged_at is None:
        row.acknowledged_at = china_now_naive()
        _audit(db, current_user.id, "acknowledge_student_screening", row.run_code,
               "student_confirmed_contacted_adult")
    db.commit()
    db.refresh(row)
    return screening_engine.to_student_payload(row, urgent_session_id=_linked_session_code(db, row))


@router.delete("/{run_code}", status_code=204)
def delete_screening(run_code: str, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    _require_enabled()
    row = db.query(StudentScreeningRun).filter(
        StudentScreeningRun.run_code == run_code,
        StudentScreeningRun.user_id == current_user.id,
        StudentScreeningRun.deleted_at.is_(None),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="筛查结果不存在或已删除")
    if screening_engine.safety_active(row) and _linked_session_code(db, row):
        raise HTTPException(status_code=409, detail="请先完成安全交接，再删除本次结果")
    row.deleted_at = china_now_naive()
    row.answers_json = "{}"
    _audit(db, current_user.id, "delete_student_screening", run_code, "deleted")
    db.commit()
    return None


def _answers_json(answers: dict[str, int]) -> str:
    return json.dumps({key: answers[key] for key in sorted(answers, key=int)},
                      ensure_ascii=False, separators=(",", ":"))
