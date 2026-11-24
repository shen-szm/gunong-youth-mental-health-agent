from sqlalchemy import CheckConstraint, Column, Integer, String, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=True)
    real_name = Column(String(50), nullable=True)
    class_name = Column(String(50), nullable=True)
    student_no = Column(String(40), nullable=True, index=True)
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
    companion_state_json = Column(Text, nullable=True)
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


class StudentCompanionMemory(Base):
    """小满跨会话记住的一件小事；学生可随时查看和删除，最多保留180天。"""

    __tablename__ = "student_companion_memories"

    id = Column(Integer, primary_key=True)
    memory_code = Column(String(40), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String(120), nullable=False)
    category = Column(String(16), nullable=False, default="其他")
    dedupe_key = Column(String(64), nullable=False)
    consent_version = Column(String(32), nullable=False)
    source_session_id = Column(Integer, ForeignKey("student_chat_sessions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_student_memory_user_dedupe", "user_id", "dedupe_key", unique=True),
        Index("idx_student_memory_user_updated", "user_id", "updated_at"),
        Index("idx_student_memory_user_expiry", "user_id", "expires_at"),
    )


class StudentWellbeingAssessment(Base):
    """学生主动完成的结构化心理状态评估；结果不是医学诊断。"""

    __tablename__ = "student_wellbeing_assessments"

    id = Column(Integer, primary_key=True)
    assessment_code = Column(String(40), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period = Column(String(16), nullable=False, default="past_14_days")
    answers_json = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)
    risk_level = Column(String(16), nullable=False, default="routine", index=True)
    review_status = Column(String(32), nullable=False, default="student_self_review")
    external_ai_consent_version = Column(String(32), nullable=True)
    model_name = Column(String(80), nullable=False, default="deterministic-assessment")
    prompt_version = Column(String(32), nullable=False, default="wellbeing-assessment-v1")
    degraded = Column(Integer, nullable=False, default=0)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (Index("idx_wellbeing_user_expiry", "user_id", "expires_at"),)


class StudentAssessmentAgentRun(Base):
    """一次评估中每个 Agent 的可核验运行结果，不保存思维链。"""

    __tablename__ = "student_assessment_agent_runs"

    id = Column(Integer, primary_key=True)
    run_code = Column(String(48), nullable=False, unique=True, index=True)
    assessment_id = Column(Integer, ForeignKey("student_wellbeing_assessments.id"), nullable=False, index=True)
    agent_type = Column(String(32), nullable=False)
    status = Column(String(24), nullable=False, default="completed")
    summary = Column(Text, nullable=False)
    output_json = Column(Text, nullable=False, default="{}")
    evidence_json = Column(Text, nullable=False, default="[]")
    model_name = Column(String(80), nullable=False, default="deterministic-assessment")
    prompt_version = Column(String(32), nullable=False, default="wellbeing-assessment-v1")
    degraded = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_assessment_agent_run", "assessment_id", "agent_type"),)


class StudentScreeningRun(Base):
    """学生主动完成的标准筛查；答案只在服务端保存，教师只看分级与总分。"""

    __tablename__ = "student_screening_runs"

    id = Column(Integer, primary_key=True)
    run_code = Column(String(48), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    instrument = Column(String(16), nullable=False, default="phq9")
    instrument_version = Column(String(32), nullable=False, default="phq-9-cn-v1")
    answers_json = Column(Text, nullable=False)
    total_score = Column(Integer, nullable=False)
    band = Column(String(24), nullable=False)
    risk_level = Column(String(16), nullable=False, default="routine", index=True)
    item9_positive = Column(Integer, nullable=False, default=0)
    safety_flag_active = Column(Integer, nullable=False, default=0)
    acknowledged_at = Column(DateTime, nullable=True)
    linked_session_id = Column(Integer, ForeignKey("student_chat_sessions.id"), nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_student_screening_user_created", "user_id", "created_at"),
        Index("idx_student_screening_user_expiry", "user_id", "expires_at"),
    )


class StudentSupportRun(Base):
    """学生端统一智能体任务；只保存结构化派生结果，不保存新的聊天原文副本。"""

    __tablename__ = "student_support_runs"

    id = Column(Integer, primary_key=True)
    run_code = Column(String(48), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("student_chat_sessions.id"), nullable=True, index=True)
    task_type = Column(String(32), nullable=False, default="chat_turn", index=True)
    trigger_source = Column(String(32), nullable=False, default="student_chat")
    idempotency_key = Column(String(80), nullable=False, unique=True, index=True)
    request_fingerprint = Column(String(64), nullable=False, default="")
    input_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True, index=True)
    output_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    status = Column(String(24), nullable=False, default="running", index=True)
    risk_level = Column(String(16), nullable=False, default="routine", index=True)
    intent_summary = Column(String(160), nullable=False, default="")
    context_message_count = Column(Integer, nullable=False, default=0)
    plan_json = Column(Text, nullable=False, default="[]")
    tools_json = Column(Text, nullable=False, default="[]")
    deliverable_json = Column(Text, nullable=False, default="{}")
    emotion_basis_json = Column(Text, nullable=False, default="[]")
    model_name = Column(String(80), nullable=False, default="pending")
    prompt_version = Column(String(40), nullable=False, default="student-support-orchestrator-v1")
    degraded = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (Index("idx_student_support_user_time", "user_id", "started_at"),)


