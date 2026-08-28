"""
咕哝Web应用 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
import models  # 确保模型被加载
from validation import sanitized_validation_exception_handler

# 导入路由
from api import chat, companion, user, mood, admin, music, guardian, teacher, island, assessment

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
        "guardian_ai": bool(settings.ALLOW_EXTERNAL_AI and settings.ALLOW_GUARDIAN_SYNTHETIC_AI),
        "spark_model": settings.SPARK_MODEL,
        "spark_configured": is_spark_available(),
        "guest_session": bool(settings.ALLOW_GUEST_SESSION),
    }

# 启动时初始化数据库和管理员账号
@app.on_event("startup")
async def startup():
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
    print("数据库初始化完成！")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.BACKEND_PORT,
        reload=True
    )
