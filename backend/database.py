from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

# SQLite连接（开发阶段零配置，后续可切换MySQL）
DATABASE_URL = "sqlite:///./shengyu_v2.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
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
