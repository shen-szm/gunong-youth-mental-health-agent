"""教师工作台 API：最小支持摘要、个案查看申请、审批与原文审计访问。"""

from datetime import datetime, timedelta
import hashlib
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import screening_engine
from auth import require_admin_teacher, require_teacher
from app_time import china_day_start_naive, china_now_naive
from database import get_db
from guardian_engine import _context_has_urgent_meaning
from models import ChatMessage, MoodRecord, SensitiveAccessLog, StudentCaseAccessRequest, StudentExternalAiAuthorization, StudentScreeningRun, StudentSupportRun, StudentWellbeingAssessment, TeacherReviewReport, TeacherReviewReportDecision, TeacherStudentAssignment, TeacherWorkProductSnapshot, TeacherWorkProductTaskDecision, User, UserSession
from student_ai_authorization import AUTHORIZATION_VERSION, get_student_ai_authorization, student_ai_authorization_payload, student_ai_authorization_payloads, student_external_ai_allowed
from teacher_review_engine import build_teacher_review_report
from teacher_review_pdf import generate_teacher_review_pdf


router = APIRouter(prefix="/api/teacher", tags=["teacher"])


class AccessRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=10, max_length=500)
    scope: str = Field(default="recent_30_days", pattern=r"^recent_30_days$")


class AccessDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern=r"^(approved|rejected)$")
    note: str = Field(default="", max_length=300)


class WarningHandleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(default="", max_length=500)


class LessonPlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template: str = Field(default="", max_length=80)
    topic: str = Field(min_length=2, max_length=120)
    context: str = Field(default="", max_length=1000)


class TeacherAccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_admin: bool


class StudentAssignmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    teacher_user_id: int
    student_user_id: int
    active: bool = True


class WorkProductTaskDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(min_length=12, max_length=120, pattern=r"^WP-[A-Za-z0-9-]+$")
    task_index: int = Field(ge=0, le=2)
    decision: str = Field(pattern=r"^(confirmed|revoked)$")


class StudentAiAuthorizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool
    authority_confirmed: bool = False
    expires_days: int = Field(default=30, ge=1, le=365)


class TeacherReviewDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern=r"^(reviewed|revision_requested)$")
    checklist_confirmed: bool = False
    evidence_gap_acknowledged: bool = False
    note: str = Field(default="", max_length=1000)


def _audit(db: Session, actor: User, action: str, resource_type: str, resource_id: str, result: str) -> None:
    db.add(SensitiveAccessLog(
        actor_user_id=actor.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        created_at=china_now_naive(),
    ))
    db.commit()


def _is_admin_teacher(user: User) -> bool:
    return int(user.is_admin or 0) >= 2


def _require_student_responsibility(db: Session, teacher: User, student_id: int) -> None:
    student = db.query(User).filter(User.id == student_id, User.is_admin == 0).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if _is_admin_teacher(teacher):
        return
    assigned = db.query(TeacherStudentAssignment).filter(
        TeacherStudentAssignment.teacher_user_id == teacher.id,
        TeacherStudentAssignment.student_user_id == student_id,
        TeacherStudentAssignment.active == 1,
    ).first()
    if not assigned:
        _audit(db, teacher, "access_student_warning", "student", str(student_id), "denied_unassigned")
        raise HTTPException(status_code=403, detail="该学生不在当前教师职责范围内")


def _latest_approved_request(db: Session, teacher_id: int, student_id: int) -> StudentCaseAccessRequest | None:
    return (
        db.query(StudentCaseAccessRequest)
        .filter(
            StudentCaseAccessRequest.teacher_user_id == teacher_id,
            StudentCaseAccessRequest.student_user_id == student_id,
            StudentCaseAccessRequest.status == "approved",
            StudentCaseAccessRequest.expires_at > china_now_naive(),
        )
        .order_by(StudentCaseAccessRequest.reviewed_at.desc())
        .first()
    )


def _require_student_access(db: Session, teacher: User, student_id: int, request_id: int | None = None) -> StudentCaseAccessRequest | None:
    student = db.query(User).filter(User.id == student_id, User.is_admin == 0).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if _is_admin_teacher(teacher):
        return None
    assigned = db.query(TeacherStudentAssignment).filter(
        TeacherStudentAssignment.teacher_user_id == teacher.id,
        TeacherStudentAssignment.student_user_id == student_id,
        TeacherStudentAssignment.active == 1,
    ).first()
    if not assigned:
        _audit(db, teacher, "view_student_case", "student", str(student_id), "denied_unassigned")
        raise HTTPException(status_code=403, detail="该学生不在当前教师职责范围内")
    query = db.query(StudentCaseAccessRequest).filter(
        StudentCaseAccessRequest.teacher_user_id == teacher.id,
        StudentCaseAccessRequest.student_user_id == student_id,
        StudentCaseAccessRequest.status == "approved",
        StudentCaseAccessRequest.expires_at > china_now_naive(),
    )
    if request_id is not None:
        query = query.filter(StudentCaseAccessRequest.id == request_id)
    approved = query.order_by(StudentCaseAccessRequest.reviewed_at.desc()).first()
    if not approved:
        _audit(db, teacher, "view_student_case", "student", str(student_id), "denied")
        raise HTTPException(status_code=403, detail="该学生个案尚未获管理员教师审批")
    return approved


def _student_access_state(db: Session, teacher: User, student_id: int) -> dict:
    return _student_access_states(db, teacher, [student_id])[student_id]


def _student_access_states(db: Session, teacher: User, student_ids: list[int]) -> dict[int, dict]:
    if _is_admin_teacher(teacher):
        return {
            student_id: {"status": "direct", "request_id": None, "label": "管理员教师可直接查看"}
            for student_id in student_ids
        }
    rows = db.query(StudentCaseAccessRequest).filter(
        StudentCaseAccessRequest.teacher_user_id == teacher.id,
        StudentCaseAccessRequest.student_user_id.in_(student_ids),
    ).order_by(StudentCaseAccessRequest.created_at.desc()).all() if student_ids else []
    latest = {}
    for row in rows:
        latest.setdefault(row.student_user_id, row)
    labels = {"pending": "等待管理员教师审批", "approved": "已获批，可查看", "rejected": "申请未通过", "revoked": "授权已撤销，需重新申请"}
    states = {}
    now = china_now_naive()
    for student_id in student_ids:
        row = latest.get(student_id)
        if not row:
            states[student_id] = {"status": "not_requested", "request_id": None, "label": "需要提交查看申请"}
        elif row.status == "approved" and (not row.expires_at or row.expires_at <= now):
            states[student_id] = {"status": "expired", "request_id": row.id, "label": "授权已到期，需重新申请"}
        else:
            states[student_id] = {"status": row.status, "request_id": row.id, "label": labels.get(row.status, row.status)}
    return states


def _warning_statuses(
    db: Session,
    teacher: User,
    risk_summaries: dict[int, tuple[str, int, bool, datetime | None]],
) -> dict[int, str]:
    student_ids = list(risk_summaries)
    resource_ids = [str(student_id) for student_id in student_ids]
    rows = db.query(SensitiveAccessLog).filter(
        SensitiveAccessLog.actor_user_id == teacher.id,
        SensitiveAccessLog.action == "record_warning_followup",
        SensitiveAccessLog.resource_type == "student",
        SensitiveAccessLog.resource_id.in_(resource_ids),
        SensitiveAccessLog.result == "allowed",
    ).order_by(SensitiveAccessLog.created_at.desc()).all() if resource_ids else []
    latest_followups = {}
    for row in rows:
        latest_followups.setdefault(row.resource_id, row.created_at)
    return {
        student_id: "handled"
        if latest_followups.get(str(student_id))
        and (risk_summaries[student_id][3] is None or latest_followups[str(student_id)] >= risk_summaries[student_id][3])
        else "pending"
        for student_id in student_ids
    }


def _has_urgent_signal(db: Session, student_id: int, since: datetime | None = None) -> bool:
    since = since or china_now_naive() - timedelta(days=30)
    mood_texts = db.query(MoodRecord.content).filter(MoodRecord.user_id == student_id, MoodRecord.created_at >= since).all()
    chat_texts = db.query(ChatMessage.content).filter(
        ChatMessage.user_id == student_id,
        ChatMessage.role == "user",
        ChatMessage.created_at >= since,
    ).all()
    urgent_assessment = db.query(StudentWellbeingAssessment.id).filter(
        StudentWellbeingAssessment.user_id == student_id,
        StudentWellbeingAssessment.created_at >= since,
        StudentWellbeingAssessment.risk_level == "urgent",
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > china_now_naive(),
    ).first()
    urgent_screening = db.query(StudentScreeningRun.id).filter(
        StudentScreeningRun.user_id == student_id,
        StudentScreeningRun.created_at >= since,
        StudentScreeningRun.item9_positive == 1,
        StudentScreeningRun.safety_flag_active == 1,
        StudentScreeningRun.deleted_at.is_(None),
        StudentScreeningRun.expires_at > china_now_naive(),
    ).first()
    return bool(urgent_assessment or urgent_screening) or any(_context_has_urgent_meaning(text or "") for (text,) in [*mood_texts, *chat_texts])


