"""FastAPI 身份解析与角色授权依赖项。"""

from datetime import datetime
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.agent_session_table import AgentSession
from Service.auth_service import (
    AUTH_COOKIE_NAME,
    AuthPrincipal,
    decode_access_token,
    token_digest,
)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="身份验证失败或已过期",
    )


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    """从 Cookie 读取令牌，并额外校验学生会话状态。"""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise _unauthorized()
    try:
        principal = decode_access_token(token)
    except (RuntimeError, ValueError):
        raise _unauthorized()

    if principal.role == "student":
        agent_session = db.execute(
            select(AgentSession).where(
                AgentSession.student_no == principal.subject_id,
                AgentSession.token_hash == token_digest(token),
                AgentSession.status == "active",
            )
        ).scalar_one_or_none()
        if not agent_session or agent_session.expires_at <= datetime.now():
            raise _unauthorized()
        agent_session.last_active_at = datetime.now()
        db.commit()
    return principal


def require_roles(*roles: str) -> Callable[..., AuthPrincipal]:
    """创建限定角色的 FastAPI 依赖项。"""

    def dependency(
        principal: AuthPrincipal = Depends(get_current_principal),
    ) -> AuthPrincipal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前身份无权访问该资源",
            )
        return principal

    return dependency
