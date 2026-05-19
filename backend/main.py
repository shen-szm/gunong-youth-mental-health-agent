"""
咕哝Web应用 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
import models  # 确保模型被加载

# 导入路由
from api import chat, user, mood, admin

app = FastAPI(title="咕哝 API", description="AI情绪健康助手", version="1.0.0")

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
app.include_router(user.router)
app.include_router(mood.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"msg": "咕哝API运行中", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# 启动时初始化数据库和管理员账号
@app.on_event("startup")
async def startup():
    print("正在初始化数据库...")
    init_db()
    from init_admin import create_default_admin
    create_default_admin()
    print("数据库初始化完成！")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=True
    )
