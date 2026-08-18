"""校园助手的本地、按身份范围查询；不存储聊天原文。"""

import re

from sqlalchemy import func, select

from Model.Student_score_table import Score
from Model.archive_tables import ArchiveDocument
from Model.complaint_tables import ComplaintTicket
from Model.risk_alert_tables import RiskAlert
from Model.student_affairs_tables import (
    CampusAnnouncement,
    DormAssignment,
    GraduateDestination,
    StudentAidApplication,
    StudentLeave,
    StudentRewardPunishment,
)
from Model.student_table import Student
from Model.university_tables import AcademicTerm, Course, CourseEnrollment, CourseGrade, StudentAcademicProfile, TeachingSection
from Service.auth_service import AuthPrincipal


def _term_request(message: str) -> tuple[int, int, str] | None:
    """识别“大二上/大二上学期”等自然表达，返回年级、学期和原文。"""
    match = re.search(r"大([一二三四1-4])\s*([上下])(?:学期)?", message)
    if not match:
        return None
    year_token = match.group(1)
    year = {"一": 1, "二": 2, "三": 3, "四": 4}.get(year_token) or int(year_token)
    semester = 1 if match.group(2) == "上" else 2
    return year, semester, match.group(0)


def _student_transcript_query(db, student_no: str, message: str) -> dict | None:
    rows = db.execute(
        select(CourseGrade, TeachingSection, Course, AcademicTerm)
        .join(TeachingSection, TeachingSection.id == CourseGrade.teaching_section_id)
        .join(Course, Course.id == TeachingSection.course_id)
        .join(AcademicTerm, AcademicTerm.id == TeachingSection.academic_term_id)
        .where(CourseGrade.student_no == student_no, CourseGrade.status == "approved")
        .order_by(AcademicTerm.starts_at, Course.code)
    ).all()
    if not rows:
        return None
    terms = []
    seen = set()
    for _grade, _section, _course, term in rows:
        if term.code not in seen:
            seen.add(term.code)
            terms.append(term)
    requested = _term_request(message)
    selected_term = None
    if requested:
        year, semester, _label = requested
        index = (year - 1) * 2 + (semester - 1)
        if index < len(terms):
            selected_term = terms[index]
    selected_rows = [row for row in rows if selected_term is None or row[3].code == selected_term.code]
    if requested and selected_term is None:
        return {
            "answer": f"我识别到你查询的是{requested[2]}，但当前成绩单没有对应学期记录。",
            "data": {"term_query": requested[2], "terms": []},
        }
    return {
        "answer": f"已识别“{requested[2]}”对应的学期并查询成绩。" if requested else "已为你查询本人可见的成绩记录。",
        "data": {
            "term_query": requested[2] if requested else None,
            "term_name": selected_term.name if selected_term else None,
            "courses": [
                {
                    "term_name": term.name,
                    "course_name": course.name,
                    "course_type": course.course_type,
                    "credits": float(course.credits),
                    "score": float(grade.score) if grade.score is not None else None,
                    "grade_label": grade.grade_label,
                    "grade_point": grade.grade_point,
                }
                for grade, _section, course, term in selected_rows
            ],
            "terms": [{"code": term.code, "name": term.name} for term in terms],
        },
    }


