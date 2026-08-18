"""全量需求文档新增的画像、预警、智能体与校园服务实体。"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text

from DAO.db import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (Index("ix_student_profile_academic_risk", "academic_risk_level"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False, unique=True)
    gpa = Column(String(10), nullable=True)
    credit_deficit = Column(Integer, nullable=False, default=0)
    fail_count = Column(Integer, nullable=False, default=0)
    academic_risk_level = Column(String(20), nullable=False, default="normal")
    attendance_rate = Column(String(10), nullable=True)
    mood_average = Column(String(10), nullable=True)
    mood_trend = Column(String(20), nullable=True)
    career_interest = Column(JSON, nullable=True)
    skill_tags = Column(JSON, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class AcademicAlert(Base):
    __tablename__ = "academic_alerts"
    __table_args__ = (Index("ix_academic_alert_status", "status", "severity"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    alert_type = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False, default="warning")
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    agent_analysis = Column(Text, nullable=True)
    intervention = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    resolved_at = Column(DateTime, nullable=True)
    created_by = Column(String(30), nullable=False, default="system")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class AgentConversation(Base):
    __tablename__ = "agent_conversations"
    __table_args__ = (Index("ix_agent_conversation_owner_session", "owner_id", "session_id", "created_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(30), nullable=False)
    owner_role = Column(String(30), nullable=False)
    agent_type = Column(String(40), nullable=False)
    session_id = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    intent = Column(String(60), nullable=True)
    risk_level = Column(String(20), nullable=False, default="normal")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class AgentFeedback(Base):
    __tablename__ = "agent_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(30), nullable=False)
    message_id = Column(String(80), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class CampusActivity(Base):
    __tablename__ = "campus_activities"
    __table_args__ = (Index("ix_campus_activity_status_start", "status", "starts_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    category = Column(String(40), nullable=False)
    location = Column(String(200), nullable=True)
    starts_at = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False, default=100)
    enrolled_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="published")


class CareerOpportunity(Base):
    __tablename__ = "career_opportunities"
    __table_args__ = (Index("ix_career_opportunity_status_deadline", "status", "deadline"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=False)
    city = Column(String(80), nullable=False)
    job_type = Column(String(40), nullable=False, default="校招")
    tags = Column(JSON, nullable=True)
    deadline = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="published")


class MoodCheckin(Base):
    __tablename__ = "mood_checkins"
    __table_args__ = (Index("ix_mood_checkin_student_time", "student_no", "created_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    mood_score = Column(Integer, nullable=False)
    tags = Column(JSON, nullable=True)
    note = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=False, default="normal")
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class CampusServiceTicket(Base):
    __tablename__ = "campus_service_tickets"
    __table_args__ = (Index("ix_service_ticket_owner_status", "owner_id", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(30), nullable=False)
    category = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="submitted")
    priority = Column(String(20), nullable=False, default="normal")
    assigned_to = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class LibraryLoan(Base):
    """图书馆系统同步的学生借阅记录，当前提供本地演示适配层。"""

    __tablename__ = "library_loans"
    __table_args__ = (Index("ix_library_loan_student_status", "student_no", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    book_title = Column(String(200), nullable=False)
    author = Column(String(120), nullable=True)
    external_ref = Column(String(80), nullable=True, unique=True)
    borrowed_at = Column(DateTime, nullable=False, default=datetime.now)
    due_at = Column(DateTime, nullable=True)
    returned_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="borrowed")


class StudentTodo(Base):
    """学生端可归档待办，由成绩、选课和图书借阅等业务自动生成。"""

    __tablename__ = "student_todos"
    __table_args__ = (Index("ix_student_todo_student_status", "student_no", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    source_key = Column(String(120), nullable=False)
    todo_type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="normal")
    due_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
