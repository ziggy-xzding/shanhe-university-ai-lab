"""学生成长报告模型。"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from DAO.db import Base


class AgentReport(Base):
    __tablename__ = "agent_reports"
    __table_args__ = (
        Index("ix_agent_report_student_time", "student_no", "created_at"),
        Index("ix_agent_report_level_time", "attention_level", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    report_type = Column(String(30), nullable=False)
    metrics_snapshot = Column(JSON, nullable=False)
    attention_level = Column(String(20), nullable=False)
    strengths = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True)
    action_plan = Column(Text, nullable=True)
    comment = Column(Text, nullable=False)
    generated_by = Column(String(30), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
