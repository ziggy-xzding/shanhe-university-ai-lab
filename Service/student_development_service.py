"""学生发展页的数据编排：待办、学校推送和分群推荐。"""

from datetime import datetime, timedelta

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from Model.platform_tables import CareerOpportunity, LibraryLoan, StudentTodo
from Model.student_affairs_tables import CampusAnnouncement
from Model.student_table import Student
from Model.university_tables import AcademicTerm, Course, CourseGrade, CourseEnrollment, TeachingSection


def _ensure_todo(
    db: Session,
    *,
    student_no: str,
    source_key: str,
    todo_type: str,
    title: str,
    description: str,
    priority: str = "normal",
    due_at: datetime | None = None,
) -> StudentTodo:
    item = db.execute(
        select(StudentTodo).where(
            StudentTodo.student_no == student_no,
            StudentTodo.source_key == source_key,
        )
    ).scalar_one_or_none()
    if item is None:
        item = StudentTodo(
            student_no=student_no,
            source_key=source_key,
            todo_type=todo_type,
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
            status="active",
        )
        db.add(item)
    elif item.status == "active":
        item.title = title
        item.description = description
        item.priority = priority
        item.due_at = due_at
    return item


def sync_student_todos(db: Session, student_no: str) -> list[StudentTodo]:
    """把业务事实同步成待办；学生点“已阅”后不会被同一来源重新生成。"""
    now = datetime.now()
    open_section = db.execute(
        select(TeachingSection, AcademicTerm)
        .join(AcademicTerm, AcademicTerm.id == TeachingSection.academic_term_id)
        .where(
            TeachingSection.status == "open",
            TeachingSection.selection_open_at <= now,
            TeachingSection.selection_close_at >= now,
        )
        .order_by(TeachingSection.selection_close_at)
        .limit(1)
    ).first()
    if open_section:
        section, term = open_section
        enrolled = db.execute(
            select(CourseEnrollment.id).where(
                CourseEnrollment.student_no == student_no,
                CourseEnrollment.teaching_section_id == section.id,
                CourseEnrollment.status == "enrolled",
            )
        ).scalar_one_or_none()
        if enrolled is None:
            _ensure_todo(
                db,
                student_no=student_no,
                source_key=f"selection:{term.code}",
                todo_type="enrollment",
                title="还有开放课程未选",
                description=f"{term.name}仍有课程开放选课，请先核对培养方案和时间冲突。",
                priority="high",
                due_at=section.selection_close_at,
            )

    loans = db.execute(
        select(LibraryLoan).where(
            LibraryLoan.student_no == student_no,
            LibraryLoan.status == "borrowed",
        )
    ).scalars().all()
    for loan in loans:
        overdue = loan.due_at is not None and loan.due_at < now
        _ensure_todo(
            db,
            student_no=student_no,
            source_key=f"library:{loan.external_ref or loan.id}",
            todo_type="library",
            title="图书馆书籍待归还" if not overdue else "图书馆书籍已逾期",
            description=f"《{loan.book_title}》" + ("已超过归还日期，请尽快处理。" if overdue else "尚未归还，请留意归还日期。"),
            priority="high" if overdue else "normal",
            due_at=loan.due_at,
        )

    failed_rows = db.execute(
        select(CourseGrade, TeachingSection, Course, AcademicTerm)
        .join(TeachingSection, TeachingSection.id == CourseGrade.teaching_section_id)
        .join(Course, Course.id == TeachingSection.course_id)
        .join(AcademicTerm, AcademicTerm.id == TeachingSection.academic_term_id)
        .where(
            CourseGrade.student_no == student_no,
            CourseGrade.status == "approved",
            CourseGrade.score.is_not(None),
            CourseGrade.score < 60,
        )
    ).all()
    for grade, _section, course, term in failed_rows:
        _ensure_todo(
            db,
            student_no=student_no,
            source_key=f"grade:{grade.id}",
            todo_type="makeup",
            title="不及格课程需要补考",
            description=f"《{course.name}》成绩为 {grade.score:g} 分（{term.name}），请关注补考安排。",
            priority="high",
        )

    db.flush()
    return list(
        db.execute(
            select(StudentTodo)
            .where(StudentTodo.student_no == student_no, StudentTodo.status == "active")
            .order_by(case((StudentTodo.priority == "high", 0), else_=1), StudentTodo.due_at, StudentTodo.created_at)
            .limit(3)
        ).scalars()
    )


def todo_href(todo_type: str) -> str:
    return {
        "enrollment": "/pages/course-selection",
        "library": "/pages/library",
        "makeup": "/pages/transcript",
        "dorm": "/pages/dorm-selection",
    }.get(todo_type, "/pages/student-agent")


def build_student_development(db: Session, student_no: str) -> dict:
    student = db.execute(
        select(Student).where(Student.student_no == student_no, Student.is_deleted.is_(False))
    ).scalar_one_or_none()
    if not student:
        raise ValueError("学生不存在")

    todos = sync_student_todos(db, student_no)
    announcements = db.execute(
        select(CampusAnnouncement)
        .where(
            CampusAnnouncement.status == "published",
            CampusAnnouncement.audience.in_(("all", "student")),
        )
        .order_by(CampusAnnouncement.published_at.desc(), CampusAnnouncement.id.desc())
        .limit(3)
    ).scalars().all()

    profile_grade = None
    from Model.university_tables import StudentAcademicProfile
    profile = db.execute(
        select(StudentAcademicProfile).where(StudentAcademicProfile.student_no == student_no)
    ).scalar_one_or_none()
    if profile and profile.grade:
        try:
            profile_grade = int(profile.grade)
        except ValueError:
            profile_grade = None
    enrollment_year = student.enrollment_time.year if student.enrollment_time else profile_grade
    current_year_level = None
    if enrollment_year:
        current_year_level = max(1, min(4, datetime.now().year - enrollment_year + 1))
    is_final_year = current_year_level == 4 or (student.graduation_time and student.graduation_time <= datetime.now() + timedelta(days=365 * 2))

    recommendations = []
    if is_final_year:
        jobs = db.execute(
            select(CareerOpportunity)
            .where(CareerOpportunity.status == "published")
            .order_by(CareerOpportunity.deadline, CareerOpportunity.id)
            .limit(2)
        ).scalars().all()
        recommendations.extend(
            {
                "type": "career",
                "title": job.title,
                "description": f"{job.organization} · {job.city} · {job.job_type}",
                "href": "/pages/career",
            }
            for job in jobs
        )
    recommendations.append(
        {
            "type": "learning",
            "title": "继续学习一个新主题",
            "description": "毕业不是学习的终点，可以从知识库、课程或图书馆选择一个感兴趣的主题。",
            "href": "/pages/campus-assistant",
        }
    )
    level_label = {1: "一", 2: "二", 3: "三", 4: "四"}.get(current_year_level, "-")
    return {
        "todos": [
            {
                "id": item.id,
                "todo_type": item.todo_type,
                "title": item.title,
                "description": item.description,
                "priority": item.priority,
                "due_at": item.due_at,
                "status": item.status,
                "href": todo_href(item.todo_type),
            }
            for item in todos
        ],
        "announcements": [
            {"id": item.id, "title": item.title, "content": item.content, "published_at": item.published_at}
            for item in announcements
        ],
        "recommendations": recommendations[:3],
        "student_group": "大四/毕业阶段" if is_final_year else f"大{level_label}学生",
    }
