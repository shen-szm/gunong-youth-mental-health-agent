from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: Literal["development", "test", "production"] = "development"
    RELEASE_VERSION: str = "5.1.0-alpha.19"
    DATABASE_URL: str = "sqlite:///./shengyu_v5_dev.db"
    DEMO_MODE: bool = True
    SESSION_COOKIE_NAME: str = "shengyu_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7
    COOKIE_SECURE: bool = False
    AGENT_STEP_DELAY_MS: int = 180
    # 外部模型总开关；学生数据还必须通过教师端登记且未过期的授权记录。
    ALLOW_EXTERNAL_AI: bool = False
    # 学生自由倾诉包含高度敏感信息；除总开关外，必须有教师端登记且未过期的机构/监护授权依据。
    ALLOW_STUDENT_EXTERNAL_AI: bool = False
    # 守护者表单已强制合成数据确认和去标识校验，可单独启用；失败时仍显式降级。
    ALLOW_GUARDIAN_SYNTHETIC_AI: bool = True

    # 讯飞语音识别(ASR)和语音合成(TTS)配置
    XUNFEI_APP_ID: str = ""
    XUNFEI_API_KEY: str = ""
    XUNFEI_API_SECRET: str = ""

    # 星火大模型配置（HTTP API方式）
    SPARK_MODEL: str = "pro"  # pro / pro-128k / lite / max / max-32k / ultra
    SPARK_API_PASSWORD: str = ""  # 讯飞开放平台控制台获取的APIPassword

    # MySQL配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "shengyu_db"

    BACKEND_PORT: int = 9000

    # 只有显式提供强密码时才初始化本地教师账号。
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""

    # CORS配置 - 前端开发服务器地址
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def enforce_production_session_security(self):
        if self.APP_ENV == "production" and (self.DEMO_MODE or not self.COOKIE_SECURE):
            raise ValueError("production requires DEMO_MODE=false and COOKIE_SECURE=true")
        return self

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
