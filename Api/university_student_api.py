"""高校学生档案分页查询接口。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.class_table import Class
from Model.student_table import Student
from Model.university_tables import College, Major, StudentAcademicProfile
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles
from Service.data_scope import assert_college_scope


university_student_router = APIRouter(prefix="/api/university/students", tags=["高校学生档案"])
require_student_manager = require_roles("admin", "college_admin")


class AcademicProfileUpdateRequest(BaseModel):
    status: Literal["active", "suspended", "withdrawn", "graduated", "inactive"] | None = None
    phone: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def require_a_change(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一项需要更新的学籍信息")
        return self


@university_student_router.get("")
def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, min_length=1, max_length=50),
    principal: AuthPrincipal = Depends(require_student_manager),
    db: Session = Depends(get_db),
):
    filters = [Student.is_deleted.is_(False)]
    if principal.role == "college_admin":
        if principal.college_id is None:
            return {"page": page, "page_size": page_size, "total": 0, "items": []}
        filters.append(StudentAcademicProfile.college_id == principal.college_id)
    if keyword:
        escaped = f"%{keyword.strip()}%"
        filters.append((Student.student_no.like(escaped)) | (Student.name.like(escaped)))

    total = db.execute(
        select(func.count(StudentAcademicProfile.id))
        .join(Student, Student.student_no == StudentAcademicProfile.student_no)
        .where(*filters)
    ).scalar_one()
    rows = db.execute(
        select(Student, StudentAcademicProfile, College, Major, Class)
        .join(StudentAcademicProfile, StudentAcademicProfile.student_no == Student.student_no)
        .join(College, College.id == StudentAcademicProfile.college_id)
        .join(Major, Major.id == StudentAcademicProfile.major_id)
        .outerjoin(Class, Class.id == StudentAcademicProfile.class_id)
        .where(*filters)
        .order_by(Student.student_no)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "student_no": student.student_no,
                "name": student.name,
                "college_code": college.code,
                "college_name": college.name,
                "major_code": major.code,
                "major_name": major.name,
                "class_no": classroom.class_no if classroom else None,
                "class_name": classroom.name if classroom else None,
                "grade": profile.grade,
                "status": profile.status,
                "phone": profile.phone,
            }
            for student, profile, college, major, classroom in rows
        ],
    }


@university_student_router.patch("/{student_no}/academic-profile")
def update_student_academic_profile(
    student_no: str,
    payload: AcademicProfileUpdateRequest,
    principal: AuthPrincipal = Depends(require_student_manager),
    db: Session = Depends(get_db),
):
    profile = db.execute(
        select(StudentAcademicProfile).where(StudentAcademicProfile.student_no == student_no)
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="学生学籍档案不存在")
    assert_college_scope(db, principal, profile.college_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes:
        profile.status = changes["status"]
    if "phone" in changes:
        profile.phone = changes["phone"].strip() if changes["phone"] else None
    db.commit()
    return {
        "student_no": profile.student_no,
        "college_id": profile.college_id,
        "major_id": profile.major_id,
        "class_id": profile.class_id,
        "grade": profile.grade,
        "status": profile.status,
        "phone": profile.phone,
    }
