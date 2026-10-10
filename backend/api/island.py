"""
心岛守护者 API

提供多智能体系统的HTTP接口：
- Agent运行触发
- 游戏行为日志
- 环境指令下发与确认
- 情绪报告生成与下载
- 咕团互动与状态
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import get_db
from models import (
    User, IslandCommand, GameBehaviorLog, IslandAgentRun,
    PetState, IslandReport,
    SensitiveAccessLog,
)
from student_ai_authorization import student_external_ai_allowed

router = APIRouter(prefix="/api/island", tags=["island"])


# ── 请求/响应模型 ─────────────────────────────────────────

class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trigger: Literal["login", "activity_end", "manual", "scheduled"] = "login"


class BehaviorLogRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal[
        "place_enter", "activity_start", "activity_finish",
        "activity_interact", "reflection", "pet_interaction", "login", "logout",
    ]
    place: str | None = None
    activity: str | None = None
    payload: dict = Field(default_factory=dict)


class CommandAckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_ids: list[int]


class PetInteractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["feed", "groom", "talk", "play"]
    message: str = Field(default="", max_length=600)


class ReportGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: int = Field(default=7, ge=1, le=30)


# ── Agent 运行 ────────────────────────────────────────────

@router.post("/agent/run")
async def run_agent(
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发一次心岛守护者多Agent流程。"""
    from agents import IslandOrchestrator
    external_ai_allowed = student_external_ai_allowed(db, current_user.id)
    orchestrator = IslandOrchestrator(db, external_ai_allowed=external_ai_allowed)
    result = await orchestrator.run(
        user_id=current_user.id,
        nickname=current_user.nickname or current_user.username,
        trigger=payload.trigger,
    )
    audit_result = "local_no_transfer"
    if result.get("crisis"):
        audit_result = "safety_override"
    elif external_ai_allowed and result.get("external_transfer_attempted"):
        audit_result = "xunfei_consent_used"
    elif external_ai_allowed:
        audit_result = "consented_no_transfer"
    db.add(SensitiveAccessLog(
        actor_user_id=current_user.id,
        action="island_external_ai_execution",
        resource_type="island_agent_run",
        resource_id=str(result.get("run_code") or "safety")[:64],
        result=audit_result,
        created_at=datetime.now(),
    ))
    db.commit()
    return result


