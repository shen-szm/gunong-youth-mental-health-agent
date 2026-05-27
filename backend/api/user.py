"""
用户API路由 - 注册/登录/个人信息
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
from security import get_password_hash, verify_password

router = APIRouter(prefix="/api/user", tags=["user"])

class RegisterReq(BaseModel):
    username: str
    password: str
    nickname: str = ""

class LoginReq(BaseModel):
    username: str
    password: str

class UserResp(BaseModel):
    id: int
    username: str
    nickname: str = ""
    avatar: str = ""
    class Config:
        from_attributes = True

@router.post("/register")
async def register(req: RegisterReq, db: Session = Depends(get_db)):
    """用户注册"""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        plain_password=req.password,  # 存储明文密码用于找回密码
        nickname=req.nickname or req.username
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "注册成功", "user_id": user.id}

@router.post("/login")
async def login(req: LoginReq, db: Session = Depends(get_db)):
    """用户登录（简化版，返回user_id）"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {
        "msg": "登录成功",
        "user_id": user.id,
        "nickname": user.nickname,
        "is_admin": bool(user.is_admin)
    }

@router.get("/{user_id}", response_model=UserResp)
async def get_profile(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.put("/{user_id}")
async def update_profile(user_id: int, nickname: str = "", avatar: str = "", db: Session = Depends(get_db)):
    """更新用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if nickname:
        user.nickname = nickname
    if avatar:
        user.avatar = avatar
    db.commit()
    return {"msg": "更新成功"}


@router.get("/recover-password")
async def recover_password(username: str, db: Session = Depends(get_db)):
    """找回密码：输入用户名返回明文密码"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户名不存在")
    if not user.plain_password:
        raise HTTPException(status_code=400, detail="该账号密码无法找回，请联系管理员重置")
    return {"username": user.username, "password": user.plain_password}


@router.post("/reset-password/{user_id}")
async def reset_password(user_id: int, admin_id: int, new_password: str = "123456", db: Session = Depends(get_db)):
    """管理员重置用户密码"""
    from models import User as UserModel
    admin = db.query(UserModel).filter(UserModel.id == admin_id).first()
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = get_password_hash(new_password)
    user.plain_password = new_password
    db.commit()
    return {"msg": f"已将 {user.username} 的密码重置为 {new_password}"}
