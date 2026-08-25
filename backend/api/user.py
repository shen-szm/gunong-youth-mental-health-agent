"""用户与本地演示会话 API。"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from auth import clear_session, establish_session, get_current_user, require_admin_teacher
from config import settings
from database import get_db
from models import User, UserSession
from security import get_password_hash, verify_password

router = APIRouter(prefix="/api/user", tags=["user"])


class RegisterReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)
    nickname: str = Field(default="", max_length=50)


class LoginReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class ChangePwdReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int | None = None
    old_password: str
    new_password1: str = Field(min_length=10, max_length=128)
    new_password2: str = Field(min_length=10, max_length=128)


class AdminResetPasswordReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_password: str = Field(min_length=10, max_length=128)


class UserResp(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str = ""
    avatar: str = ""


def _payload(user: User) -> dict:
    level = int(user.is_admin or 0)
    return {
        "user_id": user.id,
        "nickname": user.nickname or user.username,
        "is_admin": level >= 1,
        "is_super_admin": level >= 2,
        "role": "admin_teacher" if level >= 2 else "teacher" if level == 1 else "student",
    }


def _get_demo_user(db: Session) -> User:
    """获取固定合成演示用户，不授予教师权限。"""
    user = db.query(User).filter(User.username == "demo_guest").first()
    if not user:
        user = User(
            username="demo_guest",
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            nickname="演示访客",
            is_admin=0,
        )
        db.add(user)
    else:
        user.nickname = "演示访客"
        user.is_admin = 0
    db.commit()
    db.refresh(user)
    return user


def _create_isolated_demo_user(db: Session) -> User:
    username = f"demo_{secrets.token_hex(8)}"
    user = User(
        username=username,
        password_hash=get_password_hash(secrets.token_urlsafe(32)),
        nickname="演示访客",
        is_admin=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_demo_session(db: Session) -> dict:
    """保留现有测试和调用方使用的无状态返回形状。"""
    user = _get_demo_user(db)
    return {"msg": "合成数据演示会话已就绪", **_payload(user)}


@router.post("/demo-session")
async def demo_session(response: Response, db: Session = Depends(get_db)):
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="演示会话未启用")
    user = _create_isolated_demo_user(db)
    establish_session(response, db, user)
    return {"msg": "合成数据演示会话已就绪", **_payload(user)}


@router.post("/register")
async def register(req: RegisterReq, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        nickname=req.nickname or req.username,
        is_admin=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    establish_session(response, db, user)
    return {"msg": "注册成功", **_payload(user)}


@router.post("/login")
async def login(req: LoginReq, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    establish_session(response, db, user)
    return {"msg": "登录成功", **_payload(user)}


@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    clear_session(response, request, db)
    return {"msg": "已退出"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return _payload(current_user)


@router.get("/recover-password")
async def recover_password_disabled():
    raise HTTPException(status_code=410, detail="出于安全原因，不再返回或展示任何账号密码")


@router.post("/reset-password/{target_user_id}")
async def reset_password(
    target_user_id: int,
    req: AdminResetPasswordReq,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_teacher),
):
    from api.companion import clear_companion_context_for_user
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = get_password_hash(req.new_password)
    clear_companion_context_for_user(target_user_id, db)
    db.query(UserSession).filter(UserSession.user_id == target_user_id).delete()
    db.commit()
    return {"msg": f"已重置 {user.username} 的密码，并注销其已有会话"}


@router.post("/change-password")
async def change_password(
    req: ChangePwdReq,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from api.companion import clear_companion_context_for_user
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    if req.new_password1 != req.new_password2:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")
    current_user.password_hash = get_password_hash(req.new_password1)
    clear_companion_context_for_user(current_user.id, db)
    db.query(UserSession).filter(UserSession.user_id == current_user.id).delete()
    db.commit()
    return {"msg": "密码修改成功，请重新登录"}


@router.get("/{user_id}", response_model=UserResp)
async def get_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id and int(current_user.is_admin or 0) < 2:
        raise HTTPException(status_code=403, detail="无权查看该资料")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    return target


@router.put("/{user_id}")
async def update_profile(
    user_id: int,
    nickname: str = "",
    avatar: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该资料")
    if nickname:
        current_user.nickname = nickname[:50]
    if avatar:
        current_user.avatar = avatar[:255]
    db.commit()
    return {"msg": "更新成功"}
