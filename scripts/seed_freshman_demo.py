"""创建 2026 级新生演示账号、开放课程和可选寝室。"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from DAO.db import Base, engine, session
from Model.class_table import Class
from Model.platform_tables import LibraryLoan
from Model.student_affairs_tables import DormRoom
from Model.student_table import Student
from Model.teacher_table import teacher_table  # noqa: F401 - registers FK target
from Model.university_tables import AcademicTerm, College, Course, Major, MajorCourse, StudentAcademicProfile, TeachingSection
from Service.auth_service import hash_password


STUDENT_NO = "20260110010101"
STUDENT_NAME = "申屠浙"
PASSWORD = "123456"
COLLEGE_CODE = "INTL"
COLLEGE_NAME = "国际学院"
MAJOR_CODE = "EN01"
MAJOR_NAME = "英语"
CLASS_NO = "EN2026-1"
TERM_CODE = "2026-2027-1"
OPEN_AT = datetime(2026, 7, 20)
CLOSE_AT = datetime(2026, 8, 31)


def get_or_create(db, model, filters: dict, defaults: dict):
    item = db.query(model).filter_by(**filters).first()
    if item:
        return item
    item = model(**filters, **defaults)
    db.add(item)
    db.flush()
    return item


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = session()
    try:
        college = get_or_create(db, College, {"code": COLLEGE_CODE}, {"name": COLLEGE_NAME, "status": "active"})
        major = get_or_create(db, Major, {"college_id": college.id, "code": MAJOR_CODE}, {"name": MAJOR_NAME, "status": "active"})
        classroom = get_or_create(
            db,
            Class,
            {"class_no": CLASS_NO},
            {"name": "英语 2026-1 班", "start_date": datetime(2026, 9, 1), "head_teacher_id": 1, "instructor_id": 1, "is_deleted": 0},
        )
        student = get_or_create(db, Student, {"student_no": STUDENT_NO}, {"name": STUDENT_NAME})
        student.name = STUDENT_NAME
        student.password_hash = hash_password(PASSWORD)
        student.class_id = classroom.id
        student.major = major.name
        student.enrollment_time = datetime(2026, 9, 1)
        student.graduation_time = datetime(2030, 6, 30)
        student.education = "本科"
        student.age = 18
        student.gender = "女"
        student.is_deleted = False

        profile = get_or_create(
            db,
            StudentAcademicProfile,
            {"student_no": STUDENT_NO},
            {"college_id": college.id, "major_id": major.id, "class_id": classroom.id, "grade": "2026", "status": "active"},
        )
        profile.college_id = college.id
        profile.major_id = major.id
        profile.class_id = classroom.id
        profile.grade = "2026"
        profile.status = "active"

        term = get_or_create(
            db,
            AcademicTerm,
            {"code": TERM_CODE},
            {"name": "2026-2027 学年第 1 学期", "starts_at": datetime(2026, 9, 1), "ends_at": datetime(2027, 1, 20), "status": "active"},
        )
        term.name = "2026-2027 学年第 1 学期"
        term.starts_at = datetime(2026, 9, 1)
        term.ends_at = datetime(2027, 1, 20)
        term.status = "active"

        course_specs = (
            ("GE101", "大学英语 I", 3.0, 48),
            ("EN101", "英语听说 I", 2.0, 32),
            ("EN102", "英语写作 I", 2.0, 32),
            ("EN103", "英语阅读 I", 2.0, 32),
            ("GE201", "高等数学 I", 5.0, 80),
            ("GE202", "大学体育 I", 1.0, 32),
            ("GE203", "中国近现代史纲要", 3.0, 48),
            ("GE204", "计算机应用基础", 2.0, 32),
        )
        section_count = 0
        for index, (code, name, credits, hours) in enumerate(course_specs, start=1):
            course = get_or_create(db, Course, {"code": code}, {"name": name, "credits": Decimal(str(credits)), "hours": hours, "course_type": "必修课", "status": "active"})
            course.name = name
            course.credits = Decimal(str(credits))
            course.hours = hours
            course.course_type = "必修课"
            relation = db.execute(select(MajorCourse).where(MajorCourse.major_id == major.id, MajorCourse.course_id == course.id)).scalar_one_or_none()
            if relation is None:
                db.add(MajorCourse(major_id=major.id, course_id=course.id, is_required=True))
            section = db.execute(select(TeachingSection).where(TeachingSection.course_id == course.id, TeachingSection.academic_term_id == term.id).order_by(TeachingSection.id)).scalars().first()
            timetable = [{"day": ((index - 1) % 5) + 1, "start": "08:00", "end": "09:40"}]
            if section is None:
                section = TeachingSection(course_id=course.id, academic_term_id=term.id, teacher_id=1, capacity=60, enrolled_count=0, selection_open_at=OPEN_AT, selection_close_at=CLOSE_AT, timetable_json=timetable, status="open")
                db.add(section)
            else:
                section.capacity = max(section.capacity, 60)
                section.selection_open_at = OPEN_AT
                section.selection_close_at = CLOSE_AT
                section.timetable_json = timetable
                section.status = "open"
            section_count += 1

        for building, room_no in (("东区 1 栋", "101"), ("东区 1 栋", "102"), ("东区 2 栋", "201")):
            old_room = get_or_create(db, DormRoom, {"building": building, "room_no": room_no}, {"room_type": "四人间", "capacity": 4, "status": "closed"})
            old_room.status = "closed"
        for building, room_no in (("紫荆楼B栋", "707"), ("紫荆楼B栋", "708")):
            get_or_create(db, DormRoom, {"building": building, "room_no": room_no}, {"room_type": "四人间", "capacity": 4, "status": "open"})

        db.commit()
        print({"student_no": STUDENT_NO, "student": STUDENT_NAME, "password": PASSWORD, "grade": "2026", "open_sections": section_count, "dorm_rooms": 2})
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
