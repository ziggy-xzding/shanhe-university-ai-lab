"""高校课程、教学班和选课接口。"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Schema.university_schema import EnrollmentResponse
from Service.academic_service import drop_student_enrollment, enroll_student
from Service.auth_service import AuthPrincipal
from Service.authorization import get_current_principal, require_roles
from Model.university_tables import AcademicTerm, College, Course, CourseEnrollment, CourseGrade, Major, MajorCourse, StudentAcademicProfile, TeachingSection
from Model.student_table import Student
from Model.teacher_table import teacher_table
from Service.data_scope import assert_college_scope, assert_section_scope
from Service.gpa_service import GPA_RULE_NOTE, grade_point_for_score, weighted_gpa


university_academic_router = APIRouter(prefix="/api/university", tags=["高校教学管理"])
require_student = require_roles("student")
require_academic_admin = require_roles("admin", "academic_admin", "teacher")
require_curriculum_manager = require_roles("admin", "academic_admin", "college_admin", "teacher")
require_system_admin = require_roles("admin")
require_teacher = require_roles("teacher")


class CourseCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    credits: Decimal = Field(ge=0, le=30)
    hours: int = Field(ge=0, le=500)
    course_type: str = Field(default="必修课", min_length=1, max_length=20)


class CourseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    credits: Decimal | None = Field(default=None, ge=0, le=30)
    hours: int | None = Field(default=None, ge=0, le=500)
    course_type: str | None = Field(default=None, min_length=1, max_length=20)
    status: Literal["active", "inactive"] | None = None


class AcademicTermCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    starts_at: datetime
    ends_at: datetime


class MajorCourseCreateRequest(BaseModel):
    course_id: int = Field(gt=0)
    is_required: bool = True


class CollegeCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)


class MajorCreateRequest(BaseModel):
    college_id: int = Field(gt=0)
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)


class GradeSubmitRequest(BaseModel):
    student_no: str = Field(min_length=1, max_length=20)
    score: int = Field(ge=0, le=100)


class TeachingSectionCreateRequest(BaseModel):
    course_id: int = Field(gt=0)
    academic_term_id: int = Field(gt=0)
    teacher_id: int | None = Field(default=None, gt=0)
    capacity: int = Field(ge=1, le=500)
    selection_open_at: datetime
    selection_close_at: datetime
    timetable: list[dict] = Field(default_factory=list)

    @classmethod
    def _validate_selection_window(cls, value):
        if value.selection_close_at <= value.selection_open_at:
            raise ValueError("选课结束时间必须晚于开始时间")
        return value


class TeachingSectionUpdateRequest(BaseModel):
    capacity: int | None = Field(default=None, ge=1, le=500)
    selection_open_at: datetime | None = None
    selection_close_at: datetime | None = None
    timetable: list[dict] | None = None
    status: Literal["open", "closed", "finished"] | None = None


def _grade_point(score: int) -> str:
    return f"{grade_point_for_score(score):.2f}"


@university_academic_router.post(
    "/sections/{section_id}/enrollments",
    response_model=EnrollmentResponse,
    status_code=201,
)
def create_enrollment(
    section_id: int,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    enrollment = enroll_student(db, principal.subject_id, section_id)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@university_academic_router.delete("/sections/{section_id}/enrollments/me")
def drop_my_enrollment(
    section_id: int,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    enrollment = drop_student_enrollment(db, principal.subject_id, section_id)
    db.commit()
    return {"id": enrollment.id, "teaching_section_id": enrollment.teaching_section_id, "status": enrollment.status}


@university_academic_router.get("/me/transcript")
def get_my_transcript(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    rows = list(
        db.execute(
            select(CourseGrade, TeachingSection, Course, AcademicTerm)
            .join(TeachingSection, CourseGrade.teaching_section_id == TeachingSection.id)
            .join(Course, TeachingSection.course_id == Course.id)
            .join(AcademicTerm, TeachingSection.academic_term_id == AcademicTerm.id)
            .where(
                CourseGrade.student_no == principal.subject_id,
                CourseGrade.status == "approved",
            )
            .order_by(AcademicTerm.starts_at, Course.code)
        ).all()
    )
    items = []
    grouped = {}
    for grade, _section, course, term in rows:
        item = {
            "term_code": term.code,
            "term_name": term.name,
            "course_code": course.code,
            "course_name": course.name,
            "course_type": course.course_type,
            "credits": float(course.credits),
            "score": float(grade.score) if grade.score is not None else None,
            "grade_label": grade.grade_label,
            "grade_display": grade.grade_label or (float(grade.score) if grade.score is not None else "-") ,
            "grade_point": grade.grade_point,
        }
        items.append(item)
        grouped.setdefault(term.code, {"term_code": term.code, "term_name": term.name, "items": []})["items"].append(item)
    terms = []
    level_names = ("一", "二", "三", "四")
    for index, term in enumerate(grouped.values()):
        level = min(index // 2, 3)
        semester = "上" if index % 2 == 0 else "下"
        term["term_alias"] = f"大{level_names[level]}{semester}学期"
        term["total_credits"] = round(sum(item["credits"] for item in term["items"]), 1)
        term["gpa"] = weighted_gpa(term["items"])
        term["gpa"] = float(term["gpa"]) if term["gpa"] is not None else None
        terms.append(term)
    total_credits = round(sum(item["credits"] for item in items), 1)
    gpa = weighted_gpa(items)
    return {
        "student_no": principal.subject_id,
        "gpa": float(gpa) if gpa is not None else None,
        "total_credits": total_credits,
        "terms": terms,
        "items": items,
        "gpa_rule": {"note": GPA_RULE_NOTE},
    }


@university_academic_router.get("/me/enrollments")
def list_my_enrollments(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    rows = list(
        db.execute(
            select(CourseEnrollment, TeachingSection, Course)
            .join(TeachingSection, CourseEnrollment.teaching_section_id == TeachingSection.id)
            .join(Course, TeachingSection.course_id == Course.id)
            .where(
                CourseEnrollment.student_no == principal.subject_id,
                CourseEnrollment.status == "enrolled",
            )
            .order_by(Course.code)
        ).all()
    )
    return {
        "items": [
            {
                "enrollment_id": enrollment.id,
                "section_id": section.id,
                "course_code": course.code,
                "course_name": course.name,
                "credits": float(course.credits),
                "timetable": section.timetable_json,
            }
            for enrollment, section, course in rows
        ]
    }


@university_academic_router.get("/sections")
def list_open_teaching_sections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    management: bool = False,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    if management and principal.role not in {"admin", "academic_admin", "college_admin", "teacher"}:
        raise HTTPException(status_code=403, detail="无权管理教学班")
    statement = select(TeachingSection, Course).join(Course, TeachingSection.course_id == Course.id)
    if not management:
        now = datetime.now()
        statement = statement.where(
            TeachingSection.status == "open",
            TeachingSection.selection_open_at <= now,
            TeachingSection.selection_close_at >= now,
        )
        if principal.role == "student":
            profile = db.execute(
                select(StudentAcademicProfile).where(
                    StudentAcademicProfile.student_no == principal.subject_id
                )
            ).scalar_one_or_none()
            if profile is not None:
                statement = statement.join(
                    MajorCourse,
                    MajorCourse.course_id == TeachingSection.course_id,
                ).where(MajorCourse.major_id == profile.major_id)
    rows = list(db.execute(statement.order_by(Course.code, TeachingSection.id).offset((page - 1) * page_size).limit(page_size)).all())
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "section_id": section.id,
                "course_code": course.code,
                "course_name": course.name,
                "credits": float(course.credits),
                "capacity": section.capacity,
                "enrolled_count": section.enrolled_count,
                "selection_open_at": section.selection_open_at,
                "selection_close_at": section.selection_close_at,
                "timetable": section.timetable_json,
            }
            for section, course in rows
        ],
    }


@university_academic_router.get("/me/teaching-sections")
def list_my_teaching_sections(
    principal: AuthPrincipal = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(TeachingSection, Course, AcademicTerm)
        .join(Course, Course.id == TeachingSection.course_id)
        .join(AcademicTerm, AcademicTerm.id == TeachingSection.academic_term_id)
        .where(TeachingSection.teacher_id == principal.teacher_id)
        .order_by(AcademicTerm.starts_at.desc(), Course.code, TeachingSection.id)
    ).all()
    return {
        "items": [
            {
                "section_id": section.id,
                "course_code": course.code,
                "course_name": course.name,
                "term_name": term.name,
            }
            for section, course, term in rows
        ]
    }


@university_academic_router.get("/courses")
def list_course_catalog(
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    statement = select(Course)
    if not include_inactive or principal.role == "college_admin":
        statement = statement.where(Course.status == "active")
    total = db.execute(select(func.count()).select_from(statement.subquery())).scalar_one()
    rows = db.execute(
        statement.order_by(Course.code).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {"id": course.id, "code": course.code, "name": course.name, "credits": float(course.credits), "hours": course.hours, "course_type": course.course_type, "status": course.status}
            for course in rows
        ]
    }


@university_academic_router.get("/colleges")
def list_colleges(
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    statement = select(College).where(College.status == "active")
    if principal.role == "college_admin":
        if principal.college_id is None:
            return {"items": []}
        statement = statement.where(College.id == principal.college_id)
    colleges = db.execute(statement.order_by(College.code)).scalars().all()
    return {"items": [{"id": college.id, "code": college.code, "name": college.name} for college in colleges]}


@university_academic_router.post("/colleges", status_code=201)
def create_college(
    payload: CollegeCreateRequest,
    principal: AuthPrincipal = Depends(require_system_admin),
    db: Session = Depends(get_db),
):
    code = payload.code.strip().upper()
    if db.execute(select(College).where(College.code == code)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="学院代码已存在")
    college = College(code=code, name=payload.name.strip(), status="active")
    db.add(college)
    db.commit()
    db.refresh(college)
    return {"id": college.id, "code": college.code, "name": college.name, "status": college.status}


@university_academic_router.get("/majors")
def list_majors(
    college_id: int | None = Query(default=None, gt=0),
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    if principal.role == "college_admin":
        if principal.college_id is None:
            return {"items": []}
        if college_id is not None and college_id != principal.college_id:
            assert_college_scope(db, principal, college_id)
        college_id = principal.college_id
    statement = select(Major, College).join(College, College.id == Major.college_id)
    if college_id is not None:
        statement = statement.where(Major.college_id == college_id)
    rows = db.execute(statement.where(Major.status == "active").order_by(College.code, Major.code)).all()
    return {
        "items": [
            {"id": major.id, "college_id": college.id, "college_name": college.name, "code": major.code, "name": major.name}
            for major, college in rows
        ]
    }


@university_academic_router.post("/majors", status_code=201)
def create_major(
    payload: MajorCreateRequest,
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    college = db.get(College, payload.college_id)
    if not college or college.status != "active":
        raise HTTPException(status_code=404, detail="学院不存在或已停用")
    assert_college_scope(db, principal, college.id)
    code = payload.code.strip().upper()
    if db.execute(select(Major).where(Major.college_id == college.id, Major.code == code)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该学院专业代码已存在")
    major = Major(college_id=college.id, code=code, name=payload.name.strip(), status="active")
    db.add(major)
    db.commit()
    db.refresh(major)
    return {"id": major.id, "college_id": major.college_id, "code": major.code, "name": major.name, "status": major.status}


@university_academic_router.get("/majors/{major_id}/courses")
def list_major_curriculum(
    major_id: int,
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    major = db.get(Major, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    assert_college_scope(db, principal, major.college_id)
    rows = db.execute(
        select(MajorCourse, Course)
        .join(Course, Course.id == MajorCourse.course_id)
        .where(MajorCourse.major_id == major_id)
        .order_by(Course.code)
    ).all()
    return {
        "items": [
            {
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "credits": float(course.credits),
                "course_type": course.course_type,
                "hours": course.hours,
                "is_required": relation.is_required,
            }
            for relation, course in rows
        ]
    }


@university_academic_router.get("/sections/{section_id}/roster")
def list_section_roster_for_grade_entry(
    section_id: int,
    principal: AuthPrincipal = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    section = db.execute(
        select(TeachingSection).where(TeachingSection.id == section_id)
    ).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="教学班不存在")
    assert_section_scope(db, principal, section)
    rows = db.execute(
        select(CourseEnrollment, Student, CourseGrade)
        .join(Student, Student.student_no == CourseEnrollment.student_no)
        .outerjoin(
            CourseGrade,
            and_(
                CourseGrade.teaching_section_id == CourseEnrollment.teaching_section_id,
                CourseGrade.student_no == CourseEnrollment.student_no,
            ),
        )
        .where(
            CourseEnrollment.teaching_section_id == section_id,
            CourseEnrollment.status == "enrolled",
            Student.is_deleted.is_(False),
        )
        .order_by(Student.student_no)
    ).all()
    return {
        "items": [
            {
                "student_no": student.student_no,
                "name": student.name,
                "grade_id": grade.id if grade else None,
                "score": grade.score if grade else None,
                "grade_status": grade.status if grade else None,
            }
            for _enrollment, student, grade in rows
        ]
    }


@university_academic_router.post("/sections", status_code=201)
def create_teaching_section(
    payload: TeachingSectionCreateRequest,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    if not db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="课程不存在")
    if not db.execute(select(AcademicTerm).where(AcademicTerm.id == payload.academic_term_id)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="学期不存在")
    if principal.role == "teacher" and payload.teacher_id not in {None, principal.teacher_id}:
        raise HTTPException(status_code=403, detail="教师只能发布自己的教学班")
    teacher_id = principal.teacher_id if principal.role == "teacher" else payload.teacher_id
    if teacher_id is not None and not db.execute(
        select(teacher_table.tid).where(teacher_table.tid == teacher_id)
    ).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="授课教师不存在")
    if payload.selection_close_at <= payload.selection_open_at:
        raise HTTPException(status_code=422, detail="选课结束时间必须晚于开始时间")
    section = TeachingSection(
        course_id=payload.course_id,
        academic_term_id=payload.academic_term_id,
        teacher_id=teacher_id,
        capacity=payload.capacity,
        enrolled_count=0,
        selection_open_at=payload.selection_open_at,
        selection_close_at=payload.selection_close_at,
        timetable_json=payload.timetable,
        status="open",
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return {
        "id": section.id,
        "course_id": section.course_id,
        "academic_term_id": section.academic_term_id,
        "teacher_id": section.teacher_id,
        "capacity": section.capacity,
        "selection_open_at": section.selection_open_at,
        "selection_close_at": section.selection_close_at,
        "timetable": section.timetable_json,
    }


@university_academic_router.put("/sections/{section_id}")
def update_teaching_section(
    section_id: int,
    payload: TeachingSectionUpdateRequest,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    section = db.get(TeachingSection, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="教学班不存在")
    if principal.role == "teacher":
        assert_section_scope(db, principal, section)
    values = payload.model_dump(exclude_none=True)
    if "selection_open_at" in values and "selection_close_at" in values:
        if values["selection_close_at"] <= values["selection_open_at"]:
            raise HTTPException(status_code=422, detail="选课结束时间必须晚于开始时间")
    for field, value in values.items():
        setattr(section, "timetable_json" if field == "timetable" else field, value)
    db.commit()
    db.refresh(section)
    return {"id": section.id, "status": section.status, "capacity": section.capacity, "timetable": section.timetable_json}


@university_academic_router.delete("/sections/{section_id}", status_code=204)
def close_teaching_section(
    section_id: int,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    section = db.get(TeachingSection, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="教学班不存在")
    if principal.role == "teacher":
        assert_section_scope(db, principal, section)
    section.status = "closed"
    db.commit()


@university_academic_router.post("/courses", status_code=201)
def create_course(
    payload: CourseCreateRequest,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    code = payload.code.strip().upper()
    if db.execute(select(Course).where(Course.code == code)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="课程代码已存在")
    course = Course(
        code=code,
        name=payload.name.strip(),
        credits=payload.credits,
        hours=payload.hours,
        course_type=payload.course_type.strip(),
        status="active",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "credits": float(course.credits),
        "hours": course.hours,
        "course_type": course.course_type,
        "status": course.status,
    }


@university_academic_router.put("/courses/{course_id}")
def update_course(
    course_id: int,
    payload: CourseUpdateRequest,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(course, field, value.strip() if field == "name" else value)
    db.commit()
    db.refresh(course)
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "credits": float(course.credits),
        "hours": course.hours,
        "course_type": course.course_type,
        "status": course.status,
    }


@university_academic_router.post("/terms", status_code=201)
def create_academic_term(
    payload: AcademicTermCreateRequest,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="学期结束时间必须晚于开始时间")
    code = payload.code.strip()
    if db.execute(select(AcademicTerm).where(AcademicTerm.code == code)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="学期代码已存在")
    term = AcademicTerm(
        code=code,
        name=payload.name.strip(),
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status="active",
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return {"id": term.id, "code": term.code, "name": term.name, "status": term.status}


@university_academic_router.post("/majors/{major_id}/courses", status_code=201)
def add_course_to_major(
    major_id: int,
    payload: MajorCourseCreateRequest,
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    major = db.execute(select(Major).where(Major.id == major_id)).scalar_one_or_none()
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    assert_college_scope(db, principal, major.college_id)
    if not db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="课程不存在")
    relation = db.execute(
        select(MajorCourse).where(
            MajorCourse.major_id == major_id,
            MajorCourse.course_id == payload.course_id,
        )
    ).scalar_one_or_none()
    if relation:
        relation.is_required = payload.is_required
    else:
        relation = MajorCourse(
            major_id=major_id,
            course_id=payload.course_id,
            is_required=payload.is_required,
        )
        db.add(relation)
    db.commit()
    return {
        "major_id": relation.major_id,
        "course_id": relation.course_id,
        "is_required": relation.is_required,
    }


@university_academic_router.delete("/majors/{major_id}/courses/{course_id}", status_code=204)
def remove_course_from_major(
    major_id: int,
    course_id: int,
    principal: AuthPrincipal = Depends(require_curriculum_manager),
    db: Session = Depends(get_db),
):
    relation = db.execute(
        select(MajorCourse).where(
            MajorCourse.major_id == major_id,
            MajorCourse.course_id == course_id,
        )
    ).scalar_one_or_none()
    if not relation:
        raise HTTPException(status_code=404, detail="专业课程关系不存在")
    major = db.get(Major, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="专业不存在")
    assert_college_scope(db, principal, major.college_id)
    db.delete(relation)
    db.commit()
    return Response(status_code=204)


@university_academic_router.post("/sections/{section_id}/grades", status_code=201)
def submit_grade(
    section_id: int,
    payload: GradeSubmitRequest,
    principal: AuthPrincipal = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    section = db.execute(
        select(TeachingSection).where(TeachingSection.id == section_id)
    ).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="教学班不存在")
    assert_section_scope(db, principal, section)
    enrollment = db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.teaching_section_id == section_id,
            CourseEnrollment.student_no == payload.student_no,
            CourseEnrollment.status == "enrolled",
        )
    ).scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=422, detail="学生未选该教学班")
    grade = db.execute(
        select(CourseGrade).where(
            CourseGrade.teaching_section_id == section_id,
            CourseGrade.student_no == payload.student_no,
        )
    ).scalar_one_or_none()
    if grade and grade.status == "approved":
        raise HTTPException(status_code=409, detail="已审核成绩不能由教师修改")
    if not grade:
        grade = CourseGrade(
            student_no=payload.student_no,
            teaching_section_id=section_id,
            score=payload.score,
            grade_point=_grade_point(payload.score),
            status="submitted",
        )
        db.add(grade)
    else:
        grade.score = payload.score
        grade.grade_point = _grade_point(payload.score)
        grade.status = "submitted"
    db.commit()
    db.refresh(grade)
    return {
        "id": grade.id,
        "student_no": grade.student_no,
        "teaching_section_id": grade.teaching_section_id,
        "score": grade.score,
        "grade_point": grade.grade_point,
        "status": grade.status,
    }


@university_academic_router.post("/grades/{grade_id}/approve")
def approve_grade(
    grade_id: int,
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    grade = db.execute(
        select(CourseGrade).where(CourseGrade.id == grade_id)
    ).scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="成绩记录不存在")
    if grade.status != "submitted":
        raise HTTPException(status_code=409, detail="仅可审核待审核成绩")
    grade.status = "approved"
    grade.approved_at = datetime.now()
    db.commit()
    return {"id": grade.id, "status": grade.status, "approved_at": grade.approved_at}


@university_academic_router.get("/grades")
def list_grades_for_approval(
    status_filter: str = Query("submitted", alias="status", pattern="^(submitted|approved)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_academic_admin),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(CourseGrade, Student, Course)
        .join(Student, Student.student_no == CourseGrade.student_no)
        .join(TeachingSection, TeachingSection.id == CourseGrade.teaching_section_id)
        .join(Course, Course.id == TeachingSection.course_id)
        .where(CourseGrade.status == status_filter, Student.is_deleted.is_(False))
        .order_by(Course.code, Student.student_no, CourseGrade.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "grade_id": grade.id,
                "student_no": student.student_no,
                "student_name": student.name,
                "course_code": course.code,
                "course_name": course.name,
                "score": grade.score,
                "status": grade.status,
            }
            for grade, student, course in rows
        ],
    }