def answer_campus_query(db, principal: AuthPrincipal, message: str) -> dict:
    if principal.role == "student" and any(word in message for word in ("课表", "选课", "课程安排")):
        rows = db.execute(
            select(CourseEnrollment, TeachingSection, Course, AcademicTerm)
            .join(TeachingSection, TeachingSection.id == CourseEnrollment.teaching_section_id)
            .join(Course, Course.id == TeachingSection.course_id)
            .join(AcademicTerm, AcademicTerm.id == TeachingSection.academic_term_id)
            .where(
                CourseEnrollment.student_no == principal.subject_id,
                CourseEnrollment.status == "enrolled",
            )
            .order_by(AcademicTerm.starts_at, Course.code)
        ).all()
        return {
            "answer": "已为你查询本人当前已选课程与课表。",
            "data": {
                "schedule": [
                    {
                        "course_code": course.code,
                        "course_name": course.name,
                        "term_name": term.name,
                        "timetable": section.timetable_json,
                    }
                    for _enrollment, section, course, term in rows
                ]
            },
        }
    if principal.role == "student" and any(word in message for word in ("请假", "假条")):
        rows = db.execute(
            select(StudentLeave)
            .where(StudentLeave.student_no == principal.subject_id)
            .order_by(StudentLeave.created_at.desc(), StudentLeave.id.desc())
        ).scalars().all()
        return {
            "answer": "已为你查询本人请假申请状态。",
            "data": {
                "leaves": [
                    {
                        "starts_on": item.starts_on.isoformat(),
                        "ends_on": item.ends_on.isoformat(),
                        "status": item.status,
                    }
                    for item in rows
                ]
            },
        }
    if principal.role == "student" and any(word in message for word in ("资助", "助学", "奖学金")):
        rows = db.execute(
            select(StudentAidApplication)
            .where(StudentAidApplication.student_no == principal.subject_id)
            .order_by(StudentAidApplication.created_at.desc(), StudentAidApplication.id.desc())
        ).scalars().all()
        return {
            "answer": "已为你查询本人资助申请状态。",
            "data": {
                "aid_applications": [
                    {"aid_type": item.aid_type, "status": item.status}
                    for item in rows
                ]
            },
        }
    if principal.role == "student" and any(word in message for word in ("宿舍", "寝室")):
        dorm = db.execute(
            select(DormAssignment).where(DormAssignment.student_no == principal.subject_id)
        ).scalar_one_or_none()
        return {
            "answer": "已为你查询本人宿舍安排。",
            "data": {
                "dorm": None if dorm is None else {
                    "building": dorm.building,
                    "room_no": dorm.room_no,
                    "bed_no": dorm.bed_no,
                }
            },
        }
    if principal.role == "student" and any(word in message for word in ("奖惩", "处分", "表彰")):
        records = db.execute(
            select(StudentRewardPunishment)
            .where(StudentRewardPunishment.student_no == principal.subject_id)
            .order_by(StudentRewardPunishment.recorded_at.desc(), StudentRewardPunishment.id.desc())
        ).scalars().all()
        return {
            "answer": "已为你查询本人奖惩记录。",
            "data": {
                "reward_punishments": [
                    {
                        "record_type": record.record_type,
                        "title": record.title,
                        "recorded_at": record.recorded_at,
                    }
                    for record in records
                ]
            },
        }
    if principal.role == "student" and any(word in message for word in ("毕业去向", "就业去向", "升学去向")):
        destination = db.execute(
            select(GraduateDestination).where(
                GraduateDestination.student_no == principal.subject_id
            )
        ).scalar_one_or_none()
        return {
            "answer": "已为你查询本人毕业去向。",
            "data": {
                "graduate_destination": None if destination is None else {
                    "destination_type": destination.destination_type,
                    "organization": destination.organization,
                    "detail": destination.detail,
                }
            },
        }
    """从身份令牌确定查询范围，绝不接受客户端传入的主体编号。"""
    if principal.role == "student" and any(word in message for word in ("成绩", "分数", "绩点")):
        transcript = _student_transcript_query(db, principal.subject_id, message)
        if transcript:
            return transcript
        scores = list(db.execute(select(Score).where(Score.student_no == principal.subject_id, Score.is_deleted.is_(False)).order_by(Score.exam_seq)).scalars())
        return {"answer": "已为你查询本人可见的成绩记录。", "data": {"student_no": principal.subject_id, "scores": [{"exam_seq": score.exam_seq, "score": float(score.score)} for score in scores]}}
    if principal.role == "teacher" and any(word in message for word in ("课程", "教学班", "课表")):
        sections = list(
            db.execute(
                select(TeachingSection).where(TeachingSection.teacher_id == principal.teacher_id)
            ).scalars()
        )
        return {
            "answer": "已为你查询本人任教的教学班。",
            "data": {"teaching_section_ids": [section.id for section in sections]},
        }
    if principal.role == "counselor" and any(word in message for word in ("预警", "心理", "风险")):
        open_count = db.execute(
            select(func.count(RiskAlert.id)).where(
                RiskAlert.counselor_staff_no == principal.subject_id,
                RiskAlert.status == "open",
            )
        ).scalar_one()
        return {
            "answer": "已为你查询本人负责学生的待处置心理风险预警数量。",
            "data": {"open_risk_alert_count": open_count},
        }
    if principal.role == "archive_admin" and any(word in message for word in ("档案", "归档")):
        count = db.execute(
            select(func.count(ArchiveDocument.id)).where(
                ArchiveDocument.college_id == principal.college_id
            )
        ).scalar_one()
        return {
            "answer": "已按你的学院档案管理范围统计电子档案数量。",
            "data": {"archive_document_count": count},
        }
    if principal.role == "student_affairs" and any(
        word in message for word in ("待办", "请假", "资助", "投诉")
    ):
        pending_leave_count = db.execute(
            select(func.count(StudentLeave.id)).where(StudentLeave.status == "pending")
        ).scalar_one()
        pending_aid_count = db.execute(
            select(func.count(StudentAidApplication.id)).where(StudentAidApplication.status == "pending")
        ).scalar_one()
        open_complaint_count = db.execute(
            select(func.count(ComplaintTicket.id)).where(
                ComplaintTicket.status.in_(("submitted", "in_progress"))
            )
        ).scalar_one()
        return {
            "answer": "已按学生事务办理权限汇总待处理数量，未返回任何学生身份或投诉原文。",
            "data": {
                "pending_leave_count": pending_leave_count,
                "pending_aid_count": pending_aid_count,
                "open_complaint_count": open_complaint_count,
            },
        }
    if principal.role == "staff" and any(word in message for word in ("公告", "通知")):
        announcements = list(
            db.execute(
                select(CampusAnnouncement)
                .where(
                    CampusAnnouncement.status == "published",
                    CampusAnnouncement.audience.in_(("all", "staff")),
                )
                .order_by(CampusAnnouncement.published_at.desc(), CampusAnnouncement.id.desc())
                .limit(5)
            ).scalars()
        )
        return {
            "answer": "已为你查询教职工可见的最新公告，仅返回公告标题和发布时间。",
            "data": {
                "announcements": [
                    {"title": item.title, "published_at": item.published_at}
                    for item in announcements
                ]
            },
        }
    if principal.role in {"admin", "academic_admin", "college_admin"} and any(
        word in message for word in ("学生数", "学生数量", "在校生")
    ):
        statement = select(func.count(StudentAcademicProfile.id))
        if principal.role == "college_admin":
            statement = statement.where(StudentAcademicProfile.college_id == principal.college_id)
        return {
            "answer": "已按你的管理权限统计在校学生数量。",
            "data": {"student_count": db.execute(statement).scalar_one()},
        }
    return {
        "answer": "我可以在你的权限范围内查询校务数据，例如成绩、任课教学班、心理预警或学生数量。",
        "data": {},
    }
