"""守护者多 Agent 工作台 API。"""

from __future__ import annotations

from datetime import datetime
import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import SessionLocal, get_db
from guardian_engine import (
    apply_followup_safety_override,
    create_case_code,
    ensure_agent_runs,
    process_case,
    rebuild_plan_from_reviewed_templates,
    seed_evidence_sources,
)
from guardian_pdf import generate_guardian_pdf
from guardian_schemas import FollowUpResponse, GuardianCaseCreate, SupportPlanOutput
from models import (
    AgentRun,
    EvidenceSource,
    FollowUpTask,
    GuardianCase,
    SensitiveAccessLog,
    SupportPlan,
    User,
)

router = APIRouter(prefix="/api/guardian", tags=["guardian"])


def _load(value: str, fallback):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _owned_case(db: Session, case_code: str, user: User) -> GuardianCase:
    case = db.query(GuardianCase).filter(GuardianCase.case_code == case_code).first()
    if not case:
        raise HTTPException(status_code=404, detail="工单不存在")
    if case.owner_user_id != user.id and int(user.is_admin or 0) < 2:
        raise HTTPException(status_code=403, detail="无权访问该工单")
    return case


def _audit(db: Session, user: User, action: str, resource_type: str, resource_id: str) -> None:
    db.add(
        SensitiveAccessLog(
            actor_user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result="allowed",
        )
    )
    db.commit()


