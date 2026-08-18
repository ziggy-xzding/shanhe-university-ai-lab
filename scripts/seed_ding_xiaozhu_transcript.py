"""导入新建文件夹中的华东交通大学成绩单演示数据。

数据来源：新建文件夹/41bb6277f0f8b53e090acbbe2bf4da81.jpg
该脚本可重复执行，不会重复创建丁小朱的课程、教学班、选课和成绩记录。
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from DAO.db import Base, ensure_schema_compatibility, engine, session
from Model.class_table import Class
from Model.student_table import Student
from Model.teacher_table import teacher_table  # noqa: F401 - registers the FK target
from Model.platform_tables import LibraryLoan
from Model.university_tables import (
    AcademicTerm,
    College,
    Course,
    CourseEnrollment,
    CourseGrade,
    Major,
    MajorCourse,
    StudentAcademicProfile,
    TeachingSection,
)
from Service.auth_service import hash_password
from Service.gpa_service import grade_point_for_score


STUDENT_NO = "20172110020108"
STUDENT_NAME = "丁小朱"
COLLEGE_CODE = "CS"
COLLEGE_NAME = "计算机学院"
MAJOR_CODE = "SE-RAIL"
MAJOR_NAME = "软件工程+道铁工程"
CLASS_NO = "软件+道铁2017-1"


TERMS = (
    ("2017-2018-1", "2017-2018 学年第 1 学期", datetime(2017, 9, 1), datetime(2018, 1, 31)),
    ("2017-2018-2", "2017-2018 学年第 2 学期", datetime(2018, 2, 26), datetime(2018, 7, 15)),
    ("2018-2019-1", "2018-2019 学年第 1 学期", datetime(2018, 9, 1), datetime(2019, 1, 31)),
    ("2018-2019-2", "2018-2019 学年第 2 学期", datetime(2019, 2, 25), datetime(2019, 7, 15)),
    ("2019-2020-1", "2019-2020 学年第 1 学期", datetime(2019, 9, 1), datetime(2020, 1, 31)),
    ("2019-2020-2", "2019-2020 学年第 2 学期", datetime(2020, 2, 24), datetime(2020, 7, 15)),
    ("2020-2021-1", "2020-2021 学年第 1 学期", datetime(2020, 9, 1), datetime(2021, 1, 31)),
)


# (course_name, course_type, credits, score_or_grade_label)
COURSES = {
    "2017-2018-1": (
        ("职业生涯与发展规划", "必修课", 1.0, "优秀"),
        ("专业导论与就业前景（入学教育）", "必修课", 0.5, "合格"),
        ("体育 I", "必修课", 1.0, 86),
        ("高等数学(A) I", "必修课", 6.0, 84),
        ("土建工程制图 I", "必修课", 3.0, 79),
        ("大学英语 I", "必修课", 3.0, 72),
        ("思想道德修养与法律基础", "必修课", 3.0, 80),
        ("软件开发基础", "必修课", 4.0, 79),
    ),
    "2017-2018-2": (
        ("认识实习(A)", "必修课", 1.0, "中等"),
        ("体育 II", "必修课", 1.0, 95),
        ("军事理论", "必修课", 1.0, "良好"),
        ("C++程序设计", "必修课", 3.0, 77),
        ("程序设计基础课程设计(C++语言)", "必修课", 1.0, "中等"),
        ("高等数学(A) II", "必修课", 4.0, 61),
        ("线性代数B", "必修课", 3.0, 88),
        ("大学物理", "必修课", 4.0, 85),
        ("土木工程制图 II", "必修课", 2.0, 79),
        ("大学英语 II", "必修课", 3.0, 70),
        ("交通概论", "必修课", 2.0, 77),
        ("马克思主义基本原理", "必修课", 3.0, 88),
        ("形势政策与省情教育 I", "必修课", 1.0, 90),
    ),
    "2018-2019-1": (
        ("土木工程材料(A)", "必修课", 3.0, 83.5),
        ("工程力学(G)", "必修课", 5.0, 60),
        ("体育 III", "必修课", 1.0, 86),
        ("概率论与数理统计", "必修课", 3.0, 88),
        ("大学英语 III", "必修课", 3.0, 66),
        ("中国近现代史纲要", "必修课", 2.0, 91),
        ("数据结构", "必修课", 4.0, 75),
        ("离散数学（B）", "必修课", 2.5, 92),
        ("数据结构课程设计", "必修课", 1.0, "合格"),
    ),
    "2018-2019-2": (
        ("创新创业过程与方法", "必修课", 0.5, "合格"),
        ("工程地质学", "必修课", 1.5, 84),
        ("测量学（A）", "必修课", 3.0, 70),
        ("结构力学(C)", "必修课", 4.0, 94),
        ("测量实习(A)", "必修课", 2.0, "良好"),
        ("体育 IV", "必修课", 1.0, 84),
        ("大学英语 IV", "必修课", 3.0, 76),
        ("毛泽东思想和中国特色社会主义理论体系概论（一）", "必修课", 3.5, 74),
        ("形势政策与省情教育 II", "必修课", 1.0, 89),
        ("数据库系统原理（B）", "必修课", 3.0, 82),
        ("软件工程(B)", "限选课", 3.0, 78),
        ("计算方法(B)", "限选课", 2.0, 75),
        ("数据库系统原理课程设计", "必修课", 1.0, "良好"),
    ),
    "2019-2020-1": (
        ("土力学（A）", "必修课", 2.5, 68),
        ("铁路工程（A）", "必修课", 2.5, 88),
        ("隧道工程（C）", "必修课", 1.5, 82),
        ("工程经济学(A)", "限选课", 1.0, 95),
        ("施工测量", "限选课", 2.5, 92),
        ("混凝土与结构设计原理（C）", "必修课", 3.5, 70),
        ("施工测量实习", "必修课", 2.0, "良好"),
        ("铁路轨道课程设计", "必修课", 1.0, "优秀"),
        ("毛泽东思想和中国特色社会主义理论体系概论（二）", "必修课", 2.5, "良好"),
        ("操作系统（B）", "必修课", 2.0, 93),
        ("编译原理（B）", "必修课", 3.0, 95),
        ("计算机网络（B）", "必修课", 3.0, 90),
        ("VC程序设计", "限选课", 2.0, 70),
    ),
    "2019-2020-2": (
        ("就业指导", "必修课", 1.0, 92),
        ("施工技术（D）", "必修课", 3.0, 80),
        ("基础工程（D）", "必修课", 2.0, 84),
        ("路基工程（B）", "必修课", 2.5, "中等"),
        ("铁路桥梁（B）", "必修课", 3.0, 86),
        ("工务工程（B）", "必修课", 2.0, 72),
        ("基础工程课程设计", "必修课", 1.0, "中等"),
        ("铁路桥梁课程设计", "必修课", 1.0, "中等"),
        ("路基工程课程设计", "必修课", 1.0, "中等"),
        ("计算机图形学", "限选课", 3.0, 75),
        ("计算机网络课程设计", "必修课", 1.0, "中等"),
    ),
    "2020-2021-1": (
        ("专业创新创业实践", "必修课", 2.0, "良好"),
        ("工程项目管理(A)", "限选课", 1.0, 86),
        ("施工组织与概预算(A)", "限选课", 2.5, 89),
        ("土木工程测量技术(D)", "限选课", 2.0, 82),
        ("铁路规划与线路设计(B)", "必修课", 2.5, 86),
        ("软弱地基处理（C）", "必修课", 1.5, 81),
        ("铁道工程专业英语(C)", "必修课", 2.0, 90),
        ("铁路规划与线路设计（选线）课程设计", "必修课", 2.0, "良好"),
        ("施工组织与概预算(A)课程设计", "必修课", 1.0, "中等"),
        ("软件工程实训(B)", "必修课", 4.0, "合格"),
    ),
}


def get_or_create(db, model, statement, factory):
    item = db.execute(statement).scalar_one_or_none()
    if item is None:
        item = factory()
        db.add(item)
        db.flush()
    return item


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    db = session()
    try:
        college = get_or_create(
            db,
            College,
            select(College).where(College.code == COLLEGE_CODE),
            lambda: College(code=COLLEGE_CODE, name=COLLEGE_NAME, status="active"),
        )
        major = get_or_create(
            db,
            Major,
            select(Major).where(Major.college_id == college.id, Major.code == MAJOR_CODE),
            lambda: Major(college_id=college.id, code=MAJOR_CODE, name=MAJOR_NAME, status="active"),
        )
        classroom = get_or_create(
            db,
            Class,
            select(Class).where(Class.class_no == CLASS_NO),
            lambda: Class(class_no=CLASS_NO, name="软件工程+道铁工程 2017-1 班", start_date=datetime(2017, 9, 1), head_teacher_id=1, instructor_id=1, is_deleted=0),
        )
        student = db.execute(select(Student).where(Student.student_no == STUDENT_NO)).scalar_one_or_none()
        if student is None:
            student = Student(student_no=STUDENT_NO, name=STUDENT_NAME)
            db.add(student)
            db.flush()
        student.name = STUDENT_NAME
        student.password_hash = hash_password("123456")
        student.class_id = classroom.id
        student.major = MAJOR_NAME
        student.enrollment_time = datetime(2017, 9, 1)
        student.graduation_time = datetime(2021, 6, 30)
        student.education = "本科"
        student.is_deleted = False
        profile = db.execute(select(StudentAcademicProfile).where(StudentAcademicProfile.student_no == STUDENT_NO)).scalar_one_or_none()
        if profile is None:
            profile = StudentAcademicProfile(student_no=STUDENT_NO)
            db.add(profile)
        profile.college_id = college.id
        profile.major_id = major.id
        profile.class_id = classroom.id
        profile.grade = "2017"
        profile.status = "active"

        loan = db.execute(select(LibraryLoan).where(LibraryLoan.external_ref == "LIB-DXZ-001")).scalar_one_or_none()
        if loan is None:
            loan = LibraryLoan(external_ref="LIB-DXZ-001", student_no=STUDENT_NO, book_title="数据结构与算法分析", author="Mark Allen Weiss")
            db.add(loan)
        loan.student_no = STUDENT_NO
        loan.borrowed_at = datetime(2026, 7, 1)
        loan.due_at = datetime(2026, 7, 28)
        loan.returned_at = None
        loan.status = "borrowed"

        term_map = {}
        for code, name, starts_at, ends_at in TERMS:
            term = get_or_create(db, AcademicTerm, select(AcademicTerm).where(AcademicTerm.code == code), lambda code=code, name=name, starts_at=starts_at, ends_at=ends_at: AcademicTerm(code=code, name=name, starts_at=starts_at, ends_at=ends_at, status="closed"))
            term.name, term.starts_at, term.ends_at, term.status = name, starts_at, ends_at, "closed"
            term_map[code] = term

        course_count = 0
        grade_count = 0
        for term_code, rows in COURSES.items():
            term = term_map[term_code]
            for index, (name, course_type, credits, result) in enumerate(rows, start=1):
                code = f"DXZ-{term_code[:4]}-{term_code[-1]}-{index:02d}"
                course = get_or_create(db, Course, select(Course).where(Course.code == code), lambda code=code, name=name, credits=credits, course_type=course_type: Course(code=code, name=name, credits=Decimal(str(credits)), hours=max(8, round(float(credits) * 16)), course_type=course_type, status="active"))
                course.name, course.credits, course.course_type, course.hours = name, Decimal(str(credits)), course_type, max(8, round(float(credits) * 16))
                relation = db.execute(select(MajorCourse).where(MajorCourse.major_id == major.id, MajorCourse.course_id == course.id)).scalar_one_or_none()
                if relation is None:
                    db.add(MajorCourse(major_id=major.id, course_id=course.id, is_required=course_type == "必修课"))
                section = db.execute(select(TeachingSection).where(TeachingSection.course_id == course.id, TeachingSection.academic_term_id == term.id)).scalar_one_or_none()
                if section is None:
                    section = TeachingSection(course_id=course.id, academic_term_id=term.id, teacher_id=1, capacity=100, enrolled_count=1, selection_open_at=term.starts_at, selection_close_at=term.ends_at, timetable_json=[], status="finished")
                    db.add(section)
                    db.flush()
                enrollment = db.execute(select(CourseEnrollment).where(CourseEnrollment.student_no == STUDENT_NO, CourseEnrollment.teaching_section_id == section.id)).scalar_one_or_none()
                if enrollment is None:
                    db.add(CourseEnrollment(student_no=STUDENT_NO, teaching_section_id=section.id, status="enrolled", enrolled_at=term.starts_at))
                numeric_score = Decimal(str(result)) if isinstance(result, (int, float)) else None
                grade = db.execute(select(CourseGrade).where(CourseGrade.student_no == STUDENT_NO, CourseGrade.teaching_section_id == section.id)).scalar_one_or_none()
                if grade is None:
                    grade = CourseGrade(student_no=STUDENT_NO, teaching_section_id=section.id)
                    db.add(grade)
                grade.score = numeric_score
                grade.grade_label = None if numeric_score is not None else str(result)
                point = grade_point_for_score(numeric_score)
                grade.grade_point = f"{point:.2f}" if point is not None else None
                grade.status = "approved"
                grade.approved_at = datetime(2021, 3, 21)
                course_count += 1
                grade_count += 1
        db.commit()
        print({"student_no": STUDENT_NO, "student": STUDENT_NAME, "courses": course_count, "grades": grade_count, "college": COLLEGE_NAME, "major": MAJOR_NAME, "class": CLASS_NO})
    finally:
        db.close()


if __name__ == "__main__":
    main()
