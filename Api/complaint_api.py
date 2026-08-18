"""学生投诉、建议和申诉接口。"""

from hashlib import sha256
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.complaint_tables import ComplaintAction, ComplaintIdentity, ComplaintTicket
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles


complaint_router = APIRouter(prefix="/api/complaints", tags=["投诉建议"])
require_student = require_roles("student")
require_complaint_staff = require_roles("admin", "student_affairs")
COMPLAINT_STATUSES = {"submitted", "in_progress", "resolved", "closed"}


class ComplaintCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    content: str = Field(min_length=1, max_length=5000)
    anonymous: bool = True


class ComplaintActionRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)
    comment: str = Field(min_length=1, max_length=2000)


@complaint_router.post("", status_code=201)
def create_complaint(
    payload: ComplaintCreateRequest,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    ticket = ComplaintTicket(
        category=payload.category,
        content=payload.content,
        status="submitted",
        anonymous=payload.anonymous,
        tracking_token_hash=sha256((tracking_token := token_urlsafe(24)).encode("utf-8")).hexdigest(),
    )
    db.add(ticket)
    db.flush()
    db.add(ComplaintIdentity(ticket_id=ticket.id, student_no=principal.subject_id))
    db.add(ComplaintAction(ticket_id=ticket.id, action="submit", comment=None))
    db.commit()
    return {
        "ticket_id": ticket.id,
        "category": ticket.category,
        "status": ticket.status,
        "anonymous": ticket.anonymous,
        "tracking_token": tracking_token,
    }


@complaint_router.get("/tracking/{tracking_token}")
def track_complaint(tracking_token: str, db: Session = Depends(get_db)):
    ticket = db.execute(
        select(ComplaintTicket).where(
            ComplaintTicket.tracking_token_hash
            == sha256(tracking_token.encode("utf-8")).hexdigest()
        )
    ).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="投诉查询凭证无效")
    latest_reply = db.execute(
        select(ComplaintAction.comment)
        .where(
            ComplaintAction.ticket_id == ticket.id,
            ComplaintAction.action == "status_change",
        )
        .order_by(ComplaintAction.created_at.desc(), ComplaintAction.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return {
        "ticket_id": ticket.id,
        "category": ticket.category,
        "status": ticket.status,
        "anonymous": ticket.anonymous,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "latest_reply": latest_reply,
    }


@complaint_router.get("")
def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_complaint_staff),
    db: Session = Depends(get_db),
):
    tickets = list(
        db.execute(
            select(ComplaintTicket)
            .order_by(ComplaintTicket.updated_at.desc(), ComplaintTicket.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "ticket_id": ticket.id,
                "category": ticket.category,
                "content": ticket.content,
                "status": ticket.status,
                "anonymous": ticket.anonymous,
                "assigned_department_id": ticket.assigned_department_id,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
            }
            for ticket in tickets
        ],
    }


@complaint_router.post("/{ticket_id}/actions")
def process_complaint(
    ticket_id: int,
    payload: ComplaintActionRequest,
    principal: AuthPrincipal = Depends(require_complaint_staff),
    db: Session = Depends(get_db),
):
    if payload.status not in COMPLAINT_STATUSES:
        raise HTTPException(status_code=422, detail="投诉状态无效")
    ticket = db.execute(
        select(ComplaintTicket).where(ComplaintTicket.id == ticket_id)
    ).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="投诉工单不存在")
    ticket.status = payload.status
    db.add(
        ComplaintAction(
            ticket_id=ticket.id,
            actor_staff_no=principal.subject_id,
            action="status_change",
            comment=payload.comment,
        )
    )
    db.commit()
    return {"ticket_id": ticket.id, "status": ticket.status}
