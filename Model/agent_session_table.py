"""学生成长 Agent 的短期身份会话模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String

from DAO.db import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index("ix_agent_session_student_status", "student_no", "status"),
        Index("ix_agent_session_expiry", "expires_at"),
    )

    id = Column(String(36), primary_key=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="active")
    expires_at = Column(DateTime, nullable=False)
    last_active_at = Column(DateTime, nullable=False, default=datetime.now)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
