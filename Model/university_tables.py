"""高校管理系统的可扩展领域模型。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from DAO.db import Base


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class Major(Base):
    __tablename__ = "majors"
    __table_args__ = (
        UniqueConstraint("college_id", "code", name="uq_major_college_code"),
        Index("ix_major_college_status", "college_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class AcademicTerm(Base):
    __tablename__ = "academic_terms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="active")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (Index("ix_course_status", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    credits = Column(Numeric(4, 1), nullable=False)
    hours = Column(Integer, nullable=False)
    course_type = Column(String(20), nullable=False, default="必修课")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class MajorCourse(Base):
    __tablename__ = "major_courses"
    __table_args__ = (
        UniqueConstraint("major_id", "course_id", name="uq_major_course"),
        Index("ix_major_course_required", "major_id", "is_required"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    is_required = Column(Boolean, nullable=False, default=True)


class StudentAcademicProfile(Base):
    __tablename__ = "student_academic_profiles"
    __table_args__ = (Index("ix_student_profile_college_major", "college_id", "major_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False, unique=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    grade = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class StaffProfile(Base):
    __tablename__ = "staff_profiles"
    __table_args__ = (Index("ix_staff_profile_college_department", "college_id", "department_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_no = Column(String(20), ForeignKey("staff_accounts.staff_no"), nullable=False, unique=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    position = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class TeachingSection(Base):
    __tablename__ = "teaching_sections"
    __table_args__ = (
        Index("ix_section_term_course", "academic_term_id", "course_id"),
        Index("ix_section_teacher_term", "teacher_id", "academic_term_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    academic_term_id = Column(Integer, ForeignKey("academic_terms.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teacher_table.tid"), nullable=True)
    capacity = Column(Integer, nullable=False)
    enrolled_count = Column(Integer, nullable=False, default=0)
    selection_open_at = Column(DateTime, nullable=False)
    selection_close_at = Column(DateTime, nullable=False)
    timetable_json = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("student_no", "teaching_section_id", name="uq_enrollment_student_section"),
        Index("ix_enrollment_student_status", "student_no", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    teaching_section_id = Column(Integer, ForeignKey("teaching_sections.id"), nullable=False)
    status = Column(String(20), nullable=False, default="enrolled")
    enrolled_at = Column(DateTime, nullable=False, default=datetime.now)
    dropped_at = Column(DateTime, nullable=True)


class CourseGrade(Base):
    __tablename__ = "course_grades"
    __table_args__ = (
        UniqueConstraint("student_no", "teaching_section_id", name="uq_grade_student_section"),
        Index("ix_grade_section_status", "teaching_section_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), ForeignKey("students.student_no"), nullable=False)
    teaching_section_id = Column(Integer, ForeignKey("teaching_sections.id"), nullable=False)
    score = Column(Numeric(5, 2), nullable=True)
    grade_point = Column(String(10), nullable=True)
    grade_label = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="submitted")
    submitted_at = Column(DateTime, nullable=False, default=datetime.now)
    approved_at = Column(DateTime, nullable=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("kind", "checksum", name="uq_import_kind_checksum"),
        Index("ix_import_batch_status_created", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String(30), nullable=False)
    checksum = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="previewed")
    created_by = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    confirmed_at = Column(DateTime, nullable=True)
    result_json = Column(JSON, nullable=True)


class ImportRowError(Base):
    __tablename__ = "import_row_errors"
    __table_args__ = (Index("ix_import_row_error_batch", "batch_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    field = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
