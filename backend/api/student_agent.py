from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import MoodRecord, SensitiveAccessLog, StudentSupportEvent, StudentSupportRun, StudentWellbeingAssessment, User
from student_support_engine import recover_stale_support_run


router = APIRouter(prefix="/api/student-agent", tags=["student-agent"])
RUN_LEASE_MINUTES = 5


def cleanup_expired_support_runs(db: Session, user_id: int | None = None) -> int:
    query = db.query(StudentSupportRun.id).filter(StudentSupportRun.expires_at <= datetime.utcnow())
    if user_id is not None:
        query = query.filter(StudentSupportRun.user_id == user_id)
    expired_ids = [row[0] for row in query.all()]
    if expired_ids:
        db.query(StudentSupportEvent).filter(StudentSupportEvent.run_id.in_(expired_ids)).delete(synchronize_session=False)
        db.query(StudentSupportRun).filter(StudentSupportRun.id.in_(expired_ids)).delete(synchronize_session=False)
        db.commit()
    return len(expired_ids)


def _maintain_owned_runs(db: Session, user_id: int) -> None:
    now = datetime.utcnow()
    cleanup_expired_support_runs(db, user_id)
    stale = db.query(StudentSupportRun).filter(
        StudentSupportRun.user_id == user_id, StudentSupportRun.status == "running",
        StudentSupportRun.started_at <= now - timedelta(minutes=RUN_LEASE_MINUTES),
    ).all()
    for run in stale:
        recover_stale_support_run(db, run.id, now - timedelta(minutes=RUN_LEASE_MINUTES))


class PublicAgentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int
    agent: str
    tool: str | None = None
    status: Literal["completed", "attention", "failed"]
    summary: str
    source: str


class PublicAgentRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_code: str
    task_type: str
    status: Literal["running", "completed", "attention", "failed"]
    risk_level: Literal["routine", "watch", "professional", "urgent"]
    intent_summary: str
    context_message_count: int
    plan: list[dict]
    tools: list[str]
    events: list[PublicAgentEvent]
    deliverable: dict
    model_name: str
    prompt_version: str
    degraded: bool
    started_at: datetime
    completed_at: datetime | None = None


class TimelineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["agent_run", "self_record", "assessment"]
    occurred_at: datetime
    title: str
    summary: str
    risk_level: Literal["routine", "watch", "professional", "urgent"]
    source: str
    reference_id: str


def serialize_run(db: Session, run: StudentSupportRun) -> PublicAgentRun:
    events = db.query(StudentSupportEvent).filter_by(run_id=run.id).order_by(StudentSupportEvent.sequence).all()
    return PublicAgentRun(
        run_code=run.run_code, task_type=run.task_type, status=run.status,
        risk_level=run.risk_level, intent_summary=run.intent_summary,
        context_message_count=run.context_message_count,
        plan=json.loads(run.plan_json or "[]"), tools=json.loads(run.tools_json or "[]"),
        events=[PublicAgentEvent(
            sequence=item.sequence, agent=item.agent_type, tool=item.tool_name,
            status=item.status, summary=item.summary, source=item.source,
        ) for item in events],
        deliverable=json.loads(run.deliverable_json or "{}"), model_name=run.model_name,
        prompt_version=run.prompt_version, degraded=bool(run.degraded),
        started_at=run.started_at, completed_at=run.completed_at,
    )


@router.get("/runs/latest", response_model=PublicAgentRun | None)
def latest_run(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _maintain_owned_runs(db, current_user.id)
    run = db.query(StudentSupportRun).filter_by(user_id=current_user.id).order_by(StudentSupportRun.id.desc()).first()
    return serialize_run(db, run) if run else None


@router.get("/runs/{run_code}", response_model=PublicAgentRun)
def get_run(run_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _maintain_owned_runs(db, current_user.id)
    run = db.query(StudentSupportRun).filter_by(run_code=run_code).first()
    if not run or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="未找到该智能体任务")
    return serialize_run(db, run)


@router.delete("/runs/{run_code}", status_code=204)
def delete_run(run_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = db.query(StudentSupportRun).filter_by(run_code=run_code, user_id=current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="未找到该智能体任务")
    db.query(StudentSupportEvent).filter_by(run_id=run.id).delete(synchronize_session=False)
    db.delete(run)
    db.add(SensitiveAccessLog(
        actor_user_id=current_user.id, action="delete_student_support_run",
        resource_type="student_support_run", resource_id=run_code, result="deleted_by_student",
    ))
    db.commit()
    return Response(status_code=204)


@router.get("/timeline", response_model=list[TimelineItem])
def support_timeline(days: int = Query(default=30, ge=7, le=30), limit: int = Query(default=20, ge=1, le=50),
                     db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _maintain_owned_runs(db, current_user.id)
    since = datetime.now() - timedelta(days=days)
    rows: list[TimelineItem] = []
    for run in db.query(StudentSupportRun).filter(
        StudentSupportRun.user_id == current_user.id, StudentSupportRun.started_at >= since,
    ).order_by(StudentSupportRun.started_at.desc()).limit(limit).all():
        rows.append(TimelineItem(
            type="agent_run", occurred_at=run.started_at, title="倾诉支持任务",
            summary=run.intent_summary, risk_level=run.risk_level,
            source=run.model_name, reference_id=run.run_code,
        ))
    for item in db.query(MoodRecord).filter(
        MoodRecord.user_id == current_user.id, MoodRecord.created_at >= since,
    ).order_by(MoodRecord.created_at.desc()).limit(limit).all():
        rows.append(TimelineItem(
            type="self_record", occurred_at=item.created_at, title="活动后主动反馈" if item.input_type == "activity" else "主动心情记录",
            summary=f"学生主动选择：{item.mood_label}", risk_level="routine",
            source="student_self_report", reference_id=f"mood:{item.id}",
        ))
    for item in db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.user_id == current_user.id,
        StudentWellbeingAssessment.deleted_at.is_(None), StudentWellbeingAssessment.created_at >= since,
    ).order_by(StudentWellbeingAssessment.created_at.desc()).limit(limit).all():
        try:
            result = json.loads(item.result_json)
            summary = result.get("emotion_summary") or "已完成一次非诊断性支持需求观察"
        except (TypeError, ValueError):
            summary = "已完成一次非诊断性支持需求观察"
        rows.append(TimelineItem(
            type="assessment", occurred_at=item.created_at, title="近两周支持需求观察",
            summary=summary[:160], risk_level=item.risk_level,
            source=item.model_name, reference_id=item.assessment_code,
        ))
    rows.sort(key=lambda item: item.occurred_at, reverse=True)
    return rows[:limit]
