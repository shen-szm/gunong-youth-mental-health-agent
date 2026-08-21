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
    is_admin = Column(Integer, default=0, nullable=False)  # 0=普通用户, 1=管理员
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
    role = Column(String(10), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    emotion = Column(String(20), nullable=True)  # 识别出的情绪
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_user_time", "user_id", "created_at"),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


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
