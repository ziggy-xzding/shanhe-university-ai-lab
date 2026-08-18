"""心理风险预警及辅导员处置记录。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from DAO.db import Base


class CounselorAssignment(Base):
    __tablename__ = "counselor_assignments"
    __table_args__ = (
        UniqueConstraint("student_no", name="uq_counselor_assignment_student"),
        Index("ix_counselor_assignment_counselor", "counselor_staff_no"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    counselor_staff_no = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    __table_args__ = (
        Index("ix_risk_alert_counselor_status", "counselor_staff_no", "status"),
        Index("ix_risk_alert_student_time", "student_no", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    counselor_staff_no = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    risk_level = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    trigger_summary = Column(Text, nullable=False)
    disposition = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class UnassignedRiskAlert(Base):
    """尚未配置辅导员归属时的最小必要预警暂存记录。"""

    __tablename__ = "unassigned_risk_alerts"
    __table_args__ = (
        Index("ix_unassigned_risk_alert_status_time", "status", "created_at"),
        Index("ix_unassigned_risk_alert_student", "student_no", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    risk_level = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    trigger_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    assigned_at = Column(DateTime, nullable=True)
