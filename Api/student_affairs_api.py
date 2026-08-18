"""学生事务：学生本人提交、事务人员办理。"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.risk_alert_tables import CounselorAssignment, RiskAlert, UnassignedRiskAlert
from Model.staff_account_table import StaffAccount
from Model.student_affairs_tables import CampusAnnouncement, DormAssignment, DormRoom, GraduateDestination, StudentAidApplication, StudentLeave, StudentRewardPunishment
from Model.student_table import Student
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles


student_affairs_router = APIRouter(prefix="/api/student-affairs", tags=["学生事务"])
require_student = require_roles("student")
require_leave_reviewer = require_roles("admin", "student_affairs")
require_announcement_publisher = require_roles("admin", "student_affairs")
require_dorm_manager = require_roles("admin", "student_affairs")
require_reward_manager = require_roles("admin", "student_affairs")
require_destination_manager = require_roles("admin", "student_affairs")


class LeaveCreateRequest(BaseModel):
    starts_on: date
    ends_on: date
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.ends_on < self.starts_on:
            raise ValueError("请假结束日期不能早于开始日期")
        return self


class LeaveReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    comment: str = Field(min_length=1, max_length=2000)


class AidApplicationCreateRequest(BaseModel):
    aid_type: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=2000)


class AidApplicationReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    audience: str = Field(default="all", pattern="^(all|student|staff)$")


class DormAssignmentRequest(BaseModel):
    building: str = Field(min_length=1, max_length=50)
    room_no: str = Field(min_length=1, max_length=30)
    bed_no: str | None = Field(default=None, max_length=20)


class DormSelectionRequest(BaseModel):
    room_id: int = Field(gt=0)
    bed_no: str = Field(min_length=1, max_length=20)


class RewardPunishmentCreateRequest(BaseModel):
    student_no: str = Field(min_length=1, max_length=20)
    record_type: str = Field(pattern="^(reward|punishment)$")
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = Field(default=None, max_length=5000)


class GraduateDestinationRequest(BaseModel):
    destination_type: str = Field(pattern="^(employment|further_study|entrepreneurship|other)$")
    organization: str | None = Field(default=None, max_length=200)
    detail: str | None = Field(default=None, max_length=5000)


class CounselorAssignmentRequest(BaseModel):
    counselor_staff_no: str = Field(min_length=1, max_length=20)


def _require_existing_student(db: Session, student_no: str) -> Student:
    student = db.execute(
        select(Student).where(
            Student.student_no == student_no,
            Student.is_deleted.is_not(True),
        )
    ).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


@student_affairs_router.get("/unassigned-risk-alerts")
def list_unassigned_risk_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_leave_reviewer),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(UnassignedRiskAlert)
        .where(UnassignedRiskAlert.status == "open")
        .order_by(UnassignedRiskAlert.created_at.desc(), UnassignedRiskAlert.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "student_no": item.student_no,
                "risk_level": item.risk_level,
                "trigger_summary": item.trigger_summary,
                "created_at": item.created_at,
            }
            for item in rows
        ],
    }


@student_affairs_router.put("/counselor-assignments/{student_no}")
def assign_counselor(
    student_no: str,
    payload: CounselorAssignmentRequest,
    principal: AuthPrincipal = Depends(require_leave_reviewer),
    db: Session = Depends(get_db),
):
    student = db.execute(
        select(Student).where(Student.student_no == student_no, Student.is_deleted.is_not(True))
    ).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    counselor = db.execute(
        select(StaffAccount).where(
            StaffAccount.staff_no == payload.counselor_staff_no.strip(),
            StaffAccount.role == "counselor",
            StaffAccount.status == "active",
        )
    ).scalar_one_or_none()
    if not counselor:
        raise HTTPException(status_code=422, detail="辅导员账号不存在、未启用或角色不匹配")
    assignment = db.execute(
        select(CounselorAssignment).where(CounselorAssignment.student_no == student_no)
    ).scalar_one_or_none()
    if not assignment:
        assignment = CounselorAssignment(student_no=student_no, counselor_staff_no=counselor.staff_no)
        db.add(assignment)
    else:
        assignment.counselor_staff_no = counselor.staff_no
    transferred_alerts = 0
    unassigned_alerts = db.execute(
        select(UnassignedRiskAlert).where(
            UnassignedRiskAlert.student_no == student_no,
            UnassignedRiskAlert.status == "open",
        )
    ).scalars().all()
    for unassigned_alert in unassigned_alerts:
        existing_alert = db.execute(
            select(RiskAlert).where(
                RiskAlert.student_no == student_no,
                RiskAlert.counselor_staff_no == counselor.staff_no,
                RiskAlert.status.in_(("open", "reviewed")),
            )
        ).scalar_one_or_none()
        if existing_alert is None:
            db.add(
                RiskAlert(
                    student_no=student_no,
                    counselor_staff_no=counselor.staff_no,
                    risk_level=unassigned_alert.risk_level,
                    status="open",
                    trigger_summary=unassigned_alert.trigger_summary,
                )
            )
            transferred_alerts += 1
        unassigned_alert.status = "assigned"
        unassigned_alert.assigned_at = datetime.now()
    db.commit()
    result = {
        "student_no": assignment.student_no,
        "counselor_staff_no": assignment.counselor_staff_no,
    }
    if transferred_alerts:
        result["transferred_alerts"] = transferred_alerts
    return result


@student_affairs_router.post("/leaves", status_code=201)
def create_leave(
    payload: LeaveCreateRequest,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    leave = StudentLeave(
        student_no=principal.subject_id,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        reason=payload.reason.strip(),
        status="pending",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return {
        "id": leave.id,
        "student_no": leave.student_no,
        "starts_on": leave.starts_on,
        "ends_on": leave.ends_on,
        "status": leave.status,
    }


@student_affairs_router.post("/leaves/{leave_id}/review")
def review_leave(
    leave_id: int,
    payload: LeaveReviewRequest,
    principal: AuthPrincipal = Depends(require_leave_reviewer),
    db: Session = Depends(get_db),
):
    leave = db.get(StudentLeave, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="请假申请不存在")
    if leave.status != "pending":
        raise HTTPException(status_code=409, detail="该请假申请已处理")
    leave.status = payload.status
    leave.reviewed_by = principal.subject_id
    leave.review_comment = payload.comment.strip()
    db.commit()
    return {"id": leave.id, "student_no": leave.student_no, "status": leave.status}


@student_affairs_router.get("/leaves")
def list_leave_requests(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_leave_reviewer),
    db: Session = Depends(get_db),
):
    statement = select(StudentLeave).order_by(StudentLeave.created_at.desc(), StudentLeave.id.desc())
    if status != "all":
        statement = statement.where(StudentLeave.status == status)
    rows = list(db.execute(statement.offset((page - 1) * page_size).limit(page_size)).scalars())
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "student_no": item.student_no,
                "starts_on": item.starts_on,
                "ends_on": item.ends_on,
                "reason": item.reason,
                "status": item.status,
                "review_comment": item.review_comment,
                "created_at": item.created_at,
            }
            for item in rows
        ],
    }


@student_affairs_router.post("/aid-applications", status_code=201)
def create_aid_application(
    payload: AidApplicationCreateRequest,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    application = StudentAidApplication(
        student_no=principal.subject_id,
        aid_type=payload.aid_type.strip(),
        reason=payload.reason.strip(),
        status="pending",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {
        "id": application.id,
        "student_no": application.student_no,
        "aid_type": application.aid_type,
        "status": application.status,
    }


@student_affairs_router.post("/aid-applications/{application_id}/review")
def review_aid_application(
    application_id: int,
    payload: AidApplicationReviewRequest,
    principal: AuthPrincipal = Depends(require_leave_reviewer),
    db: Session = Depends(get_db),
):
    application = db.get(StudentAidApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="资助申请不存在")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="该资助申请已处理")
    application.status = payload.status
    db.commit()
    return {"id": application.id, "student_no": application.student_no, "status": application.status}


@student_affairs_router.get("/aid-applications")
def list_aid_applications(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_leave_reviewer),
    db: Session = Depends(get_db),
):
    statement = select(StudentAidApplication).order_by(StudentAidApplication.created_at.desc(), StudentAidApplication.id.desc())
    if status != "all":
        statement = statement.where(StudentAidApplication.status == status)
    rows = list(db.execute(statement.offset((page - 1) * page_size).limit(page_size)).scalars())
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "student_no": item.student_no,
                "aid_type": item.aid_type,
                "reason": item.reason,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in rows
        ],
    }


@student_affairs_router.post("/announcements", status_code=201)
def publish_announcement(
    payload: AnnouncementCreateRequest,
    principal: AuthPrincipal = Depends(require_announcement_publisher),
    db: Session = Depends(get_db),
):
    announcement = CampusAnnouncement(
        title=payload.title.strip(),
        content=payload.content.strip(),
        audience=payload.audience,
        status="published",
        published_by=principal.subject_id,
        published_at=datetime.now(),
    )
    db.add(announcement)
    db.commit()
    return {"id": announcement.id, "title": announcement.title, "status": announcement.status}


@student_affairs_router.get("/announcements")
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_roles("admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher", "archive_admin", "staff", "student")),
    db: Session = Depends(get_db),
):
    audience = "student" if principal.role == "student" else "staff"
    rows = list(
        db.execute(
            select(CampusAnnouncement)
            .where(
                CampusAnnouncement.status == "published",
                CampusAnnouncement.audience.in_(("all", audience)),
            )
            .order_by(CampusAnnouncement.published_at.desc(), CampusAnnouncement.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {"id": item.id, "title": item.title, "content": item.content, "audience": item.audience, "published_at": item.published_at}
            for item in rows
        ],
    }


@student_affairs_router.put("/dorms/{student_no}")
def set_dorm_assignment(
    student_no: str,
    payload: DormAssignmentRequest,
    principal: AuthPrincipal = Depends(require_dorm_manager),
    db: Session = Depends(get_db),
):
    _require_existing_student(db, student_no)
    assignment = db.execute(
        select(DormAssignment).where(DormAssignment.student_no == student_no)
    ).scalar_one_or_none()
    if not assignment:
        assignment = DormAssignment(student_no=student_no, building=payload.building.strip(), room_no=payload.room_no.strip(), bed_no=payload.bed_no.strip() if payload.bed_no else None)
        db.add(assignment)
    else:
        assignment.building = payload.building.strip()
        assignment.room_no = payload.room_no.strip()
        assignment.bed_no = payload.bed_no.strip() if payload.bed_no else None
    db.commit()
    return {"student_no": assignment.student_no, "building": assignment.building, "room_no": assignment.room_no, "bed_no": assignment.bed_no}


@student_affairs_router.get("/me/dorm")
def get_my_dorm_assignment(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    assignment = db.execute(
        select(DormAssignment).where(DormAssignment.student_no == principal.subject_id)
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="暂未分配宿舍")
    return {"student_no": assignment.student_no, "building": assignment.building, "room_no": assignment.room_no, "bed_no": assignment.bed_no}


@student_affairs_router.get("/dorm-rooms")
def list_dorm_rooms(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    """返回仍有床位的新生宿舍房间，默认仅展示三间演示数据。"""
    rows = db.execute(
        select(DormRoom, func.count(DormAssignment.id).label("assigned_count"))
        .outerjoin(DormAssignment, and_(DormAssignment.building == DormRoom.building, DormAssignment.room_no == DormRoom.room_no))
        .where(DormRoom.status == "open")
        .group_by(DormRoom.id)
        .order_by(DormRoom.building, DormRoom.room_no)
        .limit(3)
    ).all()
    return {
        "items": [
            {
                "id": room.id,
                "building": room.building,
                "room_no": room.room_no,
                "room_type": room.room_type,
                "capacity": room.capacity,
                "assigned_count": assigned_count,
                "remaining_beds": max(0, room.capacity - assigned_count),
            }
            for room, assigned_count in rows
            if assigned_count < room.capacity
        ]
    }


@student_affairs_router.post("/me/dorm-selection")
def select_my_dorm(
    payload: DormSelectionRequest,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    room = db.execute(
        select(DormRoom).where(DormRoom.id == payload.room_id, DormRoom.status == "open").with_for_update()
    ).scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=404, detail="寝室不存在或暂未开放选择")
    assignments = db.execute(
        select(DormAssignment).where(DormAssignment.room_no == room.room_no).with_for_update()
    ).scalars().all()
    if not any(item.student_no == principal.subject_id for item in assignments) and len(assignments) >= room.capacity:
        raise HTTPException(status_code=409, detail="该寝室已选满，请选择其他寝室")
    if any(item.student_no != principal.subject_id and item.bed_no == payload.bed_no.strip() for item in assignments):
        raise HTTPException(status_code=409, detail="该床位已被选择，请更换床位")
    assignment = db.execute(
        select(DormAssignment).where(DormAssignment.student_no == principal.subject_id).with_for_update()
    ).scalar_one_or_none()
    if assignment is None:
        assignment = DormAssignment(student_no=principal.subject_id, building=room.building, room_no=room.room_no, bed_no=payload.bed_no.strip())
        db.add(assignment)
    else:
        assignment.building = room.building
        assignment.room_no = room.room_no
        assignment.bed_no = payload.bed_no.strip()
    db.commit()
    return {"student_no": principal.subject_id, "building": room.building, "room_no": room.room_no, "bed_no": assignment.bed_no, "message": "寝室选择成功"}


@student_affairs_router.post("/reward-punishments", status_code=201)
def create_reward_punishment(
    payload: RewardPunishmentCreateRequest,
    principal: AuthPrincipal = Depends(require_reward_manager),
    db: Session = Depends(get_db),
):
    _require_existing_student(db, payload.student_no)
    record = StudentRewardPunishment(
        student_no=payload.student_no,
        record_type=payload.record_type,
        title=payload.title.strip(),
        detail=payload.detail.strip() if payload.detail else None,
        recorded_by=principal.subject_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "student_no": record.student_no, "record_type": record.record_type, "title": record.title}


@student_affairs_router.get("/me/reward-punishments")
def list_my_reward_punishments(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    records = list(
        db.execute(
            select(StudentRewardPunishment)
            .where(StudentRewardPunishment.student_no == principal.subject_id)
            .order_by(StudentRewardPunishment.recorded_at.desc(), StudentRewardPunishment.id.desc())
        ).scalars()
    )
    return {
        "items": [
            {"id": record.id, "record_type": record.record_type, "title": record.title, "detail": record.detail, "recorded_at": record.recorded_at}
            for record in records
        ]
    }


@student_affairs_router.put("/graduate-destinations/{student_no}")
def set_graduate_destination(
    student_no: str,
    payload: GraduateDestinationRequest,
    principal: AuthPrincipal = Depends(require_destination_manager),
    db: Session = Depends(get_db),
):
    _require_existing_student(db, student_no)
    destination = db.execute(
        select(GraduateDestination).where(GraduateDestination.student_no == student_no)
    ).scalar_one_or_none()
    if not destination:
        destination = GraduateDestination(student_no=student_no, destination_type=payload.destination_type)
        db.add(destination)
    destination.destination_type = payload.destination_type
    destination.organization = payload.organization.strip() if payload.organization else None
    destination.detail = payload.detail.strip() if payload.detail else None
    db.commit()
    return {"student_no": destination.student_no, "destination_type": destination.destination_type, "organization": destination.organization, "detail": destination.detail}


@student_affairs_router.get("/me/graduate-destination")
def get_my_graduate_destination(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    destination = db.execute(
        select(GraduateDestination).where(GraduateDestination.student_no == principal.subject_id)
    ).scalar_one_or_none()
    if not destination:
        raise HTTPException(status_code=404, detail="暂未登记毕业去向")
    return {"destination_type": destination.destination_type, "organization": destination.organization, "detail": destination.detail, "updated_at": destination.updated_at}
