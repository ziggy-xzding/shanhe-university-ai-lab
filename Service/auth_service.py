"""认证服务的密码与令牌基础能力。"""

import hashlib
import os
from uuid import uuid4
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt


AUTH_ALGORITHM = "HS256"
AUTH_COOKIE_NAME = "wolink_auth"


UserRole = Literal[
    "admin",
    "college_admin",
    "academic_admin",
    "student_affairs",
    "counselor",
    "teacher",
    "archive_admin",
    "staff",
    "student",
]


@dataclass(frozen=True)
class AuthPrincipal:
    """已验证访问者的最小身份信息。"""

    role: UserRole
    subject_id: str
    display_name: str
    teacher_id: int | None = None
    staff_id: int | None = None
    college_id: int | None = None
    department_id: int | None = None


def hash_password(password: str) -> str:
    """生成可存储的 bcrypt 密码哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """安全验证明文密码与 bcrypt 哈希。"""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def token_digest(token: str) -> str:
    """计算令牌摘要，供数据库保存而非保存令牌明文。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(principal: AuthPrincipal, expires_minutes: int) -> str:
    """签发包含角色与主体标识的短期 JWT。"""
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise RuntimeError("缺少 AUTH_SECRET，无法签发登录令牌")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": principal.subject_id,
        "role": principal.role,
        "name": principal.display_name,
        "teacher_id": principal.teacher_id,
        "staff_id": principal.staff_id,
        "college_id": principal.college_id,
        "department_id": principal.department_id,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm=AUTH_ALGORITHM)


def decode_access_token(token: str) -> AuthPrincipal:
    """校验 JWT，并还原最小身份信息。"""
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise RuntimeError("缺少 AUTH_SECRET，无法验证登录令牌")
    try:
        payload = jwt.decode(token, secret, algorithms=[AUTH_ALGORITHM])
        role = payload["role"]
        subject_id = payload["sub"]
        display_name = payload["name"]
    except (KeyError, jwt.PyJWTError) as exc:
        raise ValueError("登录令牌无效或已过期") from exc
    if role not in {
        "admin",
        "college_admin",
        "academic_admin",
        "student_affairs",
        "counselor",
        "teacher",
        "archive_admin",
        "staff",
        "student",
    }:
        raise ValueError("登录令牌角色无效")
    return AuthPrincipal(
        role=role,
        subject_id=str(subject_id),
        display_name=str(display_name),
        teacher_id=payload.get("teacher_id"),
        staff_id=payload.get("staff_id"),
        college_id=payload.get("college_id"),
        department_id=payload.get("department_id"),
    )
