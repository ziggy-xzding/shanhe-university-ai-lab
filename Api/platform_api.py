"""需求文档中的 /api/v1 统一门户、智能体会话和校园数据接口。"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.platform_tables import AcademicAlert, AgentConversation, AgentFeedback, CampusActivity, CampusServiceTicket, CareerOpportunity, LibraryLoan, MoodCheckin, StudentProfile
from Model.student_table import Student
from Service.auth_service import AuthPrincipal
from Service.authorization import get_current_principal, require_roles
from Service.multi_agent_service import dispatch_message

router = APIRouter(prefix="/api/v1", tags=["统一平台 API"])
require_user = require_roles("admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher", "archive_admin", "staff", "student")


class ChatRequest(BaseModel):
    agent_type: str | None = Field(default=None, max_length=40)
    session_id: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    context: dict = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    message_id: str = Field(min_length=1, max_length=80)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


@router.post("/agent/session")
def create_session(principal: AuthPrincipal = Depends(require_user)):
    return {"session_id": str(uuid4()), "agent_type": "orchestrator", "owner_id": principal.subject_id}


@router.post("/agent/chat")
def agent_chat(payload: ChatRequest, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    session_id = payload.session_id or str(uuid4())
    result = dispatch_message(db, principal, payload.message.strip())
    agent_type = payload.agent_type or result["agent_type"]
    db.add_all([
        AgentConversation(owner_id=principal.subject_id, owner_role=principal.role, agent_type=agent_type, session_id=session_id, role="user", content=payload.message.strip(), intent=result["intent"], risk_level=result["risk_level"], metadata_json=payload.context),
        AgentConversation(owner_id=principal.subject_id, owner_role=principal.role, agent_type=agent_type, session_id=session_id, role="assistant", content=result["answer"], intent=result["intent"], risk_level=result["risk_level"], metadata_json={"sources": result.get("sources", [])}),
    ])
    db.commit()
    return {"code": 200, "data": {"message_id": str(uuid4()), "session_id": session_id, "agent_type": agent_type, "content": result["answer"], "references": result.get("sources", []), "suggestions": [], "risk_level": result["risk_level"], "tokens_used": 0, "response_time_ms": 0, "orchestration": result}}


@router.get("/agent/sessions")
def list_sessions(principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.execute(select(AgentConversation.session_id, AgentConversation.agent_type, AgentConversation.created_at).where(AgentConversation.owner_id == principal.subject_id).order_by(AgentConversation.created_at.desc()).limit(20)).all()
    seen = set()
    items = []
    for session_id, agent_type, created_at in rows:
        if session_id in seen:
            continue
        seen.add(session_id)
        items.append({"session_id": session_id, "agent_type": agent_type, "created_at": created_at})
    return {"items": items}


@router.get("/agent/sessions/{session_id}")
def session_detail(session_id: str, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.execute(select(AgentConversation).where(AgentConversation.owner_id == principal.subject_id, AgentConversation.session_id == session_id).order_by(AgentConversation.created_at)).scalars().all()
    return {"session_id": session_id, "items": [{"id": row.id, "role": row.role, "agent_type": row.agent_type, "content": row.content, "risk_level": row.risk_level, "created_at": row.created_at} for row in rows]}


@router.post("/agent/feedback", status_code=201)
def agent_feedback(payload: FeedbackRequest, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    item = AgentFeedback(owner_id=principal.subject_id, message_id=payload.message_id, rating=payload.rating, comment=payload.comment)
    db.add(item)
    db.commit()
    return {"id": item.id, "message": "反馈已记录"}


@router.get("/dashboard/overview")
def dashboard_overview(principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    activities = db.execute(select(CampusActivity).where(CampusActivity.status == "published").order_by(CampusActivity.starts_at).limit(3)).scalars().all()
    jobs = db.execute(select(CareerOpportunity).where(CareerOpportunity.status == "published").order_by(CareerOpportunity.deadline).limit(3)).scalars().all()
    mood = db.execute(select(MoodCheckin).where(MoodCheckin.student_no == principal.subject_id).order_by(MoodCheckin.created_at.desc()).limit(3)).scalars().all() if principal.role == "student" else []
    return {"role": principal.role, "activities": [{"title": item.title, "category": item.category, "location": item.location} for item in activities], "opportunities": [{"title": item.title, "organization": item.organization, "city": item.city} for item in jobs], "mood_checkins": [{"score": item.mood_score, "risk_level": item.risk_level, "created_at": item.created_at} for item in mood]}


def _student_scope(principal: AuthPrincipal, student_id: int | None = None) -> bool:
    return principal.role != "student" or student_id is None


@router.get("/students")
def list_students(page: int = Query(1, ge=1), page_size: int = Query(3, ge=1, le=100), keyword: str | None = Query(None, max_length=80), principal: AuthPrincipal = Depends(require_roles("admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher")), db: Session = Depends(get_db)):
    statement = select(Student).where(Student.is_deleted.is_(False))
    if keyword:
        statement = statement.where(Student.student_no.contains(keyword) | Student.name.contains(keyword))
    total = len(db.execute(statement).scalars().all())
    rows = db.execute(statement.order_by(Student.student_no).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"page": page, "page_size": page_size, "total": total, "items": [{"id": row.id, "student_no": row.student_no, "name": row.name, "major": row.major, "education": row.education, "status": "active" if not row.is_deleted else "deleted"} for row in rows]}


def _get_student_for_role(student_id: int, principal: AuthPrincipal, db: Session) -> Student:
    student = db.get(Student, student_id)
    if not student or student.is_deleted:
        raise HTTPException(status_code=404, detail="学生不存在")
    if principal.role == "student" and student.student_no != principal.subject_id:
        raise HTTPException(status_code=403, detail="只能查看本人信息")
    return student


@router.get("/students/{student_id}")
def student_detail(student_id: int, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    student = _get_student_for_role(student_id, principal, db)
    return {"id": student.id, "student_no": student.student_no, "name": student.name, "major": student.major, "education": student.education, "gender": student.gender, "class_id": student.class_id}


@router.get("/students/{student_id}/profile")
def student_profile(student_id: int, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    student = _get_student_for_role(student_id, principal, db)
    profile = db.execute(select(StudentProfile).where(StudentProfile.student_no == student.student_no)).scalar_one_or_none()
    return {"student_no": student.student_no, "profile": None if profile is None else {"gpa": profile.gpa, "credit_deficit": profile.credit_deficit, "fail_count": profile.fail_count, "academic_risk_level": profile.academic_risk_level, "attendance_rate": profile.attendance_rate, "career_interest": profile.career_interest, "skill_tags": profile.skill_tags}}


@router.get("/students/{student_id}/alerts")
def student_alerts(student_id: int, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    student = _get_student_for_role(student_id, principal, db)
    rows = db.execute(select(AcademicAlert).where(AcademicAlert.student_no == student.student_no).order_by(AcademicAlert.created_at.desc()).limit(3)).scalars().all()
    return {"items": [{"id": row.id, "alert_type": row.alert_type, "severity": row.severity, "title": row.title, "description": row.description, "status": row.status, "created_at": row.created_at} for row in rows]}


@router.get("/campus/activities")
def activities(principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.execute(select(CampusActivity).where(CampusActivity.status == "published").order_by(CampusActivity.starts_at).limit(3)).scalars().all()
    return {"items": [{"id": row.id, "title": row.title, "category": row.category, "location": row.location, "starts_at": row.starts_at, "capacity": row.capacity, "enrolled_count": row.enrolled_count} for row in rows]}


@router.get("/career/opportunities")
def opportunities(principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.execute(select(CareerOpportunity).where(CareerOpportunity.status == "published").order_by(CareerOpportunity.deadline).limit(3)).scalars().all()
    return {"items": [{"id": row.id, "title": row.title, "organization": row.organization, "city": row.city, "job_type": row.job_type, "tags": row.tags, "deadline": row.deadline} for row in rows]}


@router.get("/library/loans")
def library_loans(principal: AuthPrincipal = Depends(require_roles("student")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(LibraryLoan)
        .where(LibraryLoan.student_no == principal.subject_id, LibraryLoan.status == "borrowed")
        .order_by(LibraryLoan.due_at, LibraryLoan.id)
        .limit(3)
    ).scalars().all()
    return {
        "integration": "library_demo_adapter",
        "integration_note": "当前为图书馆系统演示适配层，后续可替换为学校图书馆接口。",
        "items": [
            {
                "id": row.id,
                "book_title": row.book_title,
                "author": row.author,
                "borrowed_at": row.borrowed_at,
                "due_at": row.due_at,
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/mental/checkins")
def list_mood_checkins(principal: AuthPrincipal = Depends(require_roles("student")), db: Session = Depends(get_db)):
    rows = db.execute(select(MoodCheckin).where(MoodCheckin.student_no == principal.subject_id).order_by(MoodCheckin.created_at.desc()).limit(3)).scalars().all()
    return {"items": [{"id": row.id, "mood_score": row.mood_score, "tags": row.tags, "risk_level": row.risk_level, "created_at": row.created_at} for row in rows]}


class MoodRequest(BaseModel):
    mood_score: int = Field(ge=1, le=10)
    tags: list[str] = Field(default_factory=list, max_length=6)
    note: str | None = Field(default=None, max_length=500)


@router.post("/mental/checkins", status_code=201)
def mood_checkin(payload: MoodRequest, principal: AuthPrincipal = Depends(require_roles("student")), db: Session = Depends(get_db)):
    risk = "high" if payload.mood_score <= 2 else "warning" if payload.mood_score <= 4 else "normal"
    item = MoodCheckin(student_no=principal.subject_id, mood_score=payload.mood_score, tags=payload.tags, note=payload.note, risk_level=risk)
    db.add(item)
    db.commit()
    return {"id": item.id, "risk_level": risk, "message": "情绪记录已保存；如存在现实危险，请立即联系专业人员。"}


class TicketRequest(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class TicketUpdateRequest(BaseModel):
    status: str = Field(pattern="^(submitted|processing|resolved|closed)$")
    assigned_to: str | None = Field(default=None, max_length=30)


@router.post("/service/tickets", status_code=201)
def create_service_ticket(payload: TicketRequest, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    item = CampusServiceTicket(owner_id=principal.subject_id, category=payload.category, title=payload.title, description=payload.description, priority=payload.priority)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "status": item.status, "message": "服务问题已提交，系统管理员会跟进处理"}


@router.get("/service/tickets")
def list_service_tickets(principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    statement = select(CampusServiceTicket).order_by(CampusServiceTicket.created_at.desc()).limit(3)
    if principal.role not in {"admin", "staff"}:
        statement = statement.where(CampusServiceTicket.owner_id == principal.subject_id)
    rows = db.execute(statement).scalars().all()
    return {"items": [{"id": row.id, "category": row.category, "title": row.title, "description": row.description, "status": row.status, "priority": row.priority, "assigned_to": row.assigned_to, "created_at": row.created_at} for row in rows]}


@router.patch("/service/tickets/{ticket_id}")
def update_service_ticket(ticket_id: int, payload: TicketUpdateRequest, principal: AuthPrincipal = Depends(require_roles("admin", "staff")), db: Session = Depends(get_db)):
    item = db.get(CampusServiceTicket, ticket_id)
    if not item:
        raise HTTPException(status_code=404, detail="问题工单不存在")
    item.status = payload.status
    item.assigned_to = payload.assigned_to or item.assigned_to
    db.commit()
    return {"id": item.id, "status": item.status, "assigned_to": item.assigned_to}


@router.get("/alerts")
def list_academic_alerts(principal: AuthPrincipal = Depends(require_roles("admin", "academic_admin", "student_affairs", "counselor", "teacher")), db: Session = Depends(get_db)):
    rows = db.execute(select(AcademicAlert).order_by(AcademicAlert.created_at.desc()).limit(3)).scalars().all()
    return {"items": [{"id": row.id, "student_no": row.student_no, "alert_type": row.alert_type, "severity": row.severity, "title": row.title, "status": row.status, "description": row.description} for row in rows]}


@router.patch("/alerts/{alert_id}/resolve")
def resolve_academic_alert(alert_id: int, principal: AuthPrincipal = Depends(require_roles("admin", "academic_admin", "student_affairs", "counselor")), db: Session = Depends(get_db)):
    item = db.get(AcademicAlert, alert_id)
    if not item:
        raise HTTPException(status_code=404, detail="预警不存在")
    item.status = "resolved"
    item.resolved_at = datetime.now()
    db.commit()
    return {"id": item.id, "status": item.status, "resolved_at": item.resolved_at}
