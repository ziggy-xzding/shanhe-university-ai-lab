"""仅供学生本人使用的成长 Agent 接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Schema.student_agent_schema import AgentChatRequest, AgentReportRequest
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles
from Service.score_analysis_service import build_student_overview
from Service.student_agent_service import (
    chat_with_student,
    generate_report,
    get_student_messages,
)
from Model.platform_tables import StudentTodo
from Service.student_development_service import build_student_development


student_agent_router = APIRouter(prefix="/api/student-agent", tags=["学生发展 Agent"])
require_student = require_roles("student")


@student_agent_router.get("/overview")
def overview(
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    data = build_student_overview(db, principal.subject_id)
    development = build_student_development(db, principal.subject_id)
    db.commit()
    return {
        "student": {
            "student_no": data["student_no"],
            "name": data["student_name"],
            "class_id": data["class_id"],
        },
        "metrics": {
            key: data[key]
            for key in (
                "average_score",
                "class_average",
                "class_rank",
                "class_size",
                "pass_rate",
                "latest_change",
                "attention_level",
            )
        },
        "scores": data["scores"],
        **development,
    }


@student_agent_router.post("/chat")
def chat(
    payload: AgentChatRequest,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    try:
        return chat_with_student(db, principal, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="身份验证失败或已过期") from exc


@student_agent_router.get("/messages")
def messages(
    limit: int = Query(30, ge=1, le=50),
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    return get_student_messages(db, principal, limit)


@student_agent_router.post("/reports")
def report(
    payload: AgentReportRequest,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    return generate_report(db, principal, payload.report_type)


@student_agent_router.patch("/todos/{todo_id}/read")
def archive_todo(
    todo_id: int,
    principal: AuthPrincipal = Depends(require_student),
    db: Session = Depends(get_db),
):
    item = db.execute(
        select(StudentTodo).where(
            StudentTodo.id == todo_id,
            StudentTodo.student_no == principal.subject_id,
            StudentTodo.status == "active",
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="待办不存在或已经归档")
    from datetime import datetime
    item.status = "archived"
    item.archived_at = datetime.now()
    db.commit()
    return {"id": item.id, "status": item.status}
