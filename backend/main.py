"""
咕哝Web应用 - FastAPI 主入口
"""
import asyncio
import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
import models  # 确保模型被加载
from validation import sanitized_validation_exception_handler

# 导入路由
from api import chat, companion, user, mood, admin, music, guardian, teacher, island, assessment, screening, student_agent, teacher_tasks

app = FastAPI(title="咕哝 API", description="AI心理健康教育与守护者支持工具", version=settings.RELEASE_VERSION)
app.add_exception_handler(RequestValidationError, sanitized_validation_exception_handler)

# CORS配置（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(companion.router)
app.include_router(user.router)
app.include_router(mood.router)
app.include_router(admin.router)
app.include_router(music.router)
app.include_router(guardian.router)
app.include_router(teacher.router)
app.include_router(island.router)
app.include_router(assessment.router)
app.include_router(screening.router)
app.include_router(student_agent.router)
app.include_router(teacher_tasks.router)
support_cleanup_task = None
logger = logging.getLogger(__name__)


async def periodic_support_cleanup():
    """Enforce retention even when a student never returns."""
    from database import SessionLocal
    while True:
        try:
            db = SessionLocal()
            try:
                student_agent.cleanup_expired_support_runs(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("student support retention cleanup failed; will retry on next interval")
        await asyncio.sleep(6 * 60 * 60)

@app.get("/")
async def root():
    return {"msg": "咕哝API运行中", "version": settings.RELEASE_VERSION, "docs": "/docs"}

@app.get("/health")
async def health():
    from xunfei.spark_api import is_spark_available
    return {
        "status": "ok",
        "version": settings.RELEASE_VERSION,
        "external_ai": bool(settings.ALLOW_EXTERNAL_AI),
        "student_ai": bool(settings.ALLOW_EXTERNAL_AI and settings.ALLOW_STUDENT_EXTERNAL_AI),
        "student_ai_access_mode": settings.STUDENT_AI_ACCESS_MODE,
        "student_ai_governance_ack": bool(settings.PLATFORM_STUDENT_AI_GOVERNANCE_ACK),
        "guardian_ai": bool(settings.ALLOW_EXTERNAL_AI and settings.ALLOW_GUARDIAN_SYNTHETIC_AI),
        "spark_model": settings.SPARK_MODEL,
        "spark_configured": is_spark_available(),
        "guest_session": bool(settings.ALLOW_GUEST_SESSION),
    }

# 启动时初始化数据库和管理员账号
@app.on_event("startup")
async def startup():
    global support_cleanup_task
    print("正在初始化数据库...")
    init_db()
    from database import SessionLocal
    from guardian_engine import seed_evidence_sources
    db = SessionLocal()
    try:
        seed_evidence_sources(db)
    finally:
        db.close()
    from init_admin import create_default_admin
    create_default_admin()
    support_cleanup_task = asyncio.create_task(periodic_support_cleanup())
    print("数据库初始化完成！")


@app.on_event("shutdown")
async def shutdown():
    global support_cleanup_task
    if support_cleanup_task:
        support_cleanup_task.cancel()
        try:
            await support_cleanup_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.BACKEND_PORT,
        reload=True
    )
