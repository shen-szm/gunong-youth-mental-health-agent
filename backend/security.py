"""
密码加密与验证工具
使用 hashlib + salt，不依赖 bcrypt/passlib，避免版本兼容问题
"""
import hashlib
import os
import hmac


def get_password_hash(password: str) -> str:
    """生成带salt的SHA-256哈希"""
    salt = os.urandom(16).hex()
    hashed = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        salt, hashed = hashed_password.split(":", 1)
        expected = hmac.new(salt.encode(), plain_password.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, hashed)
    except Exception:
        return False