def _case_payload(db: Session, case: GuardianCase) -> dict:
    runs = db.query(AgentRun).filter(AgentRun.case_id == case.id).order_by(AgentRun.id.asc()).all()
    plan_row = db.query(SupportPlan).filter(SupportPlan.case_id == case.id).first()
    followups = db.query(FollowUpTask).filter(FollowUpTask.case_id == case.id).order_by(FollowUpTask.day_offset).all()
    evidence_codes = set()
    for run in runs:
        evidence_codes.update(_load(run.evidence_json, []))
    evidence = []
    if evidence_codes:
        evidence = db.query(EvidenceSource).filter(EvidenceSource.source_code.in_(sorted(evidence_codes))).all()
    return {
        "case": {
            "case_code": case.case_code,
            "reporter_role": case.reporter_role,
            "age_band": case.age_band,
            "signals": _load(case.signals_json, []),
            "duration": case.duration,
            "functional_impact": case.functional_impact,
            "district": case.district,
            "risk_level": case.risk_level,
            "status": case.status,
            "review_status": case.review_status,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        },
        "agents": [
            {
                "run_code": row.run_code,
                "agent_type": row.agent_type,
                "status": row.status,
                "summary": row.summary,
                "output": _load(row.output_json, {}),
                "evidence_codes": _load(row.evidence_json, []),
                "model_name": row.model_name,
                "prompt_version": row.prompt_version,
                "degraded": bool(row.degraded),
                "error_code": row.error_code,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in runs
        ],
        "plan": _load(plan_row.plan_json, None) if plan_row else None,
        "evidence": [
            {
                "source_code": row.source_code,
                "title": row.title,
                "issuer": row.issuer,
                "source_url": row.source_url,
                "evidence_level": row.evidence_level,
                "summary": row.summary,
                "reviewed_at": row.reviewed_at,
                "review_status": row.review_status,
            }
            for row in evidence
        ],
        "follow_ups": [
            {
                "id": row.id,
                "day_offset": row.day_offset,
                "due_at": row.due_at.isoformat(),
                "status": row.status,
                "response": _load(row.response_json, {}),
            }
            for row in followups
        ],
    }


@router.post("/cases", status_code=202)
async def create_case(
    payload: GuardianCaseCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = GuardianCase(
        case_code=create_case_code(),
        owner_user_id=current_user.id,
        reporter_role=payload.reporter_role,
        age_band=payload.age_band,
        signals_json=json.dumps(payload.signals, ensure_ascii=False),
        duration=payload.duration,
        functional_impact=payload.functional_impact,
        district=payload.district,
        context=payload.context,
        guardian_may_be_source=int(payload.guardian_may_be_source),
        consent_version=payload.consent_version,
        status="queued",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    runs = ensure_agent_runs(db, case)
    _audit(db, current_user, "create_guardian_case", "guardian_case", case.case_code)
    background_tasks.add_task(process_case, case.id)
    return {
        "case_id": case.case_code,
        "run_id": runs[0].run_code,
        "status": case.status,
        "events_url": f"/api/guardian/cases/{case.case_code}/events",
    }


@router.get("/cases/{case_code}")
async def get_case(
    case_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _owned_case(db, case_code, current_user)
    _audit(db, current_user, "view_guardian_case", "guardian_case", case.case_code)
    return _case_payload(db, case)


@router.get("/cases/{case_code}/events")
async def case_events(
    case_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _owned_case(db, case_code, current_user)
    owner_id = case.owner_user_id

    async def stream():
        last_snapshot = ""
        for _ in range(180):
            stream_db = SessionLocal()
            try:
                current = stream_db.query(GuardianCase).filter(
                    GuardianCase.case_code == case_code,
                    GuardianCase.owner_user_id == owner_id,
                ).first()
                if not current:
                    yield "event: error\ndata: {\"detail\":\"工单不存在\"}\n\n"
                    return
                payload = _case_payload(stream_db, current)
                snapshot = json.dumps(payload, ensure_ascii=False, default=str)
                if snapshot != last_snapshot:
                    yield f"event: snapshot\ndata: {snapshot}\n\n"
                    last_snapshot = snapshot
                if current.status in {"completed", "failed"}:
                    yield f"event: complete\ndata: {json.dumps({'status': current.status}, ensure_ascii=False)}\n\n"
                    return
            finally:
                stream_db.close()
            await asyncio.sleep(0.5)
        yield "event: timeout\ndata: {\"detail\":\"事件流超时，可重新连接\"}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/cases/{case_code}/retry", status_code=202)
async def retry_case(
    case_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _owned_case(db, case_code, current_user)
    if case.status == "completed":
        return {"case_id": case.case_code, "status": "completed", "idempotent": True}
    if case.status == "processing":
        return {"case_id": case.case_code, "status": "processing", "idempotent": True}
    db.query(AgentRun).filter(AgentRun.case_id == case.id, AgentRun.status == "failed").update(
        {AgentRun.status: "queued", AgentRun.error_code: None, AgentRun.summary: ""},
        synchronize_session=False,
    )
    case.status = "queued"
    db.commit()
    background_tasks.add_task(process_case, case.id)
    return {"case_id": case.case_code, "status": "queued", "idempotent": False}


@router.get("/cases/{case_code}/report.pdf")
async def get_report(
    case_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _owned_case(db, case_code, current_user)
    plan_row = db.query(SupportPlan).filter(SupportPlan.case_id == case.id).first()
    if not plan_row:
        raise HTTPException(status_code=409, detail="方案仍在生成中")
    plan = SupportPlanOutput.model_validate(_load(plan_row.plan_json, {}))
    evidence = db.query(EvidenceSource).filter(EvidenceSource.source_code.in_(plan.evidence_codes)).all()
    pdf = generate_guardian_pdf(case, plan, evidence)
    _audit(db, current_user, "download_guardian_report", "guardian_case", case.case_code)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="gunong-{case.case_code}.pdf"'},
    )


@router.get("/follow-ups")
async def list_followups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(FollowUpTask, GuardianCase)
        .join(GuardianCase, GuardianCase.id == FollowUpTask.case_id)
        .filter(GuardianCase.owner_user_id == current_user.id)
        .order_by(FollowUpTask.due_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": task.id,
                "case_code": case.case_code,
                "risk_level": case.risk_level,
                "day_offset": task.day_offset,
                "due_at": task.due_at.isoformat(),
                "status": task.status,
                "response": _load(task.response_json, {}),
            }
            for task, case in rows
        ]
    }


def _owned_followup(db: Session, followup_id: int, user: User) -> tuple[FollowUpTask, GuardianCase]:
    row = (
        db.query(FollowUpTask, GuardianCase)
        .join(GuardianCase, GuardianCase.id == FollowUpTask.case_id)
        .filter(FollowUpTask.id == followup_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="回访任务不存在")
    task, case = row
    if case.owner_user_id != user.id and int(user.is_admin or 0) < 2:
        raise HTTPException(status_code=403, detail="无权访问该回访")
    return task, case


@router.post("/follow-ups/{followup_id}/responses")
async def submit_followup(
    followup_id: int,
    payload: FollowUpResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task, case = _owned_followup(db, followup_id, current_user)
    task.response_json = json.dumps(payload.model_dump(), ensure_ascii=False)
    task.status = "completed"
    urgent_followup = (
        payload.current_safety in {"unsure", "immediate_danger"}
        or payload.new_self_harm_or_suicide_signal
        or payload.action_taken_or_means_available
        or payload.family_harm_or_unsafe_home
    )
    if urgent_followup:
        if payload.family_harm_or_unsafe_home:
            case.guardian_may_be_source = 1
        apply_followup_safety_override(db, case, "followup_new_safety_signal")
        db.query(FollowUpTask).filter(
            FollowUpTask.case_id == case.id,
            FollowUpTask.id != task.id,
            FollowUpTask.status.in_(["scheduled", "due"]),
        ).update({FollowUpTask.status: "superseded_for_safety"}, synchronize_session=False)
        db.commit()
        _audit(db, current_user, "followup_urgent_override", "guardian_case", case.case_code)
        return {
            "status": "completed",
            "next_action": "不要等待普通回访：请保持陪伴并立即联系12356；已经采取行动或存在迫切危险时拨打110或120。若家庭并不安全，请联系可信教师、其他安全成年人或110。",
            "risk_level": "urgent",
            "urgent_override": True,
        }
    next_action = "继续当前支持，并按计划完成下一次回访。"
    if payload.mood_change == "worse":
        if case.risk_level in {"routine", "watch"}:
            case.risk_level = "professional"
            rebuild_plan_from_reviewed_templates(db, case)
        next_action = "状态有所加重，建议尽快联系学校心理老师或正规医疗机构重新评估；如出现危险信号请立即拨打12356、110或120。"
    elif payload.mood_change == "unchanged" or payload.action_completion == "none":
        next_action = "先识别执行困难并调整为更小步骤；若功能持续受损，升级至专业支持。"
    db.commit()
    _audit(db, current_user, "submit_followup", "follow_up", str(task.id))
    return {"status": "completed", "next_action": next_action, "risk_level": case.risk_level, "urgent_override": False}


@router.post("/follow-ups/{followup_id}/simulate-due")
async def simulate_followup_due(
    followup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="该接口仅用于本地演示")
    task, _ = _owned_followup(db, followup_id, current_user)
    if task.status != "completed":
        task.due_at = datetime.now()
        task.status = "due"
        db.commit()
    return {"id": task.id, "status": task.status, "due_at": task.due_at.isoformat()}
