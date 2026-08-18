"""匿名投诉、建议与申诉工单模型。"""

from datetime import datetime
from hashlib import sha256
from secrets import token_urlsafe

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from DAO.db import Base


class ComplaintTicket(Base):
    __tablename__ = "complaint_tickets"
    __table_args__ = (
        Index("ix_complaint_status_category", "status", "category"),
        Index("ix_complaint_tracking_token", "tracking_token_hash", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(40), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="submitted")
    anonymous = Column(Boolean, nullable=False, default=True)
    tracking_token_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        default=lambda: sha256(token_urlsafe(24).encode("utf-8")).hexdigest(),
    )
    assigned_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class ComplaintIdentity(Base):
    __tablename__ = "complaint_identities"
    __table_args__ = (Index("ix_complaint_identity_student", "student_no"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("complaint_tickets.id"), nullable=False, unique=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ComplaintAction(Base):
    __tablename__ = "complaint_actions"
    __table_args__ = (Index("ix_complaint_action_ticket_time", "ticket_id", "created_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("complaint_tickets.id"), nullable=False)
    actor_staff_no = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=True)
    action = Column(String(30), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
