"""学生结构化心理状态评估 API。"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from agents.wellbeing_assessment import ALLOWED_EMOTIONS, ITEM_LABELS, WellbeingAssessmentOrchestrator
from auth import get_current_user
from config import settings
from database import get_db
from models import SensitiveAccessLog, StudentAssessmentAgentRun, StudentWellbeingAssessment, User


router = APIRouter(prefix="/api/assessment", tags=["student-assessment"])
RETENTION_DAYS = 30
CONSENT_VERSION = "student-assessment-ai-v1"

FREQUENCY_OPTIONS = [
    {"value": "never", "label": "没有"},
    {"value": "several_days", "label": "有几天"},
    {"value": "more_than_half", "label": "一半以上时间"},
    {"value": "nearly_every_day", "label": "几乎每天"},
    {"value": "unsure", "label": "不确定／不想回答"},
]

QUESTION_GROUPS = [
    {"id": "emotion", "title": "情绪体验", "questions": [
        {"id": "low_mood", "text": "过去两周，有多少时候感到低落、难过或提不起精神？"},
        {"id": "low_interest", "text": "过去两周，有多少时候难以从平时喜欢的事情中获得兴趣？"},
        {"id": "worry", "text": "过去两周，有多少时候感到紧张、担心或难以放松？"},
    ]},
    {"id": "rhythm", "title": "睡眠与精力", "questions": [
        {"id": "sleep", "text": "过去两周，睡眠节律受到影响的情况有多频繁？"},
        {"id": "energy", "text": "过去两周，精力不足或容易疲惫的情况有多频繁？"},
    ]},
    {"id": "functioning", "title": "学习与日常", "questions": [
        {"id": "concentration", "text": "过去两周，集中注意比较困难的情况有多频繁？"},
        {"id": "school_impact", "text": "过去两周，当前状态影响上课、作业或到校的情况有多频繁？"},
        {"id": "home_impact", "text": "过去两周，当前状态影响吃饭、洗漱或家庭生活的情况有多频繁？"},
        {"id": "loneliness", "text": "过去两周，感到孤单或难以获得支持的情况有多频繁？"},
    ]},
]


class AssessmentSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: dict[str, Literal["never", "several_days", "more_than_half", "nearly_every_day", "unsure"]]
    emotions: list[str] = Field(default_factory=list, max_length=3)
    self_harm: Literal["no", "unsure", "yes"]
    unsafe_home: Literal["no", "unsure", "yes"]
    external_ai_consent_version: Literal["student-assessment-ai-v1"] | None = None

    @field_validator("answers")
    @classmethod
    def validate_answer_keys(cls, value):
        if set(value) != set(ITEM_LABELS):
            missing = sorted(set(ITEM_LABELS) - set(value))
            extra = sorted(set(value) - set(ITEM_LABELS))
            raise ValueError(f"评估题目不完整；missing={missing}; extra={extra}")
        return value

    @field_validator("emotions")
    @classmethod
    def validate_emotions(cls, value):
        if any(item not in ALLOWED_EMOTIONS for item in value):
            raise ValueError("包含不支持的情绪标签")
        return list(dict.fromkeys(value))


def _audit(db: Session, user_id: int, action: str, resource_id: str, result: str) -> None:
    db.add(SensitiveAccessLog(
        actor_user_id=user_id,
        action=action,
        resource_type="student_wellbeing_assessment",
        resource_id=resource_id,
        result=result,
    ))


def _cleanup(db: Session, user_id: int) -> None:
    now = datetime.now()
    expired = db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.user_id == user_id,
        StudentWellbeingAssessment.expires_at <= now,
        StudentWellbeingAssessment.deleted_at.is_(None),
    ).all()
    for row in expired:
        row.deleted_at = now
        row.answers_json = "{}"
        row.result_json = "{}"


def _response(row: StudentWellbeingAssessment, db: Session) -> dict:
    result = json.loads(row.result_json)
    runs = db.query(StudentAssessmentAgentRun).filter(
        StudentAssessmentAgentRun.assessment_id == row.id,
    ).order_by(StudentAssessmentAgentRun.id).all()
    result.update({
        "assessment_code": row.assessment_code,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "expires_at": row.expires_at.isoformat(),
        "agent_runs": [{
            "agent": item.agent_type,
            "status": item.status,
            "summary": item.summary,
            "evidence_ids": json.loads(item.evidence_json or "[]"),
            "model_name": item.model_name,
            "degraded": bool(item.degraded),
        } for item in runs],
    })
    return result


@router.get("/schema")
def assessment_schema(current_user: User = Depends(get_current_user)):
    return {
        "version": "wellbeing-assessment-v1",
        "period": "过去两周",
        "title": "近两周支持需求自评",
        "boundary": "这是尚待专业人员审核的支持需求观察，不是经验证的心理量表、医学诊断或专业评估，不能替代专业人员面谈。",
        "method_note": "采用主动回答、功能影响、安全项和信息缺口进行保守分流；不计算总分，不依据游戏行为推断心理状态。",
        "references": [
            {
                "title": "教育部等十七部门全面加强和改进新时代学生心理健康工作专项行动计划（2023—2025年）",
                "url": "https://www.moe.gov.cn/srcsite/A17/moe_943/moe_946/202305/t20230511_1059219.html",
            },
            {
                "title": "教育部关于学生心理健康监测预警与分级支持的相关要求",
                "url": "https://hudong.moe.gov.cn/srcsite/A06/s3325/202510/t20251020_1417420.html",
            },
        ],
        "frequency_options": FREQUENCY_OPTIONS,
        "groups": QUESTION_GROUPS,
        "emotion_options": sorted(ALLOWED_EMOTIONS - {"不确定"}),
        "safety_questions": [
            {"id": "self_harm", "text": "现在或过去两周，是否出现过伤害自己、不想活下去，或已经采取相关行动的情况？"},
            {"id": "unsafe_home", "text": "你现在是否因为暴力、威胁、性伤害或某位照护者而无法安全回家或待在家中？"},
        ],
        "safety_options": [
            {"value": "no", "label": "没有"},
            {"value": "unsure", "label": "不确定／不便回答"},
            {"value": "yes", "label": "有"},
        ],
        "external_ai_consent_version": CONSENT_VERSION,
    }


@router.post("/submit", status_code=201)
async def submit_assessment(
    payload: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _cleanup(db, current_user.id)
    answers = {**payload.answers, "self_harm": payload.self_harm, "unsafe_home": payload.unsafe_home}
    external_ai_allowed = bool(
        settings.ALLOW_EXTERNAL_AI
        and settings.ALLOW_STUDENT_EXTERNAL_AI
        and payload.external_ai_consent_version == CONSENT_VERSION
    )
    assessment_code = f"ASSESS-{datetime.now():%Y%m%d}-{secrets.token_hex(4).upper()}"
    result = await WellbeingAssessmentOrchestrator().run(
        answers=answers,
        emotions=payload.emotions,
        external_ai_allowed=external_ai_allowed,
    )
    if result.model_name == "xunfei-constrained" or result.degraded:
        _audit(
            db, current_user.id, "external_model_transfer_assessment", assessment_code,
            "consented_derived_fields_only" if result.model_name == "xunfei-constrained" else "failed",
        )
    row = StudentWellbeingAssessment(
        assessment_code=assessment_code,
        user_id=current_user.id,
        answers_json=json.dumps({"answers": payload.answers, "emotions": payload.emotions, "self_harm": payload.self_harm, "unsafe_home": payload.unsafe_home}, ensure_ascii=False),
        result_json=result.model_dump_json(),
        risk_level=result.risk_level,
        review_status=result.review_status,
        external_ai_consent_version=payload.external_ai_consent_version,
        model_name=result.model_name,
        prompt_version=result.prompt_version,
        degraded=int(result.degraded),
        expires_at=datetime.now() + timedelta(days=RETENTION_DAYS),
    )
    db.add(row)
    db.flush()
    for index, step in enumerate(result.pipeline):
        db.add(StudentAssessmentAgentRun(
            run_code=f"{assessment_code}-{index + 1}",
            assessment_id=row.id,
            agent_type=step.agent,
            status=step.status,
            summary=step.summary,
            output_json=json.dumps({"step_id": step.id}, ensure_ascii=False),
            evidence_json=json.dumps(step.evidence_ids, ensure_ascii=False),
            model_name=result.model_name if step.id in {"emotion", "planning"} else "deterministic-policy",
            prompt_version=result.prompt_version,
            degraded=int(result.degraded and step.id in {"emotion", "planning"}),
        ))
    _audit(db, current_user.id, "create_self_assessment", assessment_code, result.risk_level)
    db.commit()
    db.refresh(row)
    return _response(row, db)


@router.get("/latest")
def latest_assessment(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _cleanup(db, current_user.id)
    row = db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.user_id == current_user.id,
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > datetime.now(),
    ).order_by(StudentWellbeingAssessment.created_at.desc(), StudentWellbeingAssessment.id.desc()).first()
    db.commit()
    return {"assessment": _response(row, db) if row else None}


@router.delete("/{assessment_code}", status_code=204)
def delete_assessment(
    assessment_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.assessment_code == assessment_code,
        StudentWellbeingAssessment.user_id == current_user.id,
        StudentWellbeingAssessment.deleted_at.is_(None),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="评估不存在或已删除")
    row.deleted_at = datetime.now()
    row.answers_json = "{}"
    row.result_json = "{}"
    _audit(db, current_user.id, "delete_self_assessment", assessment_code, "deleted")
    db.commit()
