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
