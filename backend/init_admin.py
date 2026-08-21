"""按显式环境变量初始化本地教师账号，不提供默认弱口令。"""

from config import settings
from database import SessionLocal
from models import User, UserSession
from security import get_password_hash


def create_default_admin() -> None:
    username = settings.ADMIN_USERNAME.strip()
    password = settings.ADMIN_PASSWORD
    if not username and not password:
        print("[admin] 未配置本地教师账号，跳过初始化")
        return
    if not username or len(password) < 12:
        print("[admin] ADMIN_USERNAME/ADMIN_PASSWORD 配置不完整或密码少于12位，拒绝初始化")
        return

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == username).first()
        if admin:
            if not admin.is_admin:
                raise RuntimeError("管理员用户名已被普通账号占用，拒绝自动提权")
            admin.is_admin = 2
            admin.password_hash = get_password_hash(password)
            db.query(UserSession).filter(UserSession.user_id == admin.id).delete()
        else:
            db.add(
                User(
                    username=username,
                    password_hash=get_password_hash(password),
                    nickname="本地教师",
                    is_admin=2,
                )
            )
        db.commit()
        print("[admin] 本地教师账号已就绪")
    finally:
        db.close()
