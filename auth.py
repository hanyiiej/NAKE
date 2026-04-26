from datetime import datetime, timedelta
import hashlib
import secrets
import os

# 从环境变量读取，本地开发有默认值，生产环境必须设置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
PASSWORD_SALT = os.getenv("PASSWORD_SALT", "dev-salt-change-in-production") or "fallback-salt"
SESSION_EXPIRE_HOURS = 24

sessions = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(f"{PASSWORD_SALT}{password}".encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_session(admin_id: int) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "admin_id": admin_id,
        "expires": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
    }
    return token

def verify_session(token: str) -> bool:
    if token not in sessions:
        return False
    session = sessions[token]
    if datetime.utcnow() > session["expires"]:
        del sessions[token]
        return False
    return True

def get_session_admin(token: str) -> int:
    return sessions.get(token, {}).get("admin_id")

def delete_session(token: str):
    if token in sessions:
        del sessions[token]
