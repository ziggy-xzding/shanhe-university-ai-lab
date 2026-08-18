"""高校管理统计概览，按角色数据范围汇总。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.university_tables import AcademicTerm, College, Course, Major, MajorCourse, StudentAcademicProfile, TeachingSection
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles


university_statistics_router = APIRouter(prefix="/api/university/statistics", tags=["高校统计"])
require_statistics_viewer = require_roles("admin", "college_admin", "academic_admin")


@university_statistics_router.get("/overview")
def get_statistics_overview(
    principal: AuthPrincipal = Depends(require_statistics_viewer),
    db: Session = Depends(get_db),
):
    student_statement = select(func.count(StudentAcademicProfile.id))
    college_name = None
    if principal.role == "college_admin":
        if principal.college_id is None:
            raise HTTPException(status_code=403, detail="学院管理员未配置学院数据范围")
        college = db.get(College, principal.college_id)
        college_name = college.name if college else None
        student_statement = student_statement.where(StudentAcademicProfile.college_id == principal.college_id)
    return {
        "scope": "college" if principal.role == "college_admin" else "university",
        "college_name": college_name,
        "student_count": db.execute(student_statement).scalar_one(),
        "course_count": db.execute(select(func.count(Course.id)).where(Course.status == "active")).scalar_one(),
        "teaching_section_count": db.execute(select(func.count(TeachingSection.id)).where(TeachingSection.status == "open")).scalar_one(),
        "active_term_count": db.execute(select(func.count(AcademicTerm.id)).where(AcademicTerm.status == "active")).scalar_one(),
    }


@university_statistics_router.get("/breakdown")
def get_statistics_breakdown(
    principal: AuthPrincipal = Depends(require_statistics_viewer),
    db: Session = Depends(get_db),
):
    """Return the college -> major -> course hierarchy within the viewer's scope."""
    college_statement = select(College).where(College.status == "active")
    if principal.role == "college_admin":
        if principal.college_id is None:
            raise HTTPException(status_code=403, detail="学院管理员未配置学院数据范围")
        college_statement = college_statement.where(College.id == principal.college_id)
    colleges = db.execute(college_statement.order_by(College.name, College.id)).scalars().all()
    college_ids = [college.id for college in colleges]
    if not college_ids:
        return {"scope": "college" if principal.role == "college_admin" else "university", "items": []}

    majors = db.execute(
        select(Major)
        .where(Major.college_id.in_(college_ids), Major.status == "active")
        .order_by(Major.college_id, Major.name, Major.id)
    ).scalars().all()
    major_ids = [major.id for major in majors]

    student_counts = {}
    if major_ids:
        student_counts = {
            major_id: count
            for major_id, count in db.execute(
                select(StudentAcademicProfile.major_id, func.count(StudentAcademicProfile.id))
                .where(StudentAcademicProfile.major_id.in_(major_ids), StudentAcademicProfile.status == "active")
                .group_by(StudentAcademicProfile.major_id)
            ).all()
        }

    course_rows = []
    if major_ids:
        course_rows = db.execute(
            select(MajorCourse.major_id, Course)
            .join(Course, Course.id == MajorCourse.course_id)
            .where(MajorCourse.major_id.in_(major_ids), Course.status == "active")
            .order_by(MajorCourse.major_id, Course.code, Course.id)
        ).all()
    course_ids = list({course.id for _major_id, course in course_rows})
    open_section_counts = {}
    if course_ids:
        open_section_counts = {
            course_id: count
            for course_id, count in db.execute(
                select(TeachingSection.course_id, func.count(TeachingSection.id))
                .where(TeachingSection.course_id.in_(course_ids), TeachingSection.status == "open")
                .group_by(TeachingSection.course_id)
            ).all()
        }

    college_items = {
        college.id: {
            "id": college.id,
            "code": college.code,
            "name": college.name,
            "student_count": 0,
            "major_count": 0,
            "majors": [],
        }
        for college in colleges
    }
    major_items = {}
    for major in majors:
        item = {
            "id": major.id,
            "code": major.code,
            "name": major.name,
            "student_count": int(student_counts.get(major.id, 0)),
            "course_count": 0,
            "courses": [],
        }
        major_items[major.id] = item
        college_items[major.college_id]["majors"].append(item)

    for major_id, course in course_rows:
        major_item = major_items[major_id]
        major_item["courses"].append(
            {
                "id": course.id,
                "code": course.code,
                "name": course.name,
                "credits": float(course.credits),
                "hours": course.hours,
                "course_type": course.course_type,
                "open_section_count": int(open_section_counts.get(course.id, 0)),
            }
        )
        major_item["course_count"] += 1

    for college_item in college_items.values():
        college_item["major_count"] = len(college_item["majors"])
        college_item["student_count"] = sum(major["student_count"] for major in college_item["majors"])

    return {
        "scope": "college" if principal.role == "college_admin" else "university",
        "items": list(college_items.values()),
    }
