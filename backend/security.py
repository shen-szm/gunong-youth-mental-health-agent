"""密码哈希工具；新密码使用 PBKDF2，兼容校验旧格式。"""
import hashlib
import os
import hmac


def get_password_hash(password: str) -> str:
    """生成带 salt 的 PBKDF2-SHA256 哈希。"""
    if len(password) < 10:
        raise ValueError("密码至少10位")
    iterations = 310_000
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        if hashed_password.startswith("pbkdf2_sha256$"):
            _, raw_iterations, salt, hashed = hashed_password.split("$", 3)
            expected = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode(), salt.encode(), int(raw_iterations)
            ).hex()
            return hmac.compare_digest(expected, hashed)
        salt, hashed = hashed_password.split(":", 1)
        legacy = hmac.new(salt.encode(), plain_password.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(legacy, hashed)
    except Exception:
        return False
