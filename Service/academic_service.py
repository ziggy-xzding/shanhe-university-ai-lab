"""教学班和选课事务规则。"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select

from Model.student_table import Student
from Model.university_tables import CourseEnrollment, MajorCourse, StudentAcademicProfile, TeachingSection


def _has_timetable_conflict(left_slots: list[dict], right_slots: list[dict]) -> bool:
    for left in left_slots:
        for right in right_slots:
            if left.get("day") != right.get("day"):
                continue
            if left.get("start", "") < right.get("end", "") and right.get("start", "") < left.get("end", ""):
                return True
    return False


def enroll_student(
    db,
    student_no: str,
    teaching_section_id: int,
    now: datetime | None = None,
) -> CourseEnrollment:
    """为学生选课；调用方负责提交事务。"""
    now = now or datetime.now()
    student = db.execute(
        select(Student).where(Student.student_no == student_no, Student.is_deleted.is_not(True))
    ).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")
    profile = db.execute(
        select(StudentAcademicProfile).where(StudentAcademicProfile.student_no == student_no)
    ).scalar_one_or_none()
    if profile is not None and profile.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前学籍状态不能选课")
    section = db.execute(
        select(TeachingSection)
        .where(TeachingSection.id == teaching_section_id)
        .with_for_update()
    ).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教学班不存在")
    if profile is not None and not db.execute(
        select(MajorCourse).where(
            MajorCourse.major_id == profile.major_id,
            MajorCourse.course_id == section.course_id,
        )
    ).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该课程不在本人专业培养方案内",
        )
    if not section.selection_open_at <= now <= section.selection_close_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前不在选课时间内")
    if section.enrolled_count >= section.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="教学班人数已满")

    existing = db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.student_no == student_no,
            CourseEnrollment.teaching_section_id == teaching_section_id,
        )
    ).scalar_one_or_none()
    if existing and existing.status == "enrolled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已选该教学班")
    current_sections = db.execute(
        select(TeachingSection)
        .join(
            CourseEnrollment,
            CourseEnrollment.teaching_section_id == TeachingSection.id,
        )
        .where(
            CourseEnrollment.student_no == student_no,
            CourseEnrollment.status == "enrolled",
            TeachingSection.academic_term_id == section.academic_term_id,
        )
    ).scalars()
    if any(
        _has_timetable_conflict(section.timetable_json or [], current.timetable_json or [])
        for current in current_sections
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="课程时间冲突")
    if existing:
        existing.status = "enrolled"
        existing.enrolled_at = now
        existing.dropped_at = None
        enrollment = existing
    else:
        enrollment = CourseEnrollment(
            student_no=student_no,
            teaching_section_id=teaching_section_id,
            status="enrolled",
            enrolled_at=now,
        )
        db.add(enrollment)
    section.enrolled_count += 1
    db.flush()
    return enrollment


def drop_student_enrollment(
    db,
    student_no: str,
    teaching_section_id: int,
    now: datetime | None = None,
) -> CourseEnrollment:
    """学生在选课开放期内退选自己的教学班，并原子释放容量。"""
    now = now or datetime.now()
    section = db.execute(
        select(TeachingSection)
        .where(TeachingSection.id == teaching_section_id)
        .with_for_update()
    ).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教学班不存在")
    if not section.selection_open_at <= now <= section.selection_close_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前不在退选时间内")
    enrollment = db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.student_no == student_no,
            CourseEnrollment.teaching_section_id == teaching_section_id,
            CourseEnrollment.status == "enrolled",
        )
    ).scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到有效选课记录")
    enrollment.status = "dropped"
    enrollment.dropped_at = now
    section.enrolled_count = max(0, section.enrolled_count - 1)
    db.flush()
    return enrollment
