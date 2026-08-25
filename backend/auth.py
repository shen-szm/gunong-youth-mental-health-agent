"""基于 HttpOnly Cookie 的本地会话认证。"""

from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, UserSession


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def establish_session(response: Response, db: Session, user: User) -> None:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    db.add(UserSession(user_id=user.id, token_hash=_token_hash(token), expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_session(response: Response, request: Request, db: Session) -> None:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        from api.companion import clear_companion_context_for_token
        clear_companion_context_for_token(token, db)
        db.query(UserSession).filter(UserSession.token_hash == _token_hash(token)).delete()
        db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="会话已失效，请重新进入")
    session = db.query(UserSession).filter(UserSession.token_hash == _token_hash(token)).first()
    if not session or session.expires_at <= datetime.utcnow():
        if session:
            from api.companion import clear_companion_context_for_token
            clear_companion_context_for_token(token, db)
            db.delete(session)
            db.commit()
        raise HTTPException(status_code=401, detail="会话已失效，请重新进入")
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="账号不存在")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要教师权限")
    return current_user


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    if int(current_user.is_admin or 0) < 1:
        raise HTTPException(status_code=403, detail="需要教师权限")
    return current_user


def require_admin_teacher(current_user: User = Depends(get_current_user)) -> User:
    if int(current_user.is_admin or 0) < 2:
        raise HTTPException(status_code=403, detail="需要管理员教师权限")
    return current_user


def ensure_user_scope(requested_user_id: int, current_user: User) -> None:
    # 学生端旧接口始终仅限本人。教师跨用户读取必须走带审批/审计的教师工作台接口。
    if requested_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该用户数据")
