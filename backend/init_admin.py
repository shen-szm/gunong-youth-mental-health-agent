"""
管理员账号初始化脚本
启动时自动创建默认管理员账号
"""
from database import SessionLocal, init_db
from models import User
from security import get_password_hash
from config import settings

def create_default_admin():
    """创建默认管理员账号（如果不存在）"""
    db = SessionLocal()
    try:
        # 检查是否已有管理员
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                nickname="系统管理员",
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            print("[admin] 默认管理员账号已创建：admin / admin123")
        else:
            # 确保已有admin账号有is_admin标志
            if not admin.is_admin:
                admin.is_admin = True
                db.commit()
            print("[admin] 管理员账号已存在")
    except Exception as e:
        print(f"[admin] 创建管理员账号失败：{e}")
    finally:
        db.close()
