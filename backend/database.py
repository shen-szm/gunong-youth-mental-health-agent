from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# v5 默认使用独立开发数据库，避免修改现有 v2 数据或生产备份。
DATABASE_URL = settings.DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _migrate_legacy_sensitive_access_logs(target_engine):
    """将早期教师访问日志无损转换为统一审计结构。"""
    inspector = inspect(target_engine)
    if "sensitive_access_logs" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("sensitive_access_logs")}
    required = {"actor_user_id", "action", "resource_type", "resource_id", "result", "created_at"}
    if required.issubset(columns):
        return
    legacy = {"teacher_id", "student_id", "reason", "accessed_at"}
    if not legacy.issubset(columns):
        raise RuntimeError("sensitive_access_logs schema is unsupported; refusing destructive migration")

    with target_engine.begin() as connection:
        connection.execute(text("ALTER TABLE sensitive_access_logs RENAME TO sensitive_access_logs_legacy_alpha21"))
        connection.execute(text("""
            CREATE TABLE sensitive_access_logs (
                id INTEGER NOT NULL PRIMARY KEY,
                actor_user_id INTEGER NOT NULL,
                action VARCHAR(64) NOT NULL,
                resource_type VARCHAR(40) NOT NULL,
                resource_id VARCHAR(64) NOT NULL,
                result VARCHAR(24) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(actor_user_id) REFERENCES users (id)
            )
        """))
        connection.execute(text("""
            INSERT INTO sensitive_access_logs
                (id, actor_user_id, action, resource_type, resource_id, result, created_at)
            SELECT id, teacher_id, 'legacy_teacher_access', 'student', CAST(student_id AS TEXT),
                   'legacy_imported', COALESCE(accessed_at, CURRENT_TIMESTAMP)
            FROM sensitive_access_logs_legacy_alpha21
        """))
        connection.execute(text("CREATE INDEX ix_sensitive_access_logs_actor_user_id ON sensitive_access_logs (actor_user_id)"))
        connection.execute(text("DROP TABLE sensitive_access_logs_legacy_alpha21"))


def _migrate_student_support_runs(target_engine):
    """Forward-only compatibility for alpha.23 databases created during review iterations."""
    inspector = inspect(target_engine)
    if "student_support_runs" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("student_support_runs")}
    additions = {
        "request_fingerprint": "VARCHAR(64) NOT NULL DEFAULT ''",
        "input_message_id": "INTEGER",
        "output_message_id": "INTEGER",
        "context_message_count": "INTEGER NOT NULL DEFAULT 0",
        "emotion_basis_json": "TEXT NOT NULL DEFAULT '[]'",
        "expires_at": "DATETIME",
    }
    with target_engine.begin() as connection:
        for column_name, column_type in additions.items():
            if column_name not in columns:
                connection.execute(text(f"ALTER TABLE student_support_runs ADD COLUMN {column_name} {column_type}"))
        connection.execute(text(
            "UPDATE student_support_runs SET expires_at = datetime(COALESCE(started_at, CURRENT_TIMESTAMP), '+30 days') "
            "WHERE expires_at IS NULL"
        ))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_student_support_runs_input_message_id ON student_support_runs (input_message_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_student_support_runs_expires_at ON student_support_runs (expires_at)"))


def _migrate_assessment_created_at_to_china_time(target_engine):
    """将旧版 SQLite CURRENT_TIMESTAMP 生成的 UTC 自评时间一次性转为北京时间。"""
    inspector = inspect(target_engine)
    if "student_wellbeing_assessments" not in inspector.get_table_names():
        return
    migration_key = "alpha29_assessment_created_at_china_time"
    with target_engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS app_data_migrations (
                migration_key VARCHAR(120) NOT NULL PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        applied = connection.execute(
            text("SELECT 1 FROM app_data_migrations WHERE migration_key = :key"),
            {"key": migration_key},
        ).first()
        if applied:
            return
        connection.execute(text("""
            UPDATE student_wellbeing_assessments
            SET created_at = datetime(created_at, '+8 hours')
            WHERE created_at IS NOT NULL
        """))
        connection.execute(
            text("INSERT INTO app_data_migrations (migration_key) VALUES (:key)"),
            {"key": migration_key},
        )

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
        _migrate_legacy_sensitive_access_logs(engine)
        _migrate_student_support_runs(engine)
        _migrate_assessment_created_at_to_china_time(engine)
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
            "companion_state_json": "TEXT",
            "summary_deleted_at": "DATETIME",
            "processing_started_at": "DATETIME",
            "processing_token": "VARCHAR(64)",
        }
        for column_name, column_type in session_additions.items():
            if column_name not in session_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE student_chat_sessions ADD COLUMN {column_name} {column_type}"))
        screening_columns = {item["name"] for item in inspector.get_columns("student_screening_runs")}
        if "acknowledged_at" not in screening_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE student_screening_runs ADD COLUMN acknowledged_at DATETIME"))
        if "teacher_review_reports" in inspector.get_table_names():
            report_columns = {item["name"] for item in inspector.get_columns("teacher_review_reports")}
            report_additions = {
                "content_hash": "VARCHAR(64) NOT NULL DEFAULT ''",
                "scope_key": "VARCHAR(64) NOT NULL DEFAULT 'direct'",
                "revision_number": "INTEGER NOT NULL DEFAULT 1",
                "parent_report_id": "VARCHAR(120)",
            }
            for column_name, column_type in report_additions.items():
                if column_name not in report_columns:
                    with engine.begin() as connection:
                        connection.execute(text(f"ALTER TABLE teacher_review_reports ADD COLUMN {column_name} {column_type}"))
            with engine.begin() as connection:
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_review_revision ON teacher_review_reports (source_product_id, generated_by_user_id, scope_key, version, revision_number)"))
