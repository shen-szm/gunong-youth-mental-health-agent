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
        columns = {item["name"] for item in inspect(engine).get_columns("student_case_access_requests")}
        if "expires_at" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE student_case_access_requests ADD COLUMN expires_at DATETIME"))
