from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=True)
    avatar = Column(String(255), nullable=True)
    # 0=学生，1=普通教师，2=管理员教师。保留字段名以兼容既有数据库。
    is_admin = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class MoodRecord(Base):
    __tablename__ = "mood_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mood_score = Column(Float, nullable=False)  # 情绪分数 0-10
    mood_label = Column(String(20), nullable=False)  # 开心/平静/焦虑/难过/愤怒
    content = Column(Text, nullable=True)  # 用户文字记录
    input_type = Column(String(10), default="text")  # text/voice
    created_at = Column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_user_date", "user_id", "created_at"),
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("student_chat_sessions.id"), nullable=True, index=True)
    role = Column(String(10), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    emotion = Column(String(20), nullable=True)  # 识别出的情绪
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_user_time", "user_id", "created_at"),
    )


class StudentChatSession(Base):
    """学生一次连续倾诉的边界；不向教师端自动开放。"""

    __tablename__ = "student_chat_sessions"

    id = Column(Integer, primary_key=True)
    session_code = Column(String(40), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    continued_from_session_id = Column(Integer, ForeignKey("student_chat_sessions.id"), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    risk_level = Column(String(16), nullable=False, default="routine")
    external_ai_consent_version = Column(String(32), nullable=True)
    summary_deleted_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_token = Column(String(64), nullable=True)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)

    __table_args__ = (Index("idx_student_session_user_status", "user_id", "status"),)


class StudentConversationSummary(Base):
    """非诊断性的倾诉后小结，最多保留30天。"""

    __tablename__ = "student_conversation_summaries"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("student_chat_sessions.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    summary_json = Column(Text, nullable=False)
    model_name = Column(String(80), nullable=False, default="deterministic-student-summary")
    prompt_version = Column(String(32), nullable=False, default="student-summary-v1")
    degraded = Column(Integer, nullable=False, default=0)
    message_count = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (Index("idx_student_summary_user_expiry", "user_id", "expires_at"),)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class CompanionSafetyState(Base):
    """跨进程保存最小派生安全状态；不保存任何聊天原文。"""

    __tablename__ = "companion_safety_states"

    id = Column(Integer, primary_key=True)
    session_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pending_flags_json = Column(Text, nullable=False, default="[]")
    urgent = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class GuardianCase(Base):
    __tablename__ = "guardian_cases"

    id = Column(Integer, primary_key=True)
    case_code = Column(String(32), nullable=False, unique=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reporter_role = Column(String(16), nullable=False)
    age_band = Column(String(16), nullable=False)
    signals_json = Column(Text, nullable=False, default="[]")
    duration = Column(String(24), nullable=False)
    functional_impact = Column(String(24), nullable=False)
    district = Column(String(24), nullable=False)
    context = Column(Text, nullable=False, default="")
    guardian_may_be_source = Column(Integer, nullable=False, default=0)
    consent_version = Column(String(32), nullable=False)
    risk_level = Column(String(16), nullable=False, default="routine", index=True)
    status = Column(String(24), nullable=False, default="queued", index=True)
    review_status = Column(String(32), nullable=False, default="needs_professional_review")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True)
    run_code = Column(String(40), nullable=False, unique=True, index=True)
    case_id = Column(Integer, ForeignKey("guardian_cases.id"), nullable=False, index=True)
    agent_type = Column(String(32), nullable=False)
    status = Column(String(24), nullable=False, default="queued")
    summary = Column(Text, nullable=False, default="")
    output_json = Column(Text, nullable=False, default="{}")
    evidence_json = Column(Text, nullable=False, default="[]")
    model_name = Column(String(80), nullable=False, default="deterministic-template")
    prompt_version = Column(String(32), nullable=False, default="guardian-v1")
    degraded = Column(Integer, nullable=False, default=0)
    error_code = Column(String(40), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (Index("idx_agent_case_type", "case_id", "agent_type"),)


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id = Column(Integer, primary_key=True)
    source_code = Column(String(24), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    issuer = Column(String(120), nullable=False)
    source_url = Column(Text, nullable=False)
    evidence_level = Column(String(32), nullable=False)
    tags_json = Column(Text, nullable=False, default="[]")
    summary = Column(Text, nullable=False)
    reviewed_at = Column(String(16), nullable=False)
    review_status = Column(String(32), nullable=False, default="source_verified")


class SupportPlan(Base):
    __tablename__ = "support_plans"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("guardian_cases.id"), nullable=False, unique=True, index=True)
    version = Column(String(32), nullable=False)
    plan_json = Column(Text, nullable=False)
    review_status = Column(String(32), nullable=False, default="needs_professional_review")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("guardian_cases.id"), nullable=False, index=True)
    day_offset = Column(Integer, nullable=False)
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(24), nullable=False, default="scheduled", index=True)
    response_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_followup_case_day", "case_id", "day_offset", unique=True),)


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("guardian_cases.id"), nullable=False, index=True)
    trigger_code = Column(String(40), nullable=False)
    action_code = Column(String(40), nullable=False)
    redacted_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class SensitiveAccessLog(Base):
    __tablename__ = "sensitive_access_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    resource_type = Column(String(40), nullable=False)
    resource_id = Column(String(64), nullable=False)
    result = Column(String(24), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class StudentCaseAccessRequest(Base):
    """教师查看学生个案原文的申请工单。"""

    __tablename__ = "student_case_access_requests"

    id = Column(Integer, primary_key=True)
    request_code = Column(String(32), nullable=False, unique=True, index=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    scope = Column(String(32), nullable=False, default="recent_30_days")
    status = Column(String(16), nullable=False, default="pending", index=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=False, default="")
    reviewed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_case_access_teacher_student", "teacher_user_id", "student_user_id", "status"),
    )


class TeacherStudentAssignment(Base):
    """普通教师可发起支持申请的学生职责范围。"""

    __tablename__ = "teacher_student_assignments"

    id = Column(Integer, primary_key=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_teacher_student_assignment", "teacher_user_id", "student_user_id", unique=True),
    )


class TeacherWorkProductSnapshot(Base):
    """绑定教师、学生、审批工单和截止时点的工作成果快照。"""

    __tablename__ = "teacher_work_product_snapshots"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(120), nullable=False, unique=True, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_id = Column(Integer, ForeignKey("student_case_access_requests.id"), nullable=True, index=True)
    generated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_cutoff = Column(DateTime, nullable=False)
    version = Column(String(32), nullable=False, default="teacher-work-product-v1")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class TeacherWorkProductTaskDecision(Base):
    __tablename__ = "teacher_work_product_task_decisions"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(120), ForeignKey("teacher_work_product_snapshots.product_id"), nullable=False, index=True)
    task_index = Column(Integer, nullable=False)
    teacher_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="confirmed")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (Index("idx_work_product_task_decision", "product_id", "task_index", "teacher_user_id", unique=True),)
