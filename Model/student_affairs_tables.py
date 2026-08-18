"""学生事务可扩展业务模型。"""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from DAO.db import Base


class StudentLeave(Base):
    __tablename__ = "student_leaves"
    __table_args__ = (Index("ix_student_leave_student_status", "student_no", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class StudentAidApplication(Base):
    __tablename__ = "student_aid_applications"
    __table_args__ = (Index("ix_student_aid_student_status", "student_no", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    aid_type = Column(String(40), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class StudentRewardPunishment(Base):
    __tablename__ = "student_reward_punishments"
    __table_args__ = (Index("ix_reward_punishment_student_type", "student_no", "record_type"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    record_type = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    detail = Column(Text, nullable=True)
    recorded_by = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.now)


class DormAssignment(Base):
    __tablename__ = "dorm_assignments"
    __table_args__ = (Index("ix_dorm_assignment_building_room", "building", "room_no"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False, unique=True)
    building = Column(String(50), nullable=False)
    room_no = Column(String(30), nullable=False)
    bed_no = Column(String(20), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class DormRoom(Base):
    """可供新生选择的宿舍房间库存。"""

    __tablename__ = "dorm_rooms"
    __table_args__ = (UniqueConstraint("building", "room_no", name="uq_dorm_room_location"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    building = Column(String(50), nullable=False)
    room_no = Column(String(30), nullable=False)
    room_type = Column(String(30), nullable=False, default="四人间")
    capacity = Column(Integer, nullable=False, default=4)
    status = Column(String(20), nullable=False, default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class CampusAnnouncement(Base):
    __tablename__ = "campus_announcements"
    __table_args__ = (Index("ix_announcement_status_publish", "status", "published_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    audience = Column(String(40), nullable=False, default="all")
    status = Column(String(20), nullable=False, default="draft")
    published_by = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False)
    published_at = Column(DateTime, nullable=True)


class GraduateDestination(Base):
    __tablename__ = "graduate_destinations"
    __table_args__ = (Index("ix_graduate_destination_type", "destination_type"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False, unique=True)
    destination_type = Column(String(30), nullable=False)
    organization = Column(String(200), nullable=True)
    detail = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
