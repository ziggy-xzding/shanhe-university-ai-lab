"""高校模块统一的数据范围校验。"""

from fastapi import HTTPException, status
from sqlalchemy import select

from Model.university_tables import CourseEnrollment, StudentAcademicProfile
from Service.auth_service import AuthPrincipal


FULL_TEACHING_SCOPE_ROLES = {"admin", "academic_admin"}
COLLEGE_SCOPE_ROLES = {"college_admin", "archive_admin"}


def _forbidden() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="当前身份无权访问该资源",
    )


def assert_college_scope(db, principal: AuthPrincipal, college_id: int) -> None:
    if principal.role in FULL_TEACHING_SCOPE_ROLES:
        return
    if principal.role in COLLEGE_SCOPE_ROLES and principal.college_id == college_id:
        return
    _forbidden()


def assert_student_scope(db, principal: AuthPrincipal, student_no: str) -> None:
    if principal.role in FULL_TEACHING_SCOPE_ROLES:
        return
    if principal.role == "student" and principal.subject_id == student_no:
        return

    profile = db.execute(
        select(StudentAcademicProfile).where(
            StudentAcademicProfile.student_no == student_no
        )
    ).scalar_one_or_none()
    if (
        profile
        and principal.role in COLLEGE_SCOPE_ROLES
        and principal.college_id == profile.college_id
    ):
        return
    _forbidden()


def assert_section_scope(db, principal: AuthPrincipal, section) -> None:
    if principal.role in FULL_TEACHING_SCOPE_ROLES:
        return
    if principal.role == "teacher" and principal.teacher_id == section.teacher_id:
        return
    if principal.role == "student":
        enrollment = db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.student_no == principal.subject_id,
                CourseEnrollment.teaching_section_id == section.id,
                CourseEnrollment.status == "enrolled",
            )
        ).scalar_one_or_none()
        if enrollment:
            return
    _forbidden()
