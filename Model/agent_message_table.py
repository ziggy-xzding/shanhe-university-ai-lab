"""学生与 Agent 的会话消息模型。"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from DAO.db import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("ix_agent_message_session_time", "session_id", "created_at"),
        Index("ix_agent_message_risk_time", "risk_level", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("agent_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    intent = Column(String(30), nullable=True)
    content = Column(Text, nullable=False)
    source_refs = Column(JSON, nullable=True)
    risk_level = Column(String(20), nullable=False, default="normal")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