def _warning_followup_state(db: Session, teacher: User, student_id: int) -> tuple[str, datetime | None]:
    """A handled warning stays handled until the student creates a newer record."""
    latest_mood = db.query(MoodRecord).filter(MoodRecord.user_id == student_id).order_by(MoodRecord.created_at.desc()).first()
    latest_chat = db.query(ChatMessage).filter(
        ChatMessage.user_id == student_id,
        ChatMessage.role == "user",
    ).order_by(ChatMessage.created_at.desc()).first()
    latest_assessment = db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.user_id == student_id,
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > china_now_naive(),
    ).order_by(StudentWellbeingAssessment.created_at.desc()).first()
    signal_times = [item.created_at for item in (latest_mood, latest_chat, latest_assessment) if item and item.created_at]
    latest_signal_at = max(signal_times) if signal_times else None
    latest_followup = db.query(SensitiveAccessLog).filter(
        SensitiveAccessLog.actor_user_id == teacher.id,
        SensitiveAccessLog.action == "record_warning_followup",
        SensitiveAccessLog.resource_type == "student",
        SensitiveAccessLog.resource_id == str(student_id),
        SensitiveAccessLog.result == "allowed",
    ).order_by(SensitiveAccessLog.created_at.desc()).first()
    handled = bool(latest_followup and (latest_signal_at is None or latest_followup.created_at >= latest_signal_at))
    return ("handled" if handled else "pending"), latest_signal_at


def _risk_for_student(db: Session, student_id: int) -> tuple[str, float, int]:
    since = china_now_naive() - timedelta(days=30)
    moods = db.query(MoodRecord).filter(MoodRecord.user_id == student_id, MoodRecord.created_at >= since).all()
    latest_assessment = db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.user_id == student_id,
        StudentWellbeingAssessment.created_at >= since,
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > china_now_naive(),
    ).order_by(StudentWellbeingAssessment.created_at.desc()).first()
    screening_risk = screening_engine.active_screening_risk(db, student_id)
    if screening_risk in {"urgent", "professional"}:
        return "high", 0.0, len(moods)
    if latest_assessment and latest_assessment.risk_level in {"urgent", "professional"}:
        return "high", 0.0, len(moods)
    if screening_risk == "watch":
        return "middle", 0.0, len(moods)
    if latest_assessment and latest_assessment.risk_level == "watch":
        return "middle", 0.0, len(moods)
    if _has_urgent_signal(db, student_id, since):
        return "high", 0.0, len(moods)
    if not moods:
        return "low", 0.0, 0
    negative_count = sum(item.mood_label in {"难过", "焦虑", "愤怒"} for item in moods)
    return ("high" if negative_count >= 4 else "middle" if negative_count >= 1 else "low"), 0.0, len(moods)


def _risk_summaries_for_students(db: Session, student_ids: list[int]) -> dict[int, tuple[str, int, bool, datetime | None]]:
    """批量计算概览分流，避免教师首页按学生执行多轮查询。"""
    if not student_ids:
        return {}
    since = china_now_naive() - timedelta(days=30)
    now = china_now_naive()
    mood_rows = db.query(MoodRecord.user_id, MoodRecord.mood_label, MoodRecord.content, MoodRecord.created_at).filter(
        MoodRecord.user_id.in_(student_ids),
        MoodRecord.created_at >= since,
    ).all()
    chat_rows = db.query(ChatMessage.user_id, ChatMessage.content, ChatMessage.created_at).filter(
        ChatMessage.user_id.in_(student_ids),
        ChatMessage.role == "user",
        ChatMessage.created_at >= since,
    ).all()
    assessment_rows = db.query(
        StudentWellbeingAssessment.user_id,
        StudentWellbeingAssessment.risk_level,
        StudentWellbeingAssessment.created_at,
    ).filter(
        StudentWellbeingAssessment.user_id.in_(student_ids),
        StudentWellbeingAssessment.created_at >= since,
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > now,
    ).order_by(StudentWellbeingAssessment.user_id, StudentWellbeingAssessment.created_at).all()
    screening_rows = screening_engine.latest_screenings_for_students(db, student_ids)
    screening_levels = {
        student_id: screening_engine.run_risk(row, now=now)
        for student_id, row in screening_rows.items()
    }
    screening_high_ids = {
        student_id for student_id, level in screening_levels.items()
        if level in {"urgent", "professional"}
    }
    screening_middle_ids = {
        student_id for student_id, level in screening_levels.items() if level == "watch"
    }
    screening_urgent_ids = {
        student_id for student_id, level in screening_levels.items() if level == "urgent"
    }

    mood_counts = {student_id: 0 for student_id in student_ids}
    negative_counts = {student_id: 0 for student_id in student_ids}
    urgent_text_ids: set[int] = set()
    latest_assessment = {}
    urgent_assessment_ids: set[int] = set()
    immediate_assessment_ids: set[int] = set()
    latest_signal_at: dict[int, datetime] = {}
    for student_id, label, content, created_at in mood_rows:
        mood_counts[student_id] += 1
        negative_counts[student_id] += int(label in {"难过", "焦虑", "愤怒"})
        if _context_has_urgent_meaning(content or ""):
            urgent_text_ids.add(student_id)
        if created_at and (student_id not in latest_signal_at or created_at > latest_signal_at[student_id]):
            latest_signal_at[student_id] = created_at
    for student_id, content, created_at in chat_rows:
        if _context_has_urgent_meaning(content or ""):
            urgent_text_ids.add(student_id)
        if created_at and (student_id not in latest_signal_at or created_at > latest_signal_at[student_id]):
            latest_signal_at[student_id] = created_at
    for student_id, risk_level, created_at in assessment_rows:
        latest_assessment[student_id] = risk_level
        if risk_level in {"urgent", "professional"}:
            urgent_assessment_ids.add(student_id)
        if risk_level == "urgent":
            immediate_assessment_ids.add(student_id)
        if created_at and (student_id not in latest_signal_at or created_at > latest_signal_at[student_id]):
            latest_signal_at[student_id] = created_at
    for student_id, row in screening_rows.items():
        if row.created_at and (
            student_id not in latest_signal_at or row.created_at > latest_signal_at[student_id]
        ):
            latest_signal_at[student_id] = row.created_at

    summaries = {}
    for student_id in student_ids:
        latest_level = latest_assessment.get(student_id)
        if (
            student_id in urgent_assessment_ids
            or student_id in urgent_text_ids
            or student_id in screening_high_ids
        ):
            level = "high"
        elif latest_level == "watch" or student_id in screening_middle_ids:
            level = "middle"
        elif negative_counts[student_id] >= 4:
            level = "high"
        elif negative_counts[student_id] >= 1:
            level = "middle"
        else:
            level = "low"
        urgent = (
            student_id in immediate_assessment_ids
            or student_id in urgent_text_ids
            or student_id in screening_urgent_ids
        )
        summaries[student_id] = (level, mood_counts[student_id], urgent, latest_signal_at.get(student_id))
    return summaries


def _activity_student_ids(db: Session, since: datetime | None = None) -> set[int]:
    """固定集合查询，避免按学生逐个探测记录造成 N+1。"""
    mood_query = db.query(MoodRecord.user_id)
    chat_query = db.query(ChatMessage.user_id).filter(ChatMessage.role == "user")
    assessment_query = db.query(StudentWellbeingAssessment.user_id).filter(
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > china_now_naive(),
    )
    screening_query = db.query(StudentScreeningRun.user_id).filter(
        StudentScreeningRun.deleted_at.is_(None),
        StudentScreeningRun.expires_at > china_now_naive(),
    )
    if since is not None:
        mood_query = mood_query.filter(MoodRecord.created_at >= since)
        chat_query = chat_query.filter(ChatMessage.created_at >= since)
        assessment_query = assessment_query.filter(StudentWellbeingAssessment.created_at >= since)
        screening_query = screening_query.filter(StudentScreeningRun.created_at >= since)
    return {
        int(row[0])
        for query in (mood_query, chat_query, assessment_query, screening_query)
        for row in query.distinct().all()
    }


def _visible_roster_students(db: Session, query, activity_ids: set[int] | None = None) -> list[User]:
    """隐藏从未产生交互的临时访客；一旦有记录就进入教师职责视图。"""
    active_ids = activity_ids if activity_ids is not None else _activity_student_ids(db)
    return [
        student for student in query.order_by(User.id).all()
        if not (
            str(student.username or "").lower().startswith(("guest_", "demo_"))
            and student.id not in active_ids
        )
    ]


