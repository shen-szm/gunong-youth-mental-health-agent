"""教师工作台 API：最小画像、个案查看申请、审批与原文审计访问。"""

from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import require_admin_teacher, require_teacher
from database import get_db
from guardian_engine import _context_has_urgent_meaning
from models import ChatMessage, MoodRecord, SensitiveAccessLog, StudentCaseAccessRequest, TeacherStudentAssignment, TeacherWorkProductSnapshot, TeacherWorkProductTaskDecision, User, UserSession


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


def _audit(db: Session, actor: User, action: str, resource_type: str, resource_id: str, result: str) -> None:
    db.add(SensitiveAccessLog(
        actor_user_id=actor.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
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
            StudentCaseAccessRequest.expires_at > datetime.now(),
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
        StudentCaseAccessRequest.expires_at > datetime.now(),
    )
    if request_id is not None:
        query = query.filter(StudentCaseAccessRequest.id == request_id)
    approved = query.order_by(StudentCaseAccessRequest.reviewed_at.desc()).first()
    if not approved:
        _audit(db, teacher, "view_student_case", "student", str(student_id), "denied")
        raise HTTPException(status_code=403, detail="该学生个案尚未获管理员教师审批")
    return approved


def _student_access_state(db: Session, teacher: User, student_id: int) -> dict:
    if _is_admin_teacher(teacher):
        return {"status": "direct", "request_id": None, "label": "管理员教师可直接查看"}
    row = (
        db.query(StudentCaseAccessRequest)
        .filter(
            StudentCaseAccessRequest.teacher_user_id == teacher.id,
            StudentCaseAccessRequest.student_user_id == student_id,
        )
        .order_by(StudentCaseAccessRequest.created_at.desc())
        .first()
    )
    if not row:
        return {"status": "not_requested", "request_id": None, "label": "需要提交查看申请"}
    if row.status == "approved" and (not row.expires_at or row.expires_at <= datetime.now()):
        return {"status": "expired", "request_id": row.id, "label": "授权已到期，需重新申请"}
    labels = {"pending": "等待管理员教师审批", "approved": "已获批，可查看", "rejected": "申请未通过", "revoked": "授权已撤销，需重新申请"}
    return {"status": row.status, "request_id": row.id, "label": labels.get(row.status, row.status)}


def _has_urgent_signal(db: Session, student_id: int, since: datetime | None = None) -> bool:
    since = since or datetime.now() - timedelta(days=30)
    mood_texts = db.query(MoodRecord.content).filter(MoodRecord.user_id == student_id, MoodRecord.created_at >= since).all()
    chat_texts = db.query(ChatMessage.content).filter(
        ChatMessage.user_id == student_id,
        ChatMessage.role == "user",
        ChatMessage.created_at >= since,
    ).all()
    return any(_context_has_urgent_meaning(text or "") for (text,) in [*mood_texts, *chat_texts])


def _risk_for_student(db: Session, student_id: int) -> tuple[str, float, int]:
    since = datetime.now() - timedelta(days=30)
    moods = db.query(MoodRecord).filter(MoodRecord.user_id == student_id, MoodRecord.created_at >= since).all()
    if _has_urgent_signal(db, student_id, since):
        avg = round(sum(item.mood_score for item in moods) / len(moods), 1) if moods else 0.0
        return "high", avg, len(moods)
    if not moods:
        return "low", 0.0, 0
    avg = round(sum(item.mood_score for item in moods) / len(moods), 1)
    negative_count = sum(item.mood_label in {"难过", "焦虑", "愤怒"} for item in moods)
    return ("high" if negative_count >= 4 else "middle" if negative_count >= 1 else "low"), avg, len(moods)


@router.get("/class-overview")
def class_overview(db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    student_query = db.query(User).filter(User.is_admin == 0)
    if not _is_admin_teacher(teacher):
        assigned_ids = db.query(TeacherStudentAssignment.student_user_id).filter(
            TeacherStudentAssignment.teacher_user_id == teacher.id,
            TeacherStudentAssignment.active == 1,
        )
        student_query = student_query.filter(User.id.in_(assigned_ids))
    students = [
        item for item in student_query.all()
        if not (
            item.username.startswith("demo_")
            and item.username != "demo_student_case"
            and db.query(MoodRecord).filter(MoodRecord.user_id == item.id).count() == 0
            and db.query(ChatMessage).filter(ChatMessage.user_id == item.id, ChatMessage.role == "user").count() == 0
        )
    ]
    risks = [_risk_for_student(db, item.id)[0] for item in students]
    pending = db.query(StudentCaseAccessRequest).filter(StudentCaseAccessRequest.status == "pending").count()
    return {
        "total_students": len(students),
        "today_active": 0,
        "pending_warnings": sum(level in {"high", "middle"} for level in risks),
        "pending_access_requests": pending if _is_admin_teacher(teacher) else 0,
        "week_avg_score": 0,
        "week_change": 0,
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
    for student in student_query.order_by(User.id).all():
        risk, avg, count = _risk_for_student(db, student.id)
        chat_count = db.query(ChatMessage).filter(ChatMessage.user_id == student.id, ChatMessage.role == "user").count()
        if student.username.startswith("demo_") and student.username != "demo_student_case" and count + chat_count == 0:
            continue
        items.append({
            "id": student.id,
            "nickname": student.nickname or f"学生{student.id}",
            "risk_level": risk,
            "avg_mood_score": avg,
            "mood_count": count,
            "access": _student_access_state(db, teacher, student.id),
        })
    return {"students": items}


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
    for student in student_query.all():
        risk, _, count = _risk_for_student(db, student.id)
        if risk in {"high", "middle"}:
            urgent = _has_urgent_signal(db, student.id)
            rows.append({
                "id": student.id,
                "student_id": student.id,
                "student_name": student.nickname or f"学生{student.id}",
                "risk_level": risk,
                "reason": "检测到需要立即核实安全的危机表达" if urgent else f"近30天自愿情绪记录呈{('明显' if risk == 'high' else '一定')}波动（{count}条）",
                "urgent": urgent,
                "access": _student_access_state(db, teacher, student.id),
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
        request_code=f"ACCESS-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}",
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
        row.reviewed_at = datetime.now()
        db.commit()
        _audit(db, reviewer, "revoke_stale_case_access_request", "access_request", str(row.id), "allowed")
        raise HTTPException(status_code=409, detail="申请人的教师角色或学生职责范围已失效")
    row.status = payload.decision
    row.review_note = payload.note.strip()
    row.reviewer_user_id = reviewer.id
    row.reviewed_at = datetime.now()
    row.expires_at = datetime.now() + timedelta(days=7) if payload.decision == "approved" else None
    db.commit()
    _audit(db, reviewer, f"{payload.decision}_case_access_request", "access_request", str(row.id), "allowed")
    return {"status": row.status, "idempotent": False}


@router.get("/students/{student_id}/case-context")
def student_case_context(student_id: int, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    approved = _require_student_access(db, teacher, student_id, request_id)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else datetime.now()
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


@router.get("/students/{student_id}/work-product")
def student_work_product(student_id: int, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    """在同一授权边界内，把原始记录整理成教师可审核的工作成果。"""
    approved = _require_student_access(db, teacher, student_id, request_id)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else datetime.now()
    redacted_safety_revision: dict | None = None
    if approved is None:
        day_start = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        existing_direct_snapshot = db.query(TeacherWorkProductSnapshot).filter(
            TeacherWorkProductSnapshot.student_user_id == student_id,
            TeacherWorkProductSnapshot.request_id.is_(None),
            TeacherWorkProductSnapshot.generated_by_user_id == teacher.id,
            TeacherWorkProductSnapshot.created_at >= day_start,
        ).order_by(TeacherWorkProductSnapshot.created_at.desc()).first()
        if existing_direct_snapshot:
            incremental_cutoff = datetime.now()
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
            has_new_urgent_signal = any(_context_has_urgent_meaning(item.content or "") for item in [*new_moods, *new_chats])
            cutoff = incremental_cutoff if has_new_urgent_signal else existing_direct_snapshot.content_cutoff
    elif approved is not None:
        safety_check_at = datetime.now()
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
        urgent_after_approval = [item for item in [*post_approval_moods, *post_approval_chats] if _context_has_urgent_meaning(item.content or "")]
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
    urgent_records = [
        *[{"id": f"mood-{row.id}", "source": "情绪记录", "content": row.content or f"选择了“{row.mood_label}”", "emotion": row.mood_label, "created_at": row.created_at.isoformat() if row.created_at else None} for row in all_moods if _context_has_urgent_meaning(row.content or "")],
        *[{"id": f"chat-{row.id}", "source": "倾诉原文", "content": row.content, "emotion": row.emotion or "", "created_at": row.created_at.isoformat() if row.created_at else None} for row in all_chats if _context_has_urgent_meaning(row.content or "")],
    ]
    known_ids = {item["id"] for item in records}
    records.extend(item for item in urgent_records if item["id"] not in known_ids)
    records.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    trigger_evidence_ids = [redacted_safety_revision["id"]] if redacted_safety_revision else []
    trigger_evidence_ids.extend(item["id"] for item in records if _context_has_urgent_meaning(str(item.get("content") or "")))
    trigger_evidence_ids = list(dict.fromkeys(trigger_evidence_ids))
    urgent = bool(trigger_evidence_ids)
    mood_records = [item for item in records if item["source"] == "情绪记录"]
    chat_records = [item for item in records if item["source"] == "倾诉原文"]
    evidence_ids = list(dict.fromkeys([*trigger_evidence_ids, *[item["id"] for item in records[:8]]]))
    negative_count = sum(item.mood_label in {"难过", "焦虑", "愤怒"} for item in all_moods)
    baseline_risk = "high" if negative_count >= 4 else "middle" if negative_count >= 1 else "low"
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
            version="teacher-work-product-v1",
        ))
        db.commit()
    task_decisions = db.query(TeacherWorkProductTaskDecision).filter(
        TeacherWorkProductTaskDecision.product_id == product_id,
        TeacherWorkProductTaskDecision.teacher_user_id == teacher.id,
        TeacherWorkProductTaskDecision.status == "confirmed",
    ).all()
    _audit(db, teacher, "generate_teacher_work_product", "work_product", product_id, "allowed")
    return {
        "case_id": product_id,
        "version": "teacher-work-product-v1",
        "generated_at": datetime.now().isoformat(),
        "risk": risk,
        "access_basis": context["access_basis"],
        "request_id": context.get("request_id"),
        "data_from": (datetime.fromisoformat(context["content_cutoff"]) - timedelta(days=30)).isoformat(),
        "content_cutoff": context["content_cutoff"],
        "records": records,
        "pipeline": [
            {"name": "安全分流", "status": "completed", "result": "发现明确紧急信号" if urgent else "未发现明确紧急信号"},
            {"name": "记录归纳", "status": "completed", "result": f"纳入{len(chat_records)}条倾诉、{len(mood_records)}条情绪记录"},
            {"name": "证据定位", "status": "completed", "result": f"{len(evidence_ids)}条结论可回到原文"},
            {"name": "支持草案", "status": "completed", "result": "已生成，等待教师确认"},
        ],
        "observation": {
            "headline": "当前需要优先确认安全" if urgent else ("近期有值得持续关注的自愿表达" if records else "当前记录不足，建议先沟通补充"),
            "latest_signal": latest["content"][:120] if latest else "暂无可引用记录",
            "record_count": len(records),
            "evidence_ids": evidence_ids,
            "trigger_evidence_ids": trigger_evidence_ids,
        },
        "conflicts": [{"topic": "行动强度", "views": ["尽快介入", "先保持低压力接触"], "resolution": "安全规则优先" if urgent else "由教师结合线下观察确认", "evidence_ids": evidence_ids}],
        "decision": decision,
        "decision_evidence_ids": trigger_evidence_ids or evidence_ids,
        "tasks": [{**task, "evidence_ids": trigger_evidence_ids or evidence_ids} for task in next_tasks],
        "confirmed_task_indices": sorted(item.task_index for item in task_decisions),
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


@router.get("/students/{student_id}/profile")
def student_profile(student_id: int, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    approved = _require_student_access(db, teacher, student_id, request_id)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else datetime.now()
    since = cutoff - timedelta(days=30)
    moods = db.query(MoodRecord).filter(
        MoodRecord.user_id == student_id,
        MoodRecord.created_at >= since,
        MoodRecord.created_at <= cutoff,
    ).all()
    avg = round(sum(item.mood_score for item in moods) / len(moods), 1) if moods else 0.0
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
    risk = "high" if urgent or negative_count >= 4 else "middle" if negative_count >= 1 else "low"
    count = len(moods)
    return {"avg_score": avg, "risk_level": risk, "mood_count": count, "summary": "经授权读取的近30天支持摘要，不构成诊断。", "keywords": []}


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
    users = db.query(User).order_by(User.id).all()
    return {"accounts": [{"id": u.id, "username": u.username, "nickname": u.nickname, "is_admin": int(u.is_admin or 0) >= 1, "role": "admin_teacher" if int(u.is_admin or 0) >= 2 else "teacher" if int(u.is_admin or 0) == 1 else "student"} for u in users]}


@router.patch("/accounts/{account_id}")
def update_teacher_account(account_id: int, payload: TeacherAccountInput, db: Session = Depends(get_db), admin: User = Depends(require_admin_teacher)):
    target = db.query(User).filter(User.id == account_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="账号不存在")
    if int(target.is_admin or 0) >= 2:
        raise HTTPException(status_code=400, detail="管理员教师角色不能通过普通教师接口修改")
    before = int(target.is_admin or 0)
    target.is_admin = 1 if payload.is_admin else 0
    # 不允许旧会话跨越角色边界；用户须以新角色重新登录。
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
