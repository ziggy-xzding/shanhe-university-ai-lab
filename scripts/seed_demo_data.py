"""写入可重复执行的虚构演示数据。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import os
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from DAO.db import Base, engine, session
from Model.Student_score_table import Score
from Model.agent_message_table import AgentMessage
from Model.agent_report_table import AgentReport
from Model.agent_session_table import AgentSession
from Model.auth_login_log_table import AuthLoginLog
from Model.class_table import Class
from Model.consultant_table import Consultant
from Model.department_table import Department
from Model.employment_table import Employment
from Model.staff_account_table import StaffAccount
from Model.student_table import Student
from Model.teacher_table import teacher_table
from Model.university_tables import (
    AcademicTerm,
    College,
    Course,
    Major,
    MajorCourse,
    StudentAcademicProfile,
    StaffProfile,
    TeachingSection,
)
from Model.platform_tables import AcademicAlert, CampusActivity, CareerOpportunity, MoodCheckin, StudentProfile
from Model.student_affairs_tables import CampusAnnouncement
from Model.risk_alert_tables import CounselorAssignment
from Service.auth_service import hash_password, token_digest
from Service.score_analysis_service import build_student_overview

DEMO_LIMIT = max(3, int(os.getenv("DEMO_LIMIT", "3")))


def get_or_create(db, model, lookup: dict, defaults: dict | None = None):
    instance = db.query(model).filter_by(**lookup).first()
    if instance:
        return instance, False
    instance = model(**lookup, **(defaults or {}))
    db.add(instance)
    db.flush()
    return instance, True


def _seed_departments(db) -> list[Department]:
    items = [
        ("D001", "教学部", "唐文静", "A 座 301", "010-60010001"),
        ("D002", "就业服务部", "顾明", "A 座 302", "010-60010002"),
        ("D003", "教务部", "许婉", "B 座 201", "010-60010003"),
        ("D004", "运营部", "梁晨", "B 座 202", "010-60010004"),
    ]
    return [
        get_or_create(
            db,
            Department,
            {"dept_no": dept_no},
            {
                "dept_name": name,
                "dept_manager": manager,
                "dept_location": location,
                "dept_phone": phone,
                "is_deleted": False,
            },
        )[0]
        for dept_no, name, manager, location, phone in items[:DEMO_LIMIT]
    ]


def _seed_consultants(db) -> list[Consultant]:
    consultants = []
    regions = ["北京", "上海", "广州", "深圳", "杭州"]
    for index in range(DEMO_LIMIT):
        item, _ = get_or_create(
            db,
            Consultant,
            {"consultant_no": f"C{index + 1:03d}"},
            {
                "name": f"顾问{index + 1:02d}",
                "gender": "女" if index % 2 == 0 else "男",
                "phone": f"1390001{index:04d}",
                "email": f"consultant{index + 1:02d}@wolin.example",
                "dept_no": "D002" if index < 5 else "D003",
                "title": "高级顾问" if index % 3 == 0 else "学习顾问",
                "region": regions[index % len(regions)],
                "is_deleted": False,
            },
        )
        consultants.append(item)
    return consultants


def _seed_teachers(db) -> list[teacher_table]:
    teachers = []
    subjects = ["Python", "数据库", "前端", "Linux", "数据分析", "项目实战"]
    for index in range(DEMO_LIMIT):
        item, _ = get_or_create(
            db,
            teacher_table,
            {"tphone": f"1380000{index + 1:04d}"},
            {
                "tname": ["陈晓宁", "周明远", "林若溪", "沈一鸣"][index % 4]
                + f"{index + 1:02d}",
                "tsubject": subjects[index % len(subjects)],
                "t_code": "在职",
                "t_is_delete": False,
            },
        )
        teachers.append(item)
    return teachers


def _seed_classes(db, teachers: list[teacher_table]) -> list[Class]:
    classes = []
    for index in range(DEMO_LIMIT):
        item, _ = get_or_create(
            db,
            Class,
            {"class_no": f"AI24{index + 1:02d}"},
            {
                "name": f"AI 应用开发 24{index + 1:02d} 班",
                "start_date": datetime(2026, 3, 1) + timedelta(days=index * 14),
                "head_teacher_id": teachers[index].tid,
                "instructor_id": teachers[index].tid,
                "is_deleted": 0,
            },
        )
        classes.append(item)
    return classes


def _score_pattern(student_index: int) -> list[int]:
    patterns = [
        [88, 90, 91, 92, 93, 95],
        [61, 66, 70, 75, 80, 84],
        [75, 82, 69, 86, 73, 81],
        [70, 64, 62, 58, 55, 57],
    ]
    base = patterns[student_index % len(patterns)]
    offset = (student_index % 5) - 2
    return [max(35, min(99, score + offset)) for score in base]


def _seed_students_and_scores(db, classes: list[Class]) -> list[Student]:
    students = []
    names = ["李欣妍", "王子轩", "赵思琪", "陈浩然", "刘雨桐", "杨嘉诚"]
    schools = ["江城大学", "岭南学院", "北方理工", "海州师范"]
    majors = ["软件技术", "计算机科学", "电子商务", "信息管理"]
    for index in range(DEMO_LIMIT):
        class_item = classes[index // 12]
        student_no = f"ST24{index + 1:04d}"
        student, _ = get_or_create(
            db,
            Student,
            {"student_no": student_no},
            {
                "name": names[index % len(names)] + f"{index + 1:02d}",
                "class_id": class_item.id,
                "hometown": ["成都", "武汉", "西安", "郑州"][index % 4],
                "graduate_school": schools[index % len(schools)],
                "major": majors[index % len(majors)],
                "enrollment_time": class_item.start_date,
                "education": "本科" if index % 3 else "大专",
                "advisor_id": (index % 10) + 1,
                "age": 20 + (index % 8),
                "gender": "女" if index % 2 == 0 else "男",
                "is_deleted": False,
            },
        )
        if not student.password_hash:
            student.password_hash = hash_password("Student@123")
        students.append(student)
        for exam_seq, score_value in enumerate(_score_pattern(index), start=1):
            get_or_create(
                db,
                Score,
                {"student_no": student_no, "exam_seq": exam_seq},
                {"score": score_value, "is_deleted": False},
            )
    return students


def _seed_employment(db, students: list[Student], classes: list[Class]) -> None:
    for index, student in enumerate(students[:DEMO_LIMIT]):
        class_item = next(item for item in classes if item.id == student.class_id)
        get_or_create(
            db,
            Employment,
            {"student_no": student.student_no},
            {
                "class_no": class_item.class_no,
                "student_name": student.name,
                "class_name": class_item.name,
                "open_time": datetime(2026, 6, 1),
                "offer_time": datetime(2026, 6, 20) + timedelta(days=index),
                "company": ["云帆科技", "北辰数据", "星河软件", "万象智能"][index % 4],
                "salary": 8500 + index * 300,
                "is_deleted": False,
            },
        )


def _seed_staff_accounts(db, teachers: list[teacher_table]) -> None:
    staff_items = [
        ("A20260701", "admin01", "校园系统管理员", "admin", None, "Admin@123"),
        ("A20260702", "admin02", "运营管理员", "admin", None, "Admin@123"),
    ]
    staff_items.extend(
        (
            f"T202607{index + 1:02d}",
            f"teacher{index + 1:02d}",
            teacher.tname,
            "teacher",
            teacher.tid,
            "Teacher@123",
        )
        for index, teacher in enumerate(teachers)
    )
    for staff_no, username, display_name, role, teacher_id, password in staff_items:
        account, created = get_or_create(
            db,
            StaffAccount,
            {"staff_no": staff_no},
            {
                "username": username,
                "password_hash": hash_password(password),
                "display_name": display_name,
                "role": role,
                "teacher_id": teacher_id,
                "status": "active",
            },
        )
        if not created:
            account.username = username
            account.display_name = display_name
            account.role = role
            account.teacher_id = teacher_id
            account.status = "active"


def _seed_auth_logs(db) -> None:
    for index in range(DEMO_LIMIT):
        lookup = {
            "account_type": "student" if index % 2 else "staff",
            "account_id": f"seed-account-{index:02d}",
            "user_agent": "seed-demo",
        }
        get_or_create(
            db,
            AuthLoginLog,
            lookup,
            {
                "role": "student" if index % 2 else "teacher",
                "success": index % 5 != 0,
                "failure_reason": None if index % 5 != 0 else "invalid_credentials",
                "ip_hash": token_digest(f"127.0.0.{index}")[:64],
            },
        )


def _seed_agent_data(db, students: list[Student]) -> None:
    for index, student in enumerate(students[:DEMO_LIMIT]):
        session_id = f"00000000-0000-0000-0000-{index + 1:012d}"
        get_or_create(
            db,
            AgentSession,
            {"id": session_id},
            {
                "student_no": student.student_no,
                "token_hash": token_digest(f"seed-student-session-{index}"),
                "status": "active",
                "expires_at": datetime.now() + timedelta(days=7),
                "last_active_at": datetime.now(),
            },
        )
        for message_index in range(DEMO_LIMIT):
            get_or_create(
                db,
                AgentMessage,
                {
                    "session_id": session_id,
                    "role": "user" if message_index % 2 == 0 else "assistant",
                    "content": f"演示成长对话 {index + 1}-{message_index + 1}",
                },
                {
                    "intent": "analysis" if message_index % 2 else "grade_query",
                    "source_refs": [],
                    "risk_level": "normal",
                },
            )
    for index, student in enumerate(students[:DEMO_LIMIT]):
        existing = (
            db.query(AgentReport)
            .filter_by(student_no=student.student_no, report_type="latest_score")
            .first()
        )
        if existing:
            continue
        overview = build_student_overview(db, student.student_no)
        db.add(
            AgentReport(
                student_no=student.student_no,
                report_type="latest_score",
                metrics_snapshot=overview,
                attention_level=overview["attention_level"],
                strengths="学习节奏逐步清晰。",
                improvements="继续减少阶段考核波动。",
                action_plan="本周完成三组错题归纳并复测。",
                comment="易老师建议先稳住已掌握的阵地，再逐项补齐薄弱知识点。",
                generated_by="rule",
            )
        )


def _count(db, model, predicate) -> int:
    return int(db.query(model).filter(predicate).count())


def _seed_university_staff_roles(db, colleges: list[College], students: list[Student]) -> None:
    college_by_code = {college.code: college for college in colleges}
    role_specs = [
        ("C20260715", "collegeadmin01", "学院管理员", "college_admin", "College@123", "CS"),
        ("A20260716", "academic01", "教务管理员", "academic_admin", "Academic@123", None),
        ("S20260717", "affairs01", "学生事务老师", "student_affairs", "Affairs@123", None),
        ("C20260718", "counselor01", "辅导员", "counselor", "Counselor@123", "CS"),
        ("R20260719", "archive01", "档案管理员", "archive_admin", "Archive@123", "CS"),
        ("F20260720", "staff01", "学校职员", "staff", "Staff@123", None),
    ]
    for staff_no, username, display_name, role, password, college_code in role_specs:
        account, created = get_or_create(
            db,
            StaffAccount,
            {"staff_no": staff_no},
            {
                "username": username,
                "password_hash": hash_password(password),
                "display_name": display_name,
                "role": role,
                "status": "active",
            },
        )
        if not created:
            account.username = username
            account.display_name = display_name
            account.role = role
            account.status = "active"
        if college_code:
            get_or_create(
                db,
                StaffProfile,
                {"staff_no": staff_no},
                {"college_id": college_by_code[college_code].id, "position": display_name},
            )
    for student in students:
        get_or_create(
            db,
            CounselorAssignment,
            {"student_no": student.student_no},
            {"counselor_staff_no": "C20260718"},
        )


def seed_university_data(db) -> dict[str, int]:
    college_specs = [("CS", "计算机学院"), ("EE", "电子信息学院")]
    colleges = [
        get_or_create(db, College, {"code": code}, {"name": name, "status": "active"})[0]
        for code, name in college_specs
    ]
    college_by_code = {item.code: item for item in colleges}
    major_specs = [
        ("CS", "CS01", "计算机科学与技术"),
        ("CS", "SE01", "软件工程"),
        ("EE", "EE01", "电子信息工程"),
        ("EE", "AI01", "人工智能"),
    ]
    majors = [
        get_or_create(
            db,
            Major,
            {"college_id": college_by_code[college_code].id, "code": code},
            {"name": name, "status": "active"},
        )[0]
        for college_code, code, name in major_specs
    ]
    course_specs = [
        ("CS101", "程序设计基础"), ("CS201", "数据结构"),
        ("CS202", "操作系统"), ("EE101", "电路分析"),
        ("AI101", "人工智能导论"), ("GE101", "大学英语"),
    ]
    courses = [
        get_or_create(db, Course, {"code": code}, {"name": name, "credits": 3, "hours": 48, "status": "active"})[0]
        for code, name in course_specs[:DEMO_LIMIT]
    ]
    for major in majors:
        for course in courses:
            get_or_create(db, MajorCourse, {"major_id": major.id, "course_id": course.id}, {"is_required": True})
    terms = [
        get_or_create(db, AcademicTerm, {"code": code}, {"name": name, "starts_at": start, "ends_at": end, "status": "active"})[0]
        for code, name, start, end in [
            ("2026-2027-1", "2026-2027学年第一学期", datetime(2026, 9, 1), datetime(2027, 1, 20)),
            ("2026-2027-2", "2026-2027学年第二学期", datetime(2027, 2, 25), datetime(2027, 7, 10)),
        ]
    ]
    teachers = db.query(teacher_table).order_by(teacher_table.tid).all()
    for index, course in enumerate(courses):
        get_or_create(
            db,
            TeachingSection,
            {"course_id": course.id, "academic_term_id": terms[0].id},
            {
                "teacher_id": teachers[index % len(teachers)].tid if teachers else None,
                "capacity": 80,
                "enrolled_count": 0,
                "selection_open_at": datetime(2026, 8, 20),
                "selection_close_at": datetime(2026, 9, 15),
                "timetable_json": [],
                "status": "open",
            },
        )
    students = db.query(Student).filter(Student.student_no.like("ST24%")).order_by(Student.student_no).all()
    for index, student in enumerate(students):
        major = majors[index % len(majors)]
        get_or_create(
            db,
            StudentAcademicProfile,
            {"student_no": student.student_no},
            {"college_id": major.college_id, "major_id": major.id, "class_id": student.class_id, "grade": "2024", "status": "active"},
        )
    _seed_university_staff_roles(db, colleges, students)
    db.flush()
    return {"colleges": len(colleges), "majors": len(majors), "courses": len(courses), "terms": len(terms), "student_profiles": len(students)}


def seed_platform_data(db, students: list[Student]) -> dict[str, int]:
    for index, student in enumerate(students[:DEMO_LIMIT]):
        get_or_create(db, StudentProfile, {"student_no": student.student_no}, {"gpa": str(round(3.1 + index * .2, 2)), "credit_deficit": index, "fail_count": index, "academic_risk_level": "warning" if index else "normal", "attendance_rate": str(96 - index * 3), "mood_average": str(7 - index), "mood_trend": "stable", "career_interest": ["软件开发", "数据分析"], "skill_tags": ["Python", "SQL"]})
        get_or_create(db, MoodCheckin, {"student_no": student.student_no, "created_at": datetime(2026, 7, 25 + index)}, {"mood_score": 7 - index, "tags": ["学习", "作息"], "risk_level": "normal"})
        if index == 1:
            get_or_create(db, AcademicAlert, {"student_no": student.student_no, "alert_type": "fail_count"}, {"severity": "warning", "title": "近期成绩需要关注", "description": "检测到阶段性成绩波动，建议联系学习教练制定复习计划。", "created_by": "system", "status": "pending"})
    activity_specs = [("山河校园开放日", "校园活动", "大学生活动中心"), ("图书馆阅读分享会", "阅读活动", "图书馆一层"), ("羽毛球场预约体验", "体育活动", "东区体育馆")]
    for index, (title, category, location) in enumerate(activity_specs[:DEMO_LIMIT]):
        get_or_create(db, CampusActivity, {"title": title}, {"category": category, "location": location, "starts_at": datetime(2026, 9, 5 + index), "capacity": 100, "enrolled_count": 20 + index, "status": "published"})
    job_specs = [("软件开发工程师", "山河科技", "杭州", "校招"), ("数据分析实习生", "纳川数据", "上海", "实习"), ("产品助理", "致远教育", "北京", "校招")]
    for title, organization, city, job_type in job_specs[:DEMO_LIMIT]:
        get_or_create(db, CareerOpportunity, {"title": title, "organization": organization}, {"city": city, "job_type": job_type, "tags": ["Python", "成长快"], "deadline": datetime(2026, 10, 1), "status": "published"})
    announcement_specs = [
        ("2026年暑期及秋季学期安排", "请关注校历、返校和新学期注册时间，具体安排以教务通知为准。"),
        ("学生资助政策更新", "本学年学生资助申请、材料提交和审核时间已更新，请按通知准备材料。"),
        ("图书馆暑期开放安排", "暑期图书馆开放时间和借阅规则已发布，请合理安排借阅与归还。"),
    ]
    for title, content in announcement_specs[:DEMO_LIMIT]:
        get_or_create(
            db,
            CampusAnnouncement,
            {"title": title},
            {"content": content, "audience": "student", "status": "published", "published_by": "A20260701", "published_at": datetime(2026, 7, 25)},
        )
    return {"academic_alerts": _count(db, AcademicAlert, AcademicAlert.status == "pending"), "activities": _count(db, CampusActivity, CampusActivity.status == "published"), "career_opportunities": _count(db, CareerOpportunity, CareerOpportunity.status == "published"), "announcements": _count(db, CampusAnnouncement, CampusAnnouncement.status == "published")}


def seed_demo_data(db) -> dict[str, int]:
    departments = _seed_departments(db)
    _seed_consultants(db)
    teachers = _seed_teachers(db)
    classes = _seed_classes(db, teachers)
    students = _seed_students_and_scores(db, classes)
    _seed_employment(db, students, classes)
    _seed_staff_accounts(db, teachers)
    _seed_auth_logs(db)
    _seed_agent_data(db, students)
    university_summary = seed_university_data(db)
    platform_summary = seed_platform_data(db, students)
    db.flush()
    summary = {
        "departments": len(departments),
        "consultants": _count(db, Consultant, Consultant.consultant_no.like("C%")),
        "teachers": len(teachers),
        "classes": len(classes),
        "students": _count(db, Student, Student.student_no.like("ST24%")),
        "scores": _count(db, Score, Score.student_no.like("ST24%")),
        "employment": _count(db, Employment, Employment.student_no.like("ST24%")),
        "staff_accounts": _count(db, StaffAccount, StaffAccount.staff_no.like("%202607%")),
        "auth_login_logs": _count(db, AuthLoginLog, AuthLoginLog.user_agent == "seed-demo"),
        "agent_sessions": _count(db, AgentSession, AgentSession.id.like("00000000-0000-0000-0000-%")),
        "agent_messages": _count(db, AgentMessage, AgentMessage.content.like("演示成长对话%")),
        "agent_reports": _count(db, AgentReport, AgentReport.student_no.like("ST24%")),
    }
    summary.update(university_summary)
    summary.update(platform_summary)
    return summary


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = session()
    try:
        summary = seed_demo_data(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("演示数据已准备完成：")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    print("演示账号：admin01/Admin@123，teacher01/Teacher@123，学生入口示例 ST240001/李欣妍01")


if __name__ == "__main__":
    main()