@router.get("/class-overview")
def class_overview(db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    student_query = db.query(User).filter(User.is_admin == 0)
    if not _is_admin_teacher(teacher):
        assigned_ids = db.query(TeacherStudentAssignment.student_user_id).filter(
            TeacherStudentAssignment.teacher_user_id == teacher.id,
            TeacherStudentAssignment.active == 1,
        )
        student_query = student_query.filter(User.id.in_(assigned_ids))
    students = _visible_roster_students(db, student_query)
    risk_summaries = _risk_summaries_for_students(db, [item.id for item in students])
    risks = [risk_summaries[item.id][0] for item in students]
    today_active_ids = _activity_student_ids(db, china_day_start_naive())
    pending = db.query(StudentCaseAccessRequest).filter(StudentCaseAccessRequest.status == "pending").count()
    return {
        "total_students": len(students),
        "today_active": sum(item.id in today_active_ids for item in students),
        "pending_warnings": sum(level in {"high", "middle"} for level in risks),
        "pending_access_requests": pending if _is_admin_teacher(teacher) else 0,
        "risk_counts": {level: risks.count(level) for level in ("low", "middle", "high")},
        "teacher_role": "admin_teacher" if _is_admin_teacher(teacher) else "teacher",
    }


@router.get("/student-list")
def student_list(db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    items = []
    student_query = db.query(User).filter(User.is_admin == 0)
    if not _is_admin_teacher(teacher):
        assigned_ids = db.query(TeacherStudentAssignment.student_user_id).filter(
            TeacherStudentAssignment.teacher_user_id == teacher.id,
            TeacherStudentAssignment.active == 1,
        )
        student_query = student_query.filter(User.id.in_(assigned_ids))
    students = _visible_roster_students(db, student_query)
    student_ids = [student.id for student in students]
    risk_summaries = _risk_summaries_for_students(db, student_ids)
    screening_rows = screening_engine.latest_screenings_for_students(db, student_ids)
    access_states = _student_access_states(db, teacher, student_ids)
    authorization_payloads = student_ai_authorization_payloads(db, student_ids)
    for student in students:
        risk, count, _urgent, _latest_signal_at = risk_summaries[student.id]
        items.append({
            "id": student.id,
            "nickname": student.nickname or f"学生{student.id}",
            "risk_level": risk,
            "mood_count": count,
            "screening": screening_engine.to_teacher_summary(screening_rows.get(student.id)),
            "access": access_states[student.id],
            "external_ai_authorization": authorization_payloads[student.id],
        })
    return {"students": items}


@router.get("/students/{student_id}/external-ai-authorization")
def get_external_ai_authorization(student_id: int, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    _require_student_responsibility(db, teacher, student_id)
    _audit(db, teacher, "view_student_ai_authorization", "student", str(student_id), "allowed")
    return student_ai_authorization_payload(db, student_id)


@router.post("/students/{student_id}/external-ai-authorization")
def set_external_ai_authorization(
    student_id: int,
    payload: StudentAiAuthorizationInput,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    _require_student_responsibility(db, teacher, student_id)
    if payload.active and not payload.authority_confirmed:
        raise HTTPException(status_code=400, detail="启用前必须确认已核验学校或监护人的有效授权依据")
    now = china_now_naive()
    row = get_student_ai_authorization(db, student_id)
    if not row:
        row = StudentExternalAiAuthorization(
            student_user_id=student_id,
            authorized_by_user_id=teacher.id,
            basis="school_guardian_authority",
            statement_version=AUTHORIZATION_VERSION,
            purpose="student_support_agents",
            status="active" if payload.active else "revoked",
            expires_at=now + timedelta(days=payload.expires_days),
            revoked_at=None if payload.active else now,
        )
        db.add(row)
    else:
        row.authorized_by_user_id = teacher.id
        row.statement_version = AUTHORIZATION_VERSION
        row.purpose = "student_support_agents"
        row.status = "active" if payload.active else "revoked"
        row.expires_at = now + timedelta(days=payload.expires_days)
        row.revoked_at = None if payload.active else now
    db.flush()
    _audit(
        db,
        teacher,
        "enable_student_external_ai" if payload.active else "revoke_student_external_ai",
        "student",
        str(student_id),
        "authority_verified" if payload.active else "revoked",
    )
    return student_ai_authorization_payload(db, student_id)


@router.get("/warning-list")
def warning_list(db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    rows = []
    student_query = db.query(User).filter(User.is_admin == 0)
    if not _is_admin_teacher(teacher):
        assigned_ids = db.query(TeacherStudentAssignment.student_user_id).filter(
            TeacherStudentAssignment.teacher_user_id == teacher.id,
            TeacherStudentAssignment.active == 1,
        )
        student_query = student_query.filter(User.id.in_(assigned_ids))
    students = _visible_roster_students(db, student_query)
    student_ids = [student.id for student in students]
    risk_summaries = _risk_summaries_for_students(db, student_ids)
    screening_rows = screening_engine.latest_screenings_for_students(db, student_ids)
    access_states = _student_access_states(db, teacher, student_ids)
    statuses = _warning_statuses(db, teacher, risk_summaries)
    for student in students:
        risk, count, urgent, latest_signal_at = risk_summaries[student.id]
        if risk not in {"high", "middle"}:
            continue
        screening = screening_engine.to_teacher_summary(screening_rows.get(student.id))
        if screening and screening["safety_active"]:
            reason = "标准筛查第9题有应答，需要立即线下核实安全"
        elif screening and screening["risk_level"] in {"urgent", "professional"}:
            reason = "标准筛查显示近期支持需求较高（中度/中重度），建议尽快核实"
        elif screening and screening["risk_level"] == "watch":
            reason = f"标准筛查结果为{screening['band_label']}（{screening['total_score']}/27），建议安排一次关怀沟通"
        else:
            reason = "检测到需要立即核实安全的危机表达" if urgent else (
                f"近30天记录显示需要尽快核实支持需求（{count}条）"
                if risk == "high" else f"近30天有需要持续关注的自愿记录（{count}条）"
            )
        rows.append({
            "id": student.id,
            "student_id": student.id,
            "student_name": student.nickname or f"学生{student.id}",
            "risk_level": risk,
            "reason": reason,
            "urgent": urgent,
            "status": statuses[student.id],
            "updated_at": latest_signal_at.isoformat() if latest_signal_at else None,
            "access": access_states[student.id],
        })
    return {"warnings": rows}


@router.get("/warning/{warning_id}/detail")
def warning_detail(warning_id: int, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    _require_student_responsibility(db, teacher, warning_id)
    state = _student_access_state(db, teacher, warning_id)
    urgent = _has_urgent_signal(db, warning_id)
    return {
        "student_id": warning_id,
        "urgent": urgent,
        "detail": "检测到危机表达。安全处置不等待原文审批，审批仅用于后续了解最小必要背景。" if urgent else "系统仅展示自愿记录形成的趋势信号；查看个案原文需要管理员教师审批。",
        "suggestion": "立即线下核实安全并保持陪伴，不让孩子独处，远离危险物；联系可信成年人和管理员教师。拨打12356；如已实施伤害或危险迫近，立即拨打110或120。若监护人可能是伤害来源，联系其他安全成年人、可信教师或报警。" if urgent else "先提交个案查看申请；获批后再结合原文与线下观察创建支持任务。",
        "access": state,
    }


@router.post("/warning/{warning_id}/handle")
def handle_warning(warning_id: int, payload: WarningHandleInput, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    _require_student_responsibility(db, teacher, warning_id)
    _audit(db, teacher, "record_warning_followup", "student", str(warning_id), "allowed")
    return {"status": "handled", "note": payload.note}


@router.post("/students/{student_id}/access-requests", status_code=201)
def create_access_request(student_id: int, payload: AccessRequestInput, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    student = db.query(User).filter(User.id == student_id, User.is_admin == 0).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if _is_admin_teacher(teacher):
        _audit(db, teacher, "admin_direct_case_access", "student", str(student_id), "allowed")
        return {"status": "direct", "request_id": None, "message": "管理员教师可直接查看"}
    assigned = db.query(TeacherStudentAssignment).filter(
        TeacherStudentAssignment.teacher_user_id == teacher.id,
        TeacherStudentAssignment.student_user_id == student_id,
        TeacherStudentAssignment.active == 1,
    ).first()
    if not assigned:
        raise HTTPException(status_code=403, detail="该学生不在当前教师职责范围内")
    duplicate = db.query(StudentCaseAccessRequest).filter(
        StudentCaseAccessRequest.teacher_user_id == teacher.id,
        StudentCaseAccessRequest.student_user_id == student_id,
        StudentCaseAccessRequest.status == "pending",
    ).first()
    if duplicate:
        return {"status": duplicate.status, "request_id": duplicate.id, "idempotent": True}
    row = StudentCaseAccessRequest(
        request_code=f"ACCESS-{china_now_naive():%Y%m%d}-{secrets.token_hex(3).upper()}",
        teacher_user_id=teacher.id,
        student_user_id=student_id,
        reason=payload.reason.strip(),
        scope=payload.scope,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _audit(db, teacher, "submit_case_access_request", "access_request", str(row.id), "allowed")
    return {"status": row.status, "request_id": row.id, "request_code": row.request_code, "idempotent": False}


@router.get("/access-requests")
def list_access_requests(db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    query = db.query(StudentCaseAccessRequest)
    if not _is_admin_teacher(teacher):
        query = query.filter(StudentCaseAccessRequest.teacher_user_id == teacher.id)
    rows = query.order_by(StudentCaseAccessRequest.created_at.desc()).all()
    users = {u.id: u for u in db.query(User).filter(User.id.in_({x for row in rows for x in (row.teacher_user_id, row.student_user_id)})).all()} if rows else {}
    return {"items": [{
        "id": row.id,
        "request_code": row.request_code,
        "teacher_name": (users.get(row.teacher_user_id).nickname or users.get(row.teacher_user_id).username) if users.get(row.teacher_user_id) else "教师",
        "student_id": row.student_user_id,
        "student_name": (users.get(row.student_user_id).nickname or f"学生{row.student_user_id}") if users.get(row.student_user_id) else f"学生{row.student_user_id}",
        "reason": row.reason,
        "scope": row.scope,
        "status": row.status,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    } for row in rows]}


@router.post("/access-requests/{request_id}/decision")
def decide_access_request(request_id: int, payload: AccessDecisionInput, db: Session = Depends(get_db), reviewer: User = Depends(require_admin_teacher)):
    row = db.query(StudentCaseAccessRequest).filter(StudentCaseAccessRequest.id == request_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="申请工单不存在")
    if row.status != "pending":
        return {"status": row.status, "idempotent": True}
    requester = db.query(User).filter(User.id == row.teacher_user_id, User.is_admin == 1).first()
    assignment = db.query(TeacherStudentAssignment).filter(
        TeacherStudentAssignment.teacher_user_id == row.teacher_user_id,
        TeacherStudentAssignment.student_user_id == row.student_user_id,
        TeacherStudentAssignment.active == 1,
    ).first()
    if not requester or not assignment:
        row.status = "revoked"
        row.review_note = "教师角色或学生职责范围已变化，申请自动失效"
        row.reviewer_user_id = reviewer.id
        row.reviewed_at = china_now_naive()
        db.commit()
        _audit(db, reviewer, "revoke_stale_case_access_request", "access_request", str(row.id), "allowed")
        raise HTTPException(status_code=409, detail="申请人的教师角色或学生职责范围已失效")
    row.status = payload.decision
    row.review_note = payload.note.strip()
    row.reviewer_user_id = reviewer.id
    row.reviewed_at = china_now_naive()
    row.expires_at = china_now_naive() + timedelta(days=7) if payload.decision == "approved" else None
    db.commit()
    _audit(db, reviewer, f"{payload.decision}_case_access_request", "access_request", str(row.id), "allowed")
    return {"status": row.status, "idempotent": False}


@router.get("/students/{student_id}/case-context")
def student_case_context(student_id: int, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    approved = _require_student_access(db, teacher, student_id, request_id)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else china_now_naive()
    return _case_context_payload(db, teacher, student_id, approved, cutoff)


def _case_context_payload(db: Session, teacher: User, student_id: int, approved: StudentCaseAccessRequest | None, cutoff: datetime) -> dict:
    since = cutoff - timedelta(days=30)
    moods = db.query(MoodRecord).filter(MoodRecord.user_id == student_id, MoodRecord.created_at >= since, MoodRecord.created_at <= cutoff).order_by(MoodRecord.created_at.desc()).limit(50).all()
    chats = db.query(ChatMessage).filter(ChatMessage.user_id == student_id, ChatMessage.role == "user", ChatMessage.created_at >= since, ChatMessage.created_at <= cutoff).order_by(ChatMessage.created_at.desc()).limit(50).all()
    _audit(db, teacher, "view_student_original_content", "student", str(student_id), "allowed")
    records = [
        *[{"id": f"mood-{row.id}", "source": "情绪记录", "content": row.content or f"选择了“{row.mood_label}”", "emotion": row.mood_label, "created_at": row.created_at.isoformat() if row.created_at else None} for row in moods],
        *[{"id": f"chat-{row.id}", "source": "倾诉原文", "content": row.content, "emotion": row.emotion or "", "created_at": row.created_at.isoformat() if row.created_at else None} for row in chats],
    ]
    records.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "student_id": student_id,
        "access_basis": "admin_direct" if approved is None else "approved_request",
        "request_id": approved.id if approved else None,
        "scope": "recent_30_days",
        "content_cutoff": cutoff.isoformat(),
        "access_expires_at": approved.expires_at.isoformat() if approved and approved.expires_at else None,
        "notice": "原文仅用于该支持工单，不得传播，也不得作为诊断依据。",
        "records": records,
    }


def _bounded_delivery_text(value: object, *, limit: int = 240) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def _verified_student_agent_entry(run: StudentSupportRun) -> tuple[bool, dict | None]:
    """Whitelist the v2 structured handoff; never copy chat, emotion or model evidence fields."""
    try:
        deliverable = json.loads(run.deliverable_json or "{}")
    except (TypeError, ValueError):
        return False, None
    if not isinstance(deliverable, dict):
        return False, None
    raw_contract = deliverable.get("task_contract")
    raw_verification = deliverable.get("verification")
    raw_artifact = deliverable.get("artifact")
    if not all(isinstance(item, dict) for item in (raw_contract, raw_verification, raw_artifact)):
        return False, None

    constraints = [
        _bounded_delivery_text(item, limit=120)
        for item in raw_contract.get("constraints", [])[:8]
        if _bounded_delivery_text(item, limit=120)
    ] if isinstance(raw_contract.get("constraints"), list) else []
    criteria = [
        _bounded_delivery_text(item, limit=120)
        for item in raw_contract.get("acceptance_criteria", [])[:8]
        if _bounded_delivery_text(item, limit=120)
    ] if isinstance(raw_contract.get("acceptance_criteria"), list) else []
    contract = {
        "objective": _bounded_delivery_text(raw_contract.get("objective")),
        "constraints": constraints,
        "acceptance_criteria": criteria,
    }
    artifact = {
        "title": _bounded_delivery_text(raw_artifact.get("title"), limit=80),
        "outcome": _bounded_delivery_text(raw_artifact.get("outcome")),
        "next_action": _bounded_delivery_text(raw_artifact.get("next_action")),
        "next_owner": _bounded_delivery_text(raw_artifact.get("next_owner"), limit=64),
    }
    raw_checks = raw_verification.get("checks")
    check_catalog = {
        "task_contract_complete": ("任务契约完整", "student_agent_check:task_contract_complete"),
        "safety_gate_completed": ("安全分流已先行", "student_agent_check:safety_gate_completed"),
        "output_linked": ("回应交付已落库", "student_agent_check:output_linked"),
        "structured_cues_only": ("最小必要数据边界", "student_agent_check:structured_cues_only"),
        "ordinary_generation_stopped": ("普通生成已停止", "student_agent_check:ordinary_generation_stopped"),
        "safety_output_linked": ("安全回应交付已落库", "student_agent_check:safety_output_linked"),
        "human_handoff_present": ("真人接力路径完整", "student_agent_check:human_handoff_present"),
        "support_line_present": ("心理支持入口可用", "student_agent_check:support_line_present"),
        "emergency_route_present": ("紧急求助路径完整", "student_agent_check:emergency_route_present"),
        "responsibility_assigned": ("下一责任人明确", "student_agent_check:responsibility_assigned"),
    }
    checks = []
    if isinstance(raw_checks, list):
        for item in raw_checks[:10]:
            if not isinstance(item, dict) or item.get("status") not in {"passed", "failed"}:
                continue
            check_id = _bounded_delivery_text(item.get("id"), limit=64)
            if check_id not in check_catalog:
                continue
            label, evidence = check_catalog[check_id]
            checks.append({
                "id": check_id,
                "label": label,
                "status": item["status"],
                "evidence": evidence,
            })
    structurally_complete = bool(
        checks
        and contract["objective"]
        and contract["constraints"]
        and contract["acceptance_criteria"]
        and all(artifact.values())
        and run.status in {"completed", "attention"}
        and run.risk_level in {"routine", "watch", "professional", "urgent"}
        and run.output_message_id is not None
    )
    if not structurally_complete:
        return False, None
    verification_status = (
        "verified"
        if raw_verification.get("status") == "verified" and all(item["status"] == "passed" for item in checks)
        else "needs_attention"
    )
    return True, {
        "run_code": run.run_code,
        "completed_at": (run.completed_at + timedelta(hours=8)).isoformat() if run.completed_at else None,
        "risk_level": run.risk_level,
        "status": run.status,
        "task_contract": contract,
        "verification": {"status": verification_status, "checks": checks},
        "artifact": artifact,
    }


def _student_agent_handoff(
    db: Session,
    *,
    student_id: int,
    scoped_chats: list[ChatMessage],
    scoped_since: datetime,
    scoped_cutoff: datetime,
) -> dict:
    input_message_ids = [row.id for row in scoped_chats]
    if not input_message_ids:
        return {"run_count": 0, "verified_count": 0, "latest": []}
    # StudentSupportRun timestamps are UTC-naive; work-product cutoffs use
    # Asia/Shanghai-naive values. Convert explicitly so approval deadlines
    # cannot include up to eight hours of post-cutoff work.
    since_utc = scoped_since - timedelta(hours=8)
    cutoff_utc = scoped_cutoff - timedelta(hours=8)
    runs = db.query(StudentSupportRun).filter(
        StudentSupportRun.user_id == student_id,
        StudentSupportRun.input_message_id.in_(input_message_ids),
        StudentSupportRun.status.in_(["completed", "attention"]),
        StudentSupportRun.started_at >= since_utc,
        StudentSupportRun.started_at <= cutoff_utc,
        StudentSupportRun.completed_at.isnot(None),
        StudentSupportRun.completed_at <= cutoff_utc,
        StudentSupportRun.output_message_id.isnot(None),
        StudentSupportRun.expires_at > datetime.utcnow(),
        StudentSupportRun.prompt_version == "student-support-orchestrator-v2",
    ).order_by(StudentSupportRun.completed_at.desc(), StudentSupportRun.id.desc()).limit(100).all()
    structured_count = 0
    structured_entries = []
    verified_count = 0
    for run in runs:
        structured, entry = _verified_student_agent_entry(run)
        if structured:
            structured_count += 1
        if entry:
            structured_entries.append(entry)
            if entry["verification"]["status"] == "verified":
                verified_count += 1
    return {
        "run_count": structured_count,
        "verified_count": verified_count,
        "latest": structured_entries[:5],
    }


@router.get("/students/{student_id}/work-product")
def student_work_product(
    student_id: int,
    request_id: int | None = None,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    """在同一授权边界内，把原始记录整理成教师可审核的工作成果。"""
    approved = _require_student_access(db, teacher, student_id, request_id)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else china_now_naive()
    redacted_safety_revision: dict | None = None
    if approved is None:
        day_start = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        existing_direct_snapshot = db.query(TeacherWorkProductSnapshot).filter(
            TeacherWorkProductSnapshot.student_user_id == student_id,
            TeacherWorkProductSnapshot.request_id.is_(None),
            TeacherWorkProductSnapshot.generated_by_user_id == teacher.id,
            # `created_at` is generated by the database in UTC while the case
            # cutoff follows the application's local clock.  Compare the
            # business cutoff here so a same-day task decision does not lose
            # its snapshot around the UTC date boundary.
            TeacherWorkProductSnapshot.content_cutoff >= day_start,
            TeacherWorkProductSnapshot.content_cutoff <= cutoff,
        ).order_by(TeacherWorkProductSnapshot.content_cutoff.desc()).first()
        if existing_direct_snapshot:
            incremental_cutoff = china_now_naive()
            new_moods = db.query(MoodRecord).filter(
                MoodRecord.user_id == student_id,
                MoodRecord.created_at > existing_direct_snapshot.content_cutoff,
                MoodRecord.created_at <= incremental_cutoff,
            ).all()
            new_chats = db.query(ChatMessage).filter(
                ChatMessage.user_id == student_id,
                ChatMessage.role == "user",
                ChatMessage.created_at > existing_direct_snapshot.content_cutoff,
                ChatMessage.created_at <= incremental_cutoff,
            ).all()
            new_urgent_assessment = db.query(StudentWellbeingAssessment.id).filter(
                StudentWellbeingAssessment.user_id == student_id,
                StudentWellbeingAssessment.created_at > existing_direct_snapshot.content_cutoff,
                StudentWellbeingAssessment.created_at <= incremental_cutoff,
                StudentWellbeingAssessment.risk_level == "urgent",
                StudentWellbeingAssessment.deleted_at.is_(None),
                StudentWellbeingAssessment.expires_at > china_now_naive(),
            ).first()
            has_new_assessment = db.query(StudentWellbeingAssessment.id).filter(
                StudentWellbeingAssessment.user_id == student_id,
                StudentWellbeingAssessment.created_at > existing_direct_snapshot.content_cutoff,
                StudentWellbeingAssessment.created_at <= incremental_cutoff,
                StudentWellbeingAssessment.deleted_at.is_(None),
                StudentWellbeingAssessment.expires_at > china_now_naive(),
            ).first()
            has_new_screening = db.query(StudentScreeningRun.id).filter(
                StudentScreeningRun.user_id == student_id,
                StudentScreeningRun.created_at > existing_direct_snapshot.content_cutoff,
                StudentScreeningRun.created_at <= incremental_cutoff,
                StudentScreeningRun.deleted_at.is_(None),
                StudentScreeningRun.expires_at > china_now_naive(),
            ).first()
            has_new_record = bool(
                new_moods or new_chats or has_new_assessment
                or new_urgent_assessment or has_new_screening
            )
            cutoff = incremental_cutoff if has_new_record else existing_direct_snapshot.content_cutoff
    elif approved is not None:
        safety_check_at = china_now_naive()
        post_approval_moods = db.query(MoodRecord).filter(
            MoodRecord.user_id == student_id,
            MoodRecord.created_at > cutoff,
            MoodRecord.created_at <= safety_check_at,
        ).all()
        post_approval_chats = db.query(ChatMessage).filter(
            ChatMessage.user_id == student_id,
            ChatMessage.role == "user",
            ChatMessage.created_at > cutoff,
            ChatMessage.created_at <= safety_check_at,
        ).all()
        post_approval_assessments = db.query(StudentWellbeingAssessment).filter(
            StudentWellbeingAssessment.user_id == student_id,
            StudentWellbeingAssessment.created_at > cutoff,
            StudentWellbeingAssessment.created_at <= safety_check_at,
            StudentWellbeingAssessment.risk_level == "urgent",
            StudentWellbeingAssessment.deleted_at.is_(None),
            StudentWellbeingAssessment.expires_at > china_now_naive(),
        ).all()
        urgent_after_approval = [item for item in [*post_approval_moods, *post_approval_chats] if _context_has_urgent_meaning(item.content or "")]
        urgent_after_approval.extend(post_approval_assessments)
        if urgent_after_approval:
            latest_urgent_at = max(item.created_at for item in urgent_after_approval if item.created_at)
            safety_id = f"safety-{latest_urgent_at.strftime('%Y%m%d%H%M%S%f')}"
            redacted_safety_revision = {
                "id": safety_id,
                "source": "最少必要安全事件",
                "content": "审批截止后检测到新的明确危机信号。新增原文需重新申请权限；安全处置不等待审批。",
                "emotion": "需要立即协助",
                "created_at": latest_urgent_at.isoformat(),
                "redacted": True,
            }
    context = _case_context_payload(db, teacher, student_id, approved, cutoff)
    records = context["records"]
    if redacted_safety_revision:
        records.append(redacted_safety_revision)
    scoped_cutoff = datetime.fromisoformat(context["content_cutoff"])
    scoped_since = scoped_cutoff - timedelta(days=30)
    all_moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == student_id,
        MoodRecord.created_at >= scoped_since,
        MoodRecord.created_at <= scoped_cutoff,
    ).all()
    all_chats = db.query(ChatMessage).filter(
        ChatMessage.user_id == student_id,
        ChatMessage.role == "user",
        ChatMessage.created_at >= scoped_since,
        ChatMessage.created_at <= scoped_cutoff,
    ).all()
    agent_handoff = _student_agent_handoff(
        db,
        student_id=student_id,
        scoped_chats=all_chats,
        scoped_since=scoped_since,
        scoped_cutoff=scoped_cutoff,
    )
    assessments = db.query(StudentWellbeingAssessment).filter(
        StudentWellbeingAssessment.user_id == student_id,
        StudentWellbeingAssessment.created_at >= scoped_since,
        StudentWellbeingAssessment.created_at <= scoped_cutoff,
        StudentWellbeingAssessment.deleted_at.is_(None),
        StudentWellbeingAssessment.expires_at > china_now_naive(),
    ).order_by(StudentWellbeingAssessment.created_at.desc()).all()
    assessment_records = []
    for row in assessments:
        payload = json.loads(row.result_json or "{}")
        domain_text = "、".join(
            f"{item.get('label')}：{item.get('level')}" for item in payload.get("domains", [])
        )
        assessment_records.append({
            "id": f"assessment-{row.id}",
            "source": "支持需求自评",
            "content": f"{payload.get('risk_label', '支持需求观察')}；{domain_text or '领域信息不足'}",
            "emotion": payload.get("emotion_summary", ""),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    records.extend(assessment_records)
    screenings = db.query(StudentScreeningRun).filter(
        StudentScreeningRun.user_id == student_id,
        StudentScreeningRun.created_at >= scoped_since,
        StudentScreeningRun.created_at <= scoped_cutoff,
        StudentScreeningRun.deleted_at.is_(None),
        StudentScreeningRun.expires_at > china_now_naive(),
    ).order_by(StudentScreeningRun.created_at.desc()).all()
    screening_records = []
    for row in screenings:
        content = f"标准筛查：{screening_engine.BAND_LABELS.get(row.band, '')}（{row.total_score}/27）"
        if row.item9_positive:
            content += "；第9题有应答，" + ("安全标记待核实" if row.safety_flag_active else "安全交接已完成")
        screening_records.append({
            "id": f"screening-{row.id}",
            "source": "标准筛查",
            "content": content,
            "emotion": "",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    records.extend(screening_records)
    urgent_records = [
        *[{"id": f"mood-{row.id}", "source": "情绪记录", "content": row.content or f"选择了“{row.mood_label}”", "emotion": row.mood_label, "created_at": row.created_at.isoformat() if row.created_at else None} for row in all_moods if _context_has_urgent_meaning(row.content or "")],
        *[{"id": f"chat-{row.id}", "source": "倾诉原文", "content": row.content, "emotion": row.emotion or "", "created_at": row.created_at.isoformat() if row.created_at else None} for row in all_chats if _context_has_urgent_meaning(row.content or "")],
    ]
    known_ids = {item["id"] for item in records}
    records.extend(item for item in urgent_records if item["id"] not in known_ids)
    records.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    assessment_trigger_ids = [f"assessment-{row.id}" for row in assessments if row.risk_level == "urgent"]
    screening_trigger_ids = [
        f"screening-{row.id}" for row in screenings if row.item9_positive and row.safety_flag_active
    ]
    trigger_evidence_ids = [redacted_safety_revision["id"]] if redacted_safety_revision else []
    trigger_evidence_ids.extend(assessment_trigger_ids)
    trigger_evidence_ids.extend(screening_trigger_ids)
    trigger_evidence_ids.extend(item["id"] for item in records if _context_has_urgent_meaning(str(item.get("content") or "")))
    trigger_evidence_ids = list(dict.fromkeys(trigger_evidence_ids))
    urgent = bool(trigger_evidence_ids)
    mood_records = [item for item in records if item["source"] == "情绪记录"]
    chat_records = [item for item in records if item["source"] == "倾诉原文"]
    evidence_ids = list(dict.fromkeys([*trigger_evidence_ids, *[item["id"] for item in records[:8]]]))
    assessment_risks = [row.risk_level for row in assessments]
    screening_risks = [screening_engine.run_risk(row) for row in screenings]
    negative_count = sum(item.mood_label in {"难过", "焦虑", "愤怒"} for item in all_moods)
    baseline_risk = "high" if negative_count >= 4 else "middle" if negative_count >= 1 else "low"
    if any(level in {"urgent", "professional"} for level in [*assessment_risks, *screening_risks]):
        baseline_risk = "high"
    elif "watch" in [*assessment_risks, *screening_risks] and baseline_risk == "low":
        baseline_risk = "middle"
    if urgent:
        decision = "立即启动校内安全流程：确认学生当下安全、不让其独处并远离危险物，联系家庭之外的可信成年人或教师并拨打12356；存在迫切危险时立即拨打110或120。"
        next_tasks = [
            {"title": "确认当下安全", "owner": "当前教师", "due": "立即", "status": "待确认"},
            {"title": "联系校内心理支持负责人并拨打12356", "owner": "当前教师", "due": "立即", "status": "待执行"},
            {"title": "记录最少必要处置结果", "owner": "当前教师", "due": "处置后", "status": "待执行"},
        ]
        risk = "urgent"
    else:
        if baseline_risk == "high":
            decision = "当天完成一次非诊断性的关怀沟通，并由教师联系校内心理支持负责人共同评估后续支持强度。"
            next_tasks = [
                {"title": "当天确认学生当前状态", "owner": "当前教师", "due": "当天", "status": "待确认"},
                {"title": "联系校内心理支持负责人", "owner": "当前教师", "due": "当天", "status": "待执行"},
                {"title": "安排次日回看", "owner": "当前教师", "due": "次日", "status": "待执行"},
            ]
            risk = "professional"
        else:
            decision = "先进行一次低压力、非诊断性的关怀沟通，再根据学生意愿决定是否连接校内支持资源。"
            next_tasks = [
                {"title": "完成一次10分钟关怀沟通", "owner": "当前教师", "due": "24小时内", "status": "待确认"},
                {"title": "记录学生愿意接受的支持", "owner": "当前教师", "due": "沟通后", "status": "待执行"},
                {"title": "安排3日回看", "owner": "当前教师", "due": "3天后", "status": "待执行"},
            ]
            risk = {"middle": "watch", "low": "routine"}.get(baseline_risk, "routine")
    latest = records[0] if records else None
    access_token = str(context.get("request_id") or f"direct-{teacher.id}")
    cutoff_token = scoped_cutoff.strftime("%Y%m%d%H%M%S%f")
    revision_suffix = f"-S{redacted_safety_revision['id'].removeprefix('safety-')}" if redacted_safety_revision else ""
    product_id = f"WP-{student_id}-{access_token}-{cutoff_token}{revision_suffix}"
    snapshot = db.query(TeacherWorkProductSnapshot).filter(TeacherWorkProductSnapshot.product_id == product_id).first()
    if not snapshot:
        db.add(TeacherWorkProductSnapshot(
            product_id=product_id,
            student_user_id=student_id,
            request_id=context.get("request_id"),
            generated_by_user_id=teacher.id,
            content_cutoff=scoped_cutoff,
            version="teacher-work-product-v2",
        ))
        db.commit()
    task_decisions = db.query(TeacherWorkProductTaskDecision).filter(
        TeacherWorkProductTaskDecision.product_id == product_id,
        TeacherWorkProductTaskDecision.teacher_user_id == teacher.id,
        TeacherWorkProductTaskDecision.status == "confirmed",
    ).all()
    generation = {
        "source": "safety_override" if urgent else "deterministic",
        "model_name": "deterministic",
        "degraded": False,
        "consented": False,
        "prompt_version": "teacher-deterministic-work-product-v2",
        "external_transfer": False,
    }
    _audit(db, teacher, "generate_teacher_work_product", "work_product", product_id, "allowed")
    return {
        "case_id": product_id,
        "version": "teacher-work-product-v2",
        "generated_at": china_now_naive().isoformat(),
        "risk": risk,
        "access_basis": context["access_basis"],
        "request_id": context.get("request_id"),
        "data_from": (datetime.fromisoformat(context["content_cutoff"]) - timedelta(days=30)).isoformat(),
        "content_cutoff": context["content_cutoff"],
        "records": records,
        "pipeline": [
            {"name": "安全分流", "status": "completed", "result": "发现明确紧急信号" if urgent else "未发现明确紧急信号"},
            {"name": "记录归纳", "status": "completed", "result": f"纳入{len(chat_records)}条倾诉、{len(mood_records)}条情绪记录、{len(assessment_records)}次主动评估、{len(screening_records)}次标准筛查"},
            {"name": "证据定位", "status": "completed", "result": f"{len(evidence_ids)}条结论可回到原文"},
            {"name": "支持草案", "status": "completed", "result": "已生成，等待教师确认"},
            {
                "name": "Agent交付验收",
                "status": "completed" if agent_handoff["run_count"] == agent_handoff["verified_count"] else "attention",
                "result": (
                    f"已验收{agent_handoff['verified_count']}/{agent_handoff['run_count']}份结构化交付"
                    if agent_handoff["run_count"]
                    else "授权范围内暂无可接力的学生Agent结构化交付"
                ),
            },
        ],
        "observation": {
            "headline": "当前需要优先确认安全" if urgent else ("近期有值得持续关注的自愿表达" if records else "当前记录不足，建议先沟通补充"),
            "latest_signal": latest["content"][:120] if latest else "暂无可引用记录",
            "record_count": len(records),
            "evidence_ids": evidence_ids,
            "trigger_evidence_ids": trigger_evidence_ids,
        },
        "assessment_summary": ({
            "risk_label": json.loads(assessments[0].result_json).get("risk_label"),
            "emotion_summary": json.loads(assessments[0].result_json).get("emotion_summary"),
            "domains": json.loads(assessments[0].result_json).get("domains", []),
            "support_needs": json.loads(assessments[0].result_json).get("support_needs", []),
            "review_status": assessments[0].review_status,
            "created_at": assessments[0].created_at.isoformat() if assessments[0].created_at else None,
        } if assessments else None),
        "screening_summary": screening_engine.to_teacher_summary(screenings[0] if screenings else None),
        "conflicts": [{"topic": "行动强度", "views": ["尽快介入", "先保持低压力接触"], "resolution": "安全规则优先" if urgent else "由教师结合线下观察确认", "evidence_ids": evidence_ids}],
        "decision": decision,
        "decision_evidence_ids": trigger_evidence_ids or evidence_ids,
        "tasks": [{**task, "evidence_ids": trigger_evidence_ids or evidence_ids} for task in next_tasks],
        "confirmed_task_indices": sorted(item.task_index for item in task_decisions),
        "agent_handoff": agent_handoff,
        "generation": generation,
        "guardrails": ["不作诊断", "不把单条表达当作结论", "敏感触达前由教师确认", "仅使用本次授权范围内记录"],
    }


@router.post("/students/{student_id}/work-product/task-decisions")
def decide_work_product_task(student_id: int, payload: WorkProductTaskDecisionInput, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    approved = _require_student_access(db, teacher, student_id, request_id)
    snapshot = db.query(TeacherWorkProductSnapshot).filter(
        TeacherWorkProductSnapshot.product_id == payload.product_id,
        TeacherWorkProductSnapshot.student_user_id == student_id,
        TeacherWorkProductSnapshot.generated_by_user_id == teacher.id,
    ).first()
    expected_request_id = approved.id if approved else None
    if not snapshot or snapshot.request_id != expected_request_id:
        _audit(db, teacher, "decide_work_product_task", "work_product_task", payload.product_id, "denied_product_scope")
        raise HTTPException(status_code=403, detail="工作成果不属于当前授权范围")
    row = db.query(TeacherWorkProductTaskDecision).filter(
        TeacherWorkProductTaskDecision.product_id == payload.product_id,
        TeacherWorkProductTaskDecision.task_index == payload.task_index,
        TeacherWorkProductTaskDecision.teacher_user_id == teacher.id,
    ).first()
    if row:
        row.status = payload.decision
    else:
        db.add(TeacherWorkProductTaskDecision(
            product_id=payload.product_id,
            task_index=payload.task_index,
            teacher_user_id=teacher.id,
            status=payload.decision,
        ))
    db.commit()
    resource_id = f"{payload.product_id}:{payload.task_index}"
    _audit(db, teacher, f"{payload.decision}_work_product_task", "work_product_task", resource_id, "allowed")
    return {"product_id": payload.product_id, "task_index": payload.task_index, "status": payload.decision, "audited": True}


def _review_report_payload(row: TeacherReviewReport) -> dict:
    if hashlib.sha256((row.report_json or "{}").encode("utf-8")).hexdigest() != row.content_hash:
        raise HTTPException(status_code=409, detail="报告完整性校验失败，请联系管理员核查")
    payload = json.loads(row.report_json or "{}")
    payload.update({
        "report_id": row.report_id,
        "report_version": row.version,
        "status": row.status,
        "review_note": row.review_note,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "created_at": row.created_at.isoformat() if row.created_at else payload.get("generated_at"),
        "content_hash": row.content_hash,
        "revision_number": row.revision_number,
        "parent_report_id": row.parent_report_id,
    })
    return payload


@router.post("/students/{student_id}/review-reports")
async def generate_teacher_review_report(
    student_id: int,
    request_id: int | None = None,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    """在审批边界内运行报告 Agent，并保存不可变内容快照。"""
    approved = _require_student_access(db, teacher, student_id, request_id)
    expected_request_id = approved.id if approved else None
    work_product = student_work_product(student_id=student_id, request_id=request_id, db=db, teacher=teacher)
    snapshot = db.query(TeacherWorkProductSnapshot).filter(
        TeacherWorkProductSnapshot.product_id == work_product["case_id"],
        TeacherWorkProductSnapshot.student_user_id == student_id,
        TeacherWorkProductSnapshot.generated_by_user_id == teacher.id,
        TeacherWorkProductSnapshot.request_id == expected_request_id,
    ).first()
    if not snapshot:
        raise HTTPException(status_code=409, detail="支持工单快照尚未完成")
    scope_key = f"request-{expected_request_id}" if expected_request_id else "direct"
    prior = db.query(TeacherReviewReport).filter(
        TeacherReviewReport.source_product_id == snapshot.product_id,
        TeacherReviewReport.generated_by_user_id == teacher.id,
        TeacherReviewReport.scope_key == scope_key,
        TeacherReviewReport.version == "teacher-review-report-v2",
    ).order_by(TeacherReviewReport.revision_number.desc(), TeacherReviewReport.id.desc()).first()
    if prior and prior.status in {"draft", "reviewed"}:
        _audit(db, teacher, "reuse_teacher_review_report", "teacher_review_report", prior.report_id, "idempotent")
        return _review_report_payload(prior)
    student = db.query(User).filter(User.id == student_id, User.is_admin == 0).first()
    report = await build_teacher_review_report(
        work_product=work_product,
        student_label=(student.nickname or student.username) if student else f"学生 {student_id}",
        teacher_label=teacher.nickname or teacher.username,
        external_ai_allowed=student_external_ai_allowed(db, student_id),
    )
    _require_student_access(db, teacher, student_id, request_id)
    generation = report.get("generation") or {}
    if generation.get("external_transfer_attempted"):
        _audit(db, teacher, "external_ai_transfer_attempt", "teacher_review_report", snapshot.product_id, "succeeded" if generation.get("external_transfer_succeeded") else "failed_safe_degrade")
    report_id = f"TR-{student_id}-{china_now_naive().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"
    report["report_id"] = report_id
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
    row = TeacherReviewReport(
        report_id=report_id,
        student_user_id=student_id,
        request_id=expected_request_id,
        source_product_id=snapshot.product_id,
        generated_by_user_id=teacher.id,
        report_json=serialized,
        content_hash=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        scope_key=scope_key,
        revision_number=(prior.revision_number + 1) if prior else 1,
        parent_report_id=prior.report_id if prior else None,
        status="draft",
        version="teacher-review-report-v2",
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(TeacherReviewReport).filter(
            TeacherReviewReport.source_product_id == snapshot.product_id,
            TeacherReviewReport.generated_by_user_id == teacher.id,
            TeacherReviewReport.scope_key == scope_key,
            TeacherReviewReport.version == "teacher-review-report-v2",
            TeacherReviewReport.revision_number == ((prior.revision_number + 1) if prior else 1),
        ).first()
        if existing:
            _audit(db, teacher, "reuse_teacher_review_report", "teacher_review_report", existing.report_id, "concurrent_idempotent")
            return _review_report_payload(existing)
        raise HTTPException(status_code=409, detail="报告版本冲突，请刷新后重试")
    _audit(db, teacher, "generate_teacher_review_report", "teacher_review_report", report_id, "allowed")
    return _review_report_payload(row)


@router.get("/students/{student_id}/review-reports/latest")
def latest_teacher_review_report(
    student_id: int,
    request_id: int | None = None,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    approved = _require_student_access(db, teacher, student_id, request_id)
    expected_request_id = approved.id if approved else None
    row = db.query(TeacherReviewReport).filter(
        TeacherReviewReport.student_user_id == student_id,
        TeacherReviewReport.request_id == expected_request_id,
        TeacherReviewReport.generated_by_user_id == teacher.id,
    ).order_by(TeacherReviewReport.created_at.desc(), TeacherReviewReport.id.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="尚未生成最终评审报告")
    _audit(db, teacher, "view_teacher_review_report", "teacher_review_report", row.report_id, "allowed")
    return _review_report_payload(row)


@router.get("/students/{student_id}/review-reports/{report_id}/detail")
def exact_teacher_review_report(
    student_id: int, report_id: str, request_id: int | None = None,
    db: Session = Depends(get_db), teacher: User = Depends(require_teacher),
):
    approved = _require_student_access(db, teacher, student_id, request_id)
    row = db.query(TeacherReviewReport).filter_by(
        report_id=report_id, student_user_id=student_id,
        request_id=approved.id if approved else None, generated_by_user_id=teacher.id,
    ).first()
    if not row:
        raise HTTPException(404, "评审报告不存在或不属于当前授权范围")
    payload = _review_report_payload(row)
    _audit(db, teacher, "view_teacher_review_report", "teacher_review_report", report_id, "allowed")
    return payload


@router.post("/students/{student_id}/review-reports/{report_id}/decision")
def decide_teacher_review_report(
    student_id: int,
    report_id: str,
    payload: TeacherReviewDecisionInput,
    request_id: int | None = None,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    approved = _require_student_access(db, teacher, student_id, request_id)
    expected_request_id = approved.id if approved else None
    row = db.query(TeacherReviewReport).filter(
        TeacherReviewReport.report_id == report_id,
        TeacherReviewReport.student_user_id == student_id,
        TeacherReviewReport.request_id == expected_request_id,
        TeacherReviewReport.generated_by_user_id == teacher.id,
    ).first()
    if not row:
        _audit(db, teacher, "review_teacher_report", "teacher_review_report", report_id, "denied_scope")
        raise HTTPException(status_code=404, detail="评审报告不存在或不属于当前授权范围")

    def deny(status_code: int, detail: str, result: str) -> None:
        _audit(db, teacher, "review_teacher_report", "teacher_review_report", report_id, result)
        raise HTTPException(status_code=status_code, detail=detail)

    if row.status == "reviewed":
        deny(409, "已签署报告为终态；如需调整，请生成新的修订版", "denied_terminal_reviewed")
    if row.status == "revision_requested" and payload.decision == "reviewed":
        deny(409, "退回的报告不能直接签署，请先生成新的修订版", "denied_revision_terminal")
    if row.status == "revision_requested" and payload.decision == "revision_requested":
        _audit(db, teacher, "review_teacher_report", "teacher_review_report", report_id, "idempotent_revision_requested")
        return _review_report_payload(row)
    if payload.decision == "reviewed" and not payload.checklist_confirmed:
        deny(400, "签署前必须逐项确认审核清单", "denied_checklist")
    report_snapshot = _review_report_payload(row)
    evidence_audit = report_snapshot.get("evidence_audit") or {}
    evidence_status = evidence_audit.get("status", "insufficient")
    unlinked_claims = int(evidence_audit.get("unlinked_claim_count") or 0)
    if payload.decision == "reviewed" and (evidence_status == "insufficient" or unlinked_claims > 0):
        deny(409, "报告存在证据不足或未关联主张，请退回补充证据后再签署", "denied_evidence_gate")
    if payload.decision == "reviewed" and evidence_status == "partial":
        if not payload.evidence_gap_acknowledged:
            deny(400, "部分可回溯报告需明确确认证据缺口", "denied_gap_ack")
        if len(payload.note.strip()) < 10:
            deny(400, "请记录接受证据缺口的具体理由和线下核对安排", "denied_gap_note")
    if payload.decision == "revision_requested" and len(payload.note.strip()) < 4:
        deny(400, "退回修订时请填写具体说明", "denied_revision_note")
    stored_note = payload.note.strip()
    if payload.decision == "reviewed" and evidence_status == "partial":
        stored_note = f"[已确认证据缺口] {stored_note}"
    reviewed_at = china_now_naive()
    updated = db.query(TeacherReviewReport).filter(
        TeacherReviewReport.id == row.id,
        TeacherReviewReport.status == "draft",
    ).update({
        TeacherReviewReport.status: payload.decision,
        TeacherReviewReport.review_note: stored_note,
        TeacherReviewReport.reviewed_by_user_id: teacher.id,
        TeacherReviewReport.reviewed_at: reviewed_at,
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        current = db.query(TeacherReviewReport).filter(
            TeacherReviewReport.report_id == report_id,
            TeacherReviewReport.student_user_id == student_id,
            TeacherReviewReport.request_id == expected_request_id,
            TeacherReviewReport.generated_by_user_id == teacher.id,
        ).first()
        if current and current.status == "revision_requested" and payload.decision == "revision_requested":
            _audit(db, teacher, "review_teacher_report", "teacher_review_report", report_id, "idempotent_revision_requested")
            return _review_report_payload(current)
        _audit(db, teacher, "review_teacher_report", "teacher_review_report", report_id, "denied_concurrent_terminal")
        raise HTTPException(status_code=409, detail="报告状态已被其他审核操作更新，请刷新后重试")

    db.add(TeacherReviewReportDecision(
        report_id=row.report_id,
        teacher_user_id=teacher.id,
        previous_status="draft",
        decision=payload.decision,
        checklist_confirmed=1 if payload.checklist_confirmed else 0,
        note=stored_note,
    ))
    db.commit()
    _audit(db, teacher, "review_teacher_report", "teacher_review_report", report_id, payload.decision)
    refreshed = db.query(TeacherReviewReport).filter(TeacherReviewReport.id == row.id).first()
    return _review_report_payload(refreshed)


@router.get("/students/{student_id}/review-reports/{report_id}.pdf")
def download_teacher_review_report(
    student_id: int,
    report_id: str,
    request_id: int | None = None,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    approved = _require_student_access(db, teacher, student_id, request_id)
    expected_request_id = approved.id if approved else None
    row = db.query(TeacherReviewReport).filter(
        TeacherReviewReport.report_id == report_id,
        TeacherReviewReport.student_user_id == student_id,
        TeacherReviewReport.request_id == expected_request_id,
        TeacherReviewReport.generated_by_user_id == teacher.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="评审报告不存在或不属于当前授权范围")
    report = _review_report_payload(row)
    content = generate_teacher_review_pdf(report)
    _audit(db, teacher, "download_teacher_review_report", "teacher_review_report", report_id, "allowed")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="teacher-review-{report_id}.pdf"'},
    )


@router.get("/students/{student_id}/profile")
def student_profile(student_id: int, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    approved = _require_student_access(db, teacher, student_id, request_id)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else china_now_naive()
    since = cutoff - timedelta(days=30)
    moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == student_id,
        MoodRecord.created_at >= since,
        MoodRecord.created_at <= cutoff,
    ).all()
    negative_count = sum(item.mood_label in {"难过", "焦虑", "愤怒"} for item in moods)
    urgent = _has_urgent_signal(db, student_id, since) if approved is None else any(
        _context_has_urgent_meaning(item.content or "")
        for item in db.query(ChatMessage).filter(
            ChatMessage.user_id == student_id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= since,
            ChatMessage.created_at <= cutoff,
        ).all()
    ) or any(_context_has_urgent_meaning(item.content or "") for item in moods)
    screening_summary = screening_engine.to_teacher_summary(
        screening_engine.latest_screening(db, student_id, cutoff=cutoff)
    )
    screening_risk = screening_summary["risk_level"] if screening_summary else "routine"
    risk = (
        "high"
        if urgent or negative_count >= 4 or screening_risk in {"urgent", "professional"}
        else "middle"
        if negative_count >= 1 or screening_risk == "watch"
        else "low"
    )
    count = len(moods)
    _audit(db, teacher, "view_student_support_profile", "student", str(student_id), "allowed")
    return {
        "risk_level": risk,
        "mood_count": count,
        "screening_summary": screening_summary,
        "summary": "经授权整理的近30天主动记录摘要；只描述已有材料，不构成心理测评或诊断。",
        "keywords": [],
        "record_window_days": 30,
    }


@router.get("/lesson-plan/templates")
def lesson_templates(teacher: User = Depends(require_teacher)):
    return {"templates": [
        {"id": "stress", "name": "考前压力与自我照顾", "description": "班级通用心理健康教育，不指向具体学生"},
        {"id": "peer", "name": "同伴沟通与求助", "description": "练习表达需要并识别可信支持资源"},
    ]}


@router.post("/lesson-plan/generate")
def generate_lesson(payload: LessonPlanInput, teacher: User = Depends(require_teacher)):
    return {"content": f"主题：{payload.topic}\n目标：帮助学生识别压力信号并练习求助。\n流程：情境引入（5分钟）→小组讨论（15分钟）→支持资源卡（10分钟）→匿名反馈（5分钟）。\n边界：不讨论具体学生个案，不进行疾病诊断。"}


@router.get("/accounts")
def teacher_accounts(db: Session = Depends(get_db), admin: User = Depends(require_admin_teacher)):
    active_ids = _activity_student_ids(db)
    users = [
        user for user in db.query(User).order_by(User.id).all()
        if int(user.is_admin or 0) > 0
        or not str(user.username or "").lower().startswith(("guest_", "demo_"))
        or user.id in active_ids
    ]
    return {"accounts": [{"id": u.id, "username": u.username, "nickname": u.nickname, "is_admin": int(u.is_admin or 0) >= 1, "role": "admin_teacher" if int(u.is_admin or 0) >= 2 else "teacher" if int(u.is_admin or 0) == 1 else "student"} for u in users]}


@router.patch("/accounts/{account_id}")
def update_teacher_account(account_id: int, payload: TeacherAccountInput, db: Session = Depends(get_db), admin: User = Depends(require_admin_teacher)):
    from api.companion import clear_companion_context_for_user
    target = db.query(User).filter(User.id == account_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="账号不存在")
    if int(target.is_admin or 0) >= 2:
        raise HTTPException(status_code=400, detail="管理员教师角色不能通过普通教师接口修改")
    before = int(target.is_admin or 0)
    target.is_admin = 1 if payload.is_admin else 0
    # 不允许旧会话跨越角色边界；用户须以新角色重新登录。
    clear_companion_context_for_user(target.id, db)
    db.query(UserSession).filter(UserSession.user_id == target.id).delete(synchronize_session=False)
    if not payload.is_admin:
        db.query(TeacherStudentAssignment).filter(TeacherStudentAssignment.teacher_user_id == target.id).update({"active": 0})
        db.query(StudentCaseAccessRequest).filter(
            StudentCaseAccessRequest.teacher_user_id == target.id,
            StudentCaseAccessRequest.status.in_(["pending", "approved"]),
        ).update({"status": "revoked", "expires_at": None, "review_note": "教师角色已撤销"}, synchronize_session=False)
    db.commit()
    _audit(db, admin, "update_account_role", "user", str(target.id), f"allowed_{before}_to_{target.is_admin}")
    return {"status": "updated"}


@router.post("/assignments")
def set_student_assignment(payload: StudentAssignmentInput, db: Session = Depends(get_db), admin: User = Depends(require_admin_teacher)):
    teacher = db.query(User).filter(User.id == payload.teacher_user_id, User.is_admin == 1).first()
    student = db.query(User).filter(User.id == payload.student_user_id, User.is_admin == 0).first()
    if not teacher or not student:
        raise HTTPException(status_code=404, detail="普通教师或学生不存在")
    row = db.query(TeacherStudentAssignment).filter(
        TeacherStudentAssignment.teacher_user_id == teacher.id,
        TeacherStudentAssignment.student_user_id == student.id,
    ).first()
    if row:
        row.active = int(payload.active)
    else:
        row = TeacherStudentAssignment(
            teacher_user_id=teacher.id,
            student_user_id=student.id,
            assigned_by_user_id=admin.id,
            active=int(payload.active),
        )
        db.add(row)
    if not payload.active:
        db.query(StudentCaseAccessRequest).filter(
            StudentCaseAccessRequest.teacher_user_id == teacher.id,
            StudentCaseAccessRequest.student_user_id == student.id,
            StudentCaseAccessRequest.status.in_(["pending", "approved"]),
        ).update({"status": "revoked", "expires_at": None, "review_note": "学生职责分配已撤销"}, synchronize_session=False)
    db.commit()
    _audit(db, admin, "update_teacher_student_assignment", "student", str(student.id), "allowed")
    return {"status": "active" if payload.active else "inactive"}
