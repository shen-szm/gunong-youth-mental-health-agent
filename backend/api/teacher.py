"""教师工作台 API：最小画像、个案查看申请、审批与原文审计访问。"""

from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import require_admin_teacher, require_teacher
from database import get_db
from guardian_engine import _context_has_urgent_meaning
from models import ChatMessage, MoodRecord, SensitiveAccessLog, StudentCaseAccessRequest, TeacherStudentAssignment, User, UserSession


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
    return ("high" if avg < 3 else "middle" if avg < 5 else "low"), avg, len(moods)


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
    since = datetime.now() - timedelta(days=30)
    cutoff = approved.reviewed_at if approved and approved.reviewed_at else datetime.now()
    moods = db.query(MoodRecord).filter(MoodRecord.user_id == student_id, MoodRecord.created_at >= since, MoodRecord.created_at <= cutoff).order_by(MoodRecord.created_at.desc()).limit(50).all()
    chats = db.query(ChatMessage).filter(ChatMessage.user_id == student_id, ChatMessage.role == "user", ChatMessage.created_at >= since, ChatMessage.created_at <= cutoff).order_by(ChatMessage.created_at.desc()).limit(50).all()
    _audit(db, teacher, "view_student_original_content", "student", str(student_id), "allowed")
    return {
        "student_id": student_id,
        "access_basis": "admin_direct" if approved is None else "approved_request",
        "request_id": approved.id if approved else None,
        "scope": "recent_30_days",
        "content_cutoff": cutoff.isoformat(),
        "access_expires_at": approved.expires_at.isoformat() if approved and approved.expires_at else None,
        "notice": "原文仅用于该支持工单，不得传播，也不得作为诊断依据。",
        "records": [
            *[{"id": f"mood-{row.id}", "source": "情绪记录", "content": row.content or f"选择了“{row.mood_label}”", "emotion": row.mood_label, "created_at": row.created_at.isoformat() if row.created_at else None} for row in moods],
            *[{"id": f"chat-{row.id}", "source": "倾诉原文", "content": row.content, "emotion": row.emotion or "", "created_at": row.created_at.isoformat() if row.created_at else None} for row in chats],
        ],
    }


@router.get("/students/{student_id}/profile")
def student_profile(student_id: int, request_id: int | None = None, db: Session = Depends(get_db), teacher: User = Depends(require_teacher)):
    _require_student_access(db, teacher, student_id, request_id)
    risk, avg, count = _risk_for_student(db, student_id)
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
