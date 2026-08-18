"""职员登录账户模型。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from DAO.db import Base


class StaffAccount(Base):
    __tablename__ = "staff_accounts"
    __table_args__ = (
        Index("ix_staff_role_status", "role", "status"),
        Index("ix_staff_teacher_id", "teacher_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_no = Column(String(20), nullable=False, unique=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teacher_table.tid"), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )
