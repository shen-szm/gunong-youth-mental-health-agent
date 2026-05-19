from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
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

    # CORS配置 - 前端开发服务器地址
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = {"env_file": ".env", "extra": "ignore"}

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
