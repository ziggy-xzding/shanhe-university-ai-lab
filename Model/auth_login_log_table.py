"""登录审计日志模型。"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String

from DAO.db import Base


class AuthLoginLog(Base):
    __tablename__ = "auth_login_logs"
    __table_args__ = (
        Index("ix_login_account_time", "account_type", "account_id", "created_at"),
        Index("ix_login_success_time", "success", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_type = Column(String(20), nullable=False)
    account_id = Column(String(50), nullable=False)
    role = Column(String(20), nullable=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
