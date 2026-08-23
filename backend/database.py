from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# v5 默认使用独立开发数据库，避免修改现有 v2 数据或生产备份。
DATABASE_URL = settings.DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    # alpha 本地库轻量前向迁移；只新增列，不触碰既有数据或生产备份。
    if DATABASE_URL.startswith("sqlite"):
        inspector = inspect(engine)
        columns = {item["name"] for item in inspector.get_columns("student_case_access_requests")}
        if "expires_at" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE student_case_access_requests ADD COLUMN expires_at DATETIME"))
        chat_columns = {item["name"] for item in inspector.get_columns("chat_messages")}
        if "session_id" not in chat_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE chat_messages ADD COLUMN session_id INTEGER"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id)"))
        session_columns = {item["name"] for item in inspector.get_columns("student_chat_sessions")}
        session_additions = {
            "continued_from_session_id": "INTEGER",
            "external_ai_consent_version": "VARCHAR(32)",
            "summary_deleted_at": "DATETIME",
            "processing_started_at": "DATETIME",
            "processing_token": "VARCHAR(64)",
        }
        for column_name, column_type in session_additions.items():
            if column_name not in session_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE student_chat_sessions ADD COLUMN {column_name} {column_type}"))
