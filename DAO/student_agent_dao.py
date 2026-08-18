"""学生成长 Agent 的会话、消息与报告持久化。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from Model.agent_message_table import AgentMessage
from Model.agent_report_table import AgentReport
from Model.agent_session_table import AgentSession


def get_latest_active_session(db: Session, student_no: str) -> AgentSession | None:
    return db.execute(
        select(AgentSession)
        .where(
            AgentSession.student_no == student_no,
            AgentSession.status == "active",
        )
        .order_by(AgentSession.last_active_at.desc())
    ).scalars().first()


def create_message(
    db: Session,
    *,
    session_id: str,
    role: str,
    content: str,
    intent: str | None = None,
    source_refs: list[dict] | None = None,
    risk_level: str = "normal",
) -> AgentMessage:
    message = AgentMessage(
        session_id=session_id,
        role=role,
        content=content,
        intent=intent,
        source_refs=source_refs,
        risk_level=risk_level,
    )
    db.add(message)
    db.flush()
    return message


def list_messages(db: Session, session_id: str, limit: int) -> list[AgentMessage]:
    return list(
        db.execute(
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
            .limit(limit)
        ).scalars()
    )


def create_report(
    db: Session,
    *,
    student_no: str,
    report_type: str,
    metrics_snapshot: dict,
    attention_level: str,
    strengths: str,
    improvements: str,
    action_plan: str,
    comment: str,
    generated_by: str,
) -> AgentReport:
    report = AgentReport(
        student_no=student_no,
        report_type=report_type,
        metrics_snapshot=metrics_snapshot,
        attention_level=attention_level,
        strengths=strengths,
        improvements=improvements,
        action_plan=action_plan,
        comment=comment,
        generated_by=generated_by,
    )
    db.add(report)
    db.flush()
    return report