@router.get("/agent/history")
def get_agent_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的Agent运行历史。"""
    runs = (
        db.query(IslandAgentRun)
        .filter(IslandAgentRun.user_id == current_user.id)
        .order_by(IslandAgentRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "run_code": r.run_code,
                "trigger": r.trigger,
                "safety_status": r.safety_status,
                "commands_issued": r.commands_issued,
                "model_used": r.model_used,
                "degraded": bool(r.degraded),
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in runs
        ]
    }


# ── 游戏行为日志 ──────────────────────────────────────────

@router.post("/behavior/log")
def log_behavior(
    payload: BehaviorLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录一条游戏行为（感知Agent的数据源）。"""
    log = GameBehaviorLog(
        user_id=current_user.id,
        event_type=payload.event_type,
        place=payload.place,
        activity=payload.activity,
        payload_json=json.dumps(payload.payload, ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    return {"ok": True, "log_id": log.id}


@router.get("/behavior/recent")
def get_recent_behaviors(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取近期游戏行为。"""
    cutoff = datetime.now() - timedelta(days=days)
    logs = (
        db.query(GameBehaviorLog)
        .filter(GameBehaviorLog.user_id == current_user.id,
                GameBehaviorLog.created_at >= cutoff)
        .order_by(GameBehaviorLog.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "behaviors": [
            {
                "event_type": l.event_type,
                "place": l.place,
                "activity": l.activity,
                "payload": json.loads(l.payload_json or "{}"),
                "time": l.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for l in logs
        ]
    }


# ── 环境指令 ──────────────────────────────────────────────

@router.get("/commands")
def get_pending_commands(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取待执行的心岛指令（前端轮询）。"""
    commands = (
        db.query(IslandCommand)
        .filter(IslandCommand.user_id == current_user.id,
                IslandCommand.status == "pending")
        .order_by(IslandCommand.created_at.asc())
        .limit(20)
        .all()
    )
    result = []
    for cmd in commands:
        try:
            payload = json.loads(cmd.payload_json or "{}")
        except (json.JSONDecodeError, TypeError):
            payload = {}
        result.append({
            "id": cmd.id,
            "type": cmd.command_type,
            "payload": payload,
            "reason": cmd.reason,
        })
        # 读取不等于执行成功；只有前端确认后才改变状态。
    return {"commands": result}


@router.post("/commands/ack")
def ack_commands(
    payload: CommandAckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认指令已执行。"""
    if not payload.command_ids:
        return {"ok": True, "updated": 0}
    updated = (
        db.query(IslandCommand)
        .filter(IslandCommand.id.in_(payload.command_ids),
                IslandCommand.user_id == current_user.id)
        .update({"status": "acknowledged", "delivered_at": datetime.now()}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "updated": updated}


# ── 咕团互动 ──────────────────────────────────────────────

@router.get("/pet/state")
def get_pet_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取咕团状态。"""
    pet = db.query(PetState).filter(PetState.user_id == current_user.id).first()
    if not pet:
        pet = PetState(user_id=current_user.id)
        db.add(pet)
        db.commit()
        db.refresh(pet)
    return {
        "intimacy": pet.intimacy,
        "mood": pet.mood,
        "today_fed": pet.today_fed,
        "today_groomed": pet.today_groomed,
        "consecutive_days": pet.consecutive_days,
        "last_interaction": pet.last_interaction.strftime("%Y-%m-%d %H:%M") if pet.last_interaction else None,
    }


@router.post("/pet/interact")
async def pet_interact(
    payload: PetInteractRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """与咕团互动（喂食/梳毛/对话/玩耍）。"""
    pet = db.query(PetState).filter(PetState.user_id == current_user.id).first()
    if not pet:
        pet = PetState(user_id=current_user.id)
        db.add(pet)

    # 更新状态
    pet.intimacy = min(1000, (pet.intimacy or 0) + 3)
    pet.last_interaction = datetime.now()
    risk_level = "routine"
    mode = "structured"
    handoff_required = False
    if payload.action == "feed":
        pet.today_fed = min(5, pet.today_fed + 1)
        pet.mood = "happy"
        reply = "咕！好吃！咕团很开心～"
    elif payload.action == "groom":
        pet.today_groomed = min(3, pet.today_groomed + 1)
        pet.mood = "content"
        reply = "咕～好舒服，咕团的毛都顺了。"
    elif payload.action == "play":
        pet.mood = "curious"
        reply = "咕！来玩来玩！"
    else:  # talk
        # 复用宠物陪伴端已验证的会话级安全门，不将原文直接拼接发送给模型。
        from api.companion import CompanionChatRequest, chat_with_companion
        if payload.message.strip():
            companion = chat_with_companion(
                CompanionChatRequest(content=payload.message.strip()),
                request=request,
                db=db,
                current_user=current_user,
            )
            reply = companion.reply
            risk_level = companion.risk_level
            mode = companion.mode
            handoff_required = companion.handoff_required
            if companion.risk_level in {"professional", "urgent"}:
                pet.mood = "concerned"
        else:
            reply = "咕，我在听。"

    db.commit()
    return {
        "ok": True,
        "action": payload.action,
        "reply": reply,
        "risk_level": risk_level,
        "mode": mode,
        "handoff_required": handoff_required,
        "pet_state": {
            "intimacy": pet.intimacy,
            "mood": pet.mood,
        },
    }


# ── 情绪报告 ──────────────────────────────────────────────

@router.post("/report/generate")
async def generate_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成情绪报告（可验收成果）。"""
    from agents import IslandOrchestrator
    external_ai_allowed = student_external_ai_allowed(db, current_user.id)
    orchestrator = IslandOrchestrator(db, external_ai_allowed=external_ai_allowed)
    try:
        result = await orchestrator.generate_report(
            user_id=current_user.id,
            nickname=current_user.nickname or current_user.username,
            days=payload.days,
        )
        if result.get("status") == "blocked":
            audit_result = "safety_blocked_no_transfer"
        elif result.get("external_transfer_attempted") and result.get("llm_used"):
            audit_result = "transfer_attempted_output_accepted"
        elif result.get("external_transfer_attempted"):
            audit_result = "transfer_attempted_output_rejected_or_failed"
        else:
            audit_result = "local_no_transfer"
        db.add(SensitiveAccessLog(
            actor_user_id=current_user.id,
            action="generate_island_emotion_report",
            resource_type="island_report",
            resource_id=str(result.get("audit_run_code") or result.get("report_code"))[:64],
            result=audit_result,
        ))
        db.commit()
        return result
    except Exception:
        db.rollback()
        db.add(SensitiveAccessLog(
            actor_user_id=current_user.id,
            action="generate_island_emotion_report",
            resource_type="island_report",
            resource_id=orchestrator.current_run_code[:64],
            result="execution_failed_after_transfer" if orchestrator.external_transfer_attempted else "local_execution_failed",
        ))
        db.commit()
        raise


@router.get("/report/list")
def list_reports(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的报告列表。"""
    reports = (
        db.query(IslandReport)
        .filter(IslandReport.user_id == current_user.id)
        .order_by(IslandReport.generated_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "reports": [
            {
                "report_code": r.report_code,
                "period_days": r.period_days,
                "has_pdf": bool(r.pdf_path),
                "model_name": r.model_name,
                "degraded": bool(r.degraded),
                "generated_at": r.generated_at.strftime("%Y-%m-%d %H:%M"),
            }
            for r in reports
        ]
    }


@router.get("/report/{report_code}")
def get_report(
    report_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取报告详情。"""
    report = (
        db.query(IslandReport)
        .filter(IslandReport.report_code == report_code,
                IslandReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    try:
        data = json.loads(report.report_json or "{}")
    except (json.JSONDecodeError, TypeError):
        data = {}
    return {
        "report_code": report.report_code,
        "period_days": report.period_days,
        "data": data,
        "has_pdf": bool(report.pdf_path),
        "model_name": report.model_name,
        "generated_at": report.generated_at.strftime("%Y-%m-%d %H:%M"),
    }


@router.get("/report/{report_code}/download")
def download_report_pdf(
    report_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载报告PDF。"""
    report = (
        db.query(IslandReport)
        .filter(IslandReport.report_code == report_code,
                IslandReport.user_id == current_user.id)
        .first()
    )
    if not report or not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF不存在")
    report_root = Path("data/reports").resolve()
    candidate = Path(report.pdf_path).resolve()
    try:
        candidate.relative_to(report_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="PDF路径无效")
    if candidate.suffix.lower() != ".pdf" or not candidate.is_file():
        raise HTTPException(status_code=404, detail="PDF文件已丢失")
    return FileResponse(
        str(candidate),
        media_type="application/pdf",
        filename=f"心岛情绪报告_{report_code}.pdf",
    )