class StudentSupportEvent(Base):
    """可公开核验的任务事件；summary 是结果摘要而不是模型思维链。"""

    __tablename__ = "student_support_events"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("student_support_runs.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    agent_type = Column(String(40), nullable=False)
    tool_name = Column(String(48), nullable=True)
    status = Column(String(24), nullable=False)
    summary = Column(String(200), nullable=False)
    source = Column(String(32), nullable=False, default="deterministic")
    evidence_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_student_support_event_order", "run_id", "sequence", unique=True),)


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


class StudentExternalAiAuthorization(Base):
    """由职责教师登记的学生外部 AI 处理授权依据；不保存证明材料原文。"""

    __tablename__ = "student_external_ai_authorizations"

    id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    authorized_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    basis = Column(String(40), nullable=False, default="school_guardian_authority")
    statement_version = Column(String(40), nullable=False, default="teacher-ai-authorization-v4")
    purpose = Column(String(120), nullable=False, default="student_support_agents")
    status = Column(String(16), nullable=False, default="active", index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


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


class TeacherReviewReport(Base):
    """教师在授权工单范围内生成并人工签署的最终评审报告。"""

    __tablename__ = "teacher_review_reports"

    id = Column(Integer, primary_key=True)
    report_id = Column(String(120), nullable=False, unique=True, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_id = Column(Integer, ForeignKey("student_case_access_requests.id"), nullable=True, index=True)
    source_product_id = Column(String(120), ForeignKey("teacher_work_product_snapshots.product_id"), nullable=False, index=True)
    generated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    report_json = Column(Text, nullable=False, default="{}")
    content_hash = Column(String(64), nullable=False, default="")
    scope_key = Column(String(64), nullable=False, default="direct")
    revision_number = Column(Integer, nullable=False, default=1)
    parent_report_id = Column(String(120), nullable=True)
    status = Column(String(24), nullable=False, default="draft", index=True)
    review_note = Column(Text, nullable=False, default="")
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    version = Column(String(40), nullable=False, default="teacher-review-report-v2")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_teacher_review_student_time", "student_user_id", "created_at"),
        Index("idx_teacher_review_revision", "source_product_id", "generated_by_user_id", "scope_key", "version", "revision_number", unique=True),
        CheckConstraint("status IN ('draft', 'reviewed', 'revision_requested')", name="ck_teacher_review_status"),
    )


class TeacherReviewReportDecision(Base):
    """评审状态的追加式审计记录；不覆盖历史决定。"""

    __tablename__ = "teacher_review_report_decisions"

    id = Column(Integer, primary_key=True)
    report_id = Column(String(120), ForeignKey("teacher_review_reports.report_id"), nullable=False, index=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    previous_status = Column(String(24), nullable=False)
    decision = Column(String(24), nullable=False)
    checklist_confirmed = Column(Integer, nullable=False, default=0)
    note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ── 心岛守护者多智能体系统 ────────────────────────────────

class IslandCommand(Base):
    """
    心岛指令表：Agent 通过此表下发环境控制指令，前端轮询或 WebSocket 接收并执行。
    这是 Agent "调用工具改变游戏环境" 的核心机制。
    """
    __tablename__ = "island_commands"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    command_type = Column(String(32), nullable=False)  # set_phase/set_weather/pet_action/toast/recommend
    payload_json = Column(Text, nullable=False, default="{}")
    reason = Column(String(200), nullable=False, default="")
    status = Column(String(16), nullable=False, default="pending", index=True)  # pending/acknowledged/expired
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    __table_args__ = (Index("idx_island_cmd_user_status", "user_id", "status"),)


class GameBehaviorLog(Base):
    """游戏行为日志：感知 Agent 的数据来源。"""
    __tablename__ = "game_behavior_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # place_enter/activity_start/activity_finish/reflection/pet_interaction/login
    place = Column(String(32), nullable=True)
    activity = Column(String(32), nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    __table_args__ = (Index("idx_behavior_user_time", "user_id", "created_at"),)


class IslandAgentRun(Base):
    """心岛 Agent 运行记录：可审计的多 Agent 执行轨迹。"""
    __tablename__ = "island_agent_runs"

    id = Column(Integer, primary_key=True)
    run_code = Column(String(40), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trigger = Column(String(32), nullable=False, default="login")  # login/activity_end/manual/scheduled
    perception_result = Column(Text, nullable=False, default="{}")
    plan_result = Column(Text, nullable=False, default="{}")
    companion_result = Column(Text, nullable=False, default="{}")
    safety_status = Column(String(16), nullable=False, default="routine")  # routine/watch/urgent
    commands_issued = Column(Integer, nullable=False, default=0)
    model_used = Column(String(80), nullable=False, default="deterministic")
    degraded = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class PetState(Base):
    """咕团状态：陪伴 Agent 管理的宠物持久化状态。"""
    __tablename__ = "pet_states"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    intimacy = Column(Integer, nullable=False, default=0)  # 亲密度 0-1000
    mood = Column(String(16), nullable=False, default="content")  # content/happy/curious/sleepy/concerned
    today_fed = Column(Integer, nullable=False, default=0)
    today_groomed = Column(Integer, nullable=False, default=0)
    consecutive_days = Column(Integer, nullable=False, default=0)  # 连续互动天数
    last_interaction = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class IslandReport(Base):
    """心岛情绪报告：报告 Agent 交付的可验收成果。"""
    __tablename__ = "island_reports"

    id = Column(Integer, primary_key=True)
    report_code = Column(String(40), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period_days = Column(Integer, nullable=False, default=7)
    report_json = Column(Text, nullable=False, default="{}")
    pdf_path = Column(String(255), nullable=True)
    model_name = Column(String(80), nullable=False, default="deterministic")
    degraded = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    __table_args__ = (Index("idx_island_report_user_time", "user_id", "generated_at"),)
