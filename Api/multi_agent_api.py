"""多智能体工作台 API。"""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles
from Service.agent_tools import list_tools_for_agents
from Service.knowledge_base_service import create_uploaded_book, get_uploaded_book, retry_book
from Service.multi_agent_service import AGENT_INTENTS, dispatch_message, list_knowledge_books, stream_dispatch_message
from Model.platform_tables import AgentConversation

router = APIRouter(prefix="/api/multi-agent", tags=["多智能体工作台"])
require_user = require_roles("admin", "college_admin", "academic_admin", "student_affairs", "counselor", "teacher", "archive_admin", "staff", "student")
require_book_manager = require_roles("admin", "academic_admin", "teacher", "archive_admin")


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=100)
    agent_type: str | None = Field(default=None, max_length=40)
    context: dict = Field(default_factory=dict)


def validate_agent_selection(agent_type: str | None) -> None:
    if agent_type and agent_type not in AGENT_INTENTS:
        raise HTTPException(status_code=422, detail="未识别的智能体选择")


def load_conversation_history(db: Session, principal: AuthPrincipal, session_id: str | None) -> list[dict]:
    """Load only the current user's recent messages for this session."""
    if not session_id:
        return []
    rows = db.execute(
        select(AgentConversation)
        .where(
            AgentConversation.owner_id == principal.subject_id,
            AgentConversation.owner_role == principal.role,
            AgentConversation.session_id == session_id,
        )
        .order_by(AgentConversation.id.desc())
        .limit(8)
    ).scalars().all()
    return [
        {"role": row.role, "agent_type": row.agent_type, "content": row.content}
        for row in reversed(rows)
    ]


@router.get("/agents")
def agents(principal: AuthPrincipal = Depends(require_user)):
    from Service.multi_agent_service import SUB_AGENTS
    tools = list_tools_for_agents()
    enriched = [{**agent, "tools": tools.get(agent["key"], [])} for agent in SUB_AGENTS]
    return {"primary_agent": "山河主智能体", "sub_agents": enriched, "role": principal.role}


@router.post("/chat")
def chat(payload: AgentChatRequest, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    validate_agent_selection(payload.agent_type)
    session_id = payload.session_id or str(uuid4())
    history = load_conversation_history(db, principal, payload.session_id)
    result = dispatch_message(db, principal, payload.message.strip(), payload.agent_type, history)
    selected_agent = payload.agent_type or result["agent_type"]
    db.add_all([
        AgentConversation(owner_id=principal.subject_id, owner_role=principal.role, agent_type=selected_agent, session_id=session_id, role="user", content=payload.message.strip(), intent=result["intent"], risk_level=result["risk_level"], metadata_json=payload.context),
        AgentConversation(owner_id=principal.subject_id, owner_role=principal.role, agent_type=selected_agent, session_id=session_id, role="assistant", content=result["answer"], intent=result["intent"], risk_level=result["risk_level"], metadata_json={"sources": result.get("sources", []), "routing": result.get("routing", {}), "agent_trace": result.get("agent_trace", []), "tool_calls": result.get("tool_calls", []), "sub_tasks": result.get("sub_tasks", [])}),
    ])
    db.commit()
    result["session_id"] = session_id
    return result


@router.post("/chat/stream")
def chat_stream(payload: AgentChatRequest, principal: AuthPrincipal = Depends(require_user), db: Session = Depends(get_db)):
    """SSE endpoint used by the workspace to render agent output incrementally."""
    validate_agent_selection(payload.agent_type)
    session_id = payload.session_id or str(uuid4())
    history = load_conversation_history(db, principal, payload.session_id)

    def event_stream():
        final_result = None
        try:
            for event in stream_dispatch_message(db, principal, payload.message.strip(), payload.agent_type, history):
                if event["event"] == "done":
                    final_result = event["data"]
                    event["data"]["session_id"] = session_id
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False, default=str)}\n\n"
            if final_result:
                selected_agent = payload.agent_type or final_result["agent_type"]
                db.add_all([
                    AgentConversation(owner_id=principal.subject_id, owner_role=principal.role, agent_type=selected_agent, session_id=session_id, role="user", content=payload.message.strip(), intent=final_result["intent"], risk_level=final_result["risk_level"], metadata_json=payload.context),
                    AgentConversation(owner_id=principal.subject_id, owner_role=principal.role, agent_type=selected_agent, session_id=session_id, role="assistant", content=final_result["answer"], intent=final_result["intent"], risk_level=final_result["risk_level"], metadata_json={"sources": final_result.get("sources", []), "routing": final_result.get("routing", {}), "agent_trace": final_result.get("agent_trace", []), "tool_calls": final_result.get("tool_calls", []), "sub_tasks": final_result.get("sub_tasks", [])}),
                ])
                db.commit()
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': '智能体流式输出中断，请稍后重试', 'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/knowledge/books")
def books(principal: AuthPrincipal = Depends(require_user)):
    return {"items": list_knowledge_books(), "can_upload": principal.role in {"admin", "academic_admin", "teacher", "archive_admin"}}


@router.post("/knowledge/books", status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    book_name: str = Form("未命名书籍"),
    principal: AuthPrincipal = Depends(require_book_manager),
):
    filename = file.filename or "book.txt"
    try:
        entry = create_uploaded_book(filename, book_name, await file.read(), principal.subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"book": entry, "message": "书籍已进入知识库解析队列"}


@router.get("/knowledge/books/{book_id}")
def book_status(book_id: str, principal: AuthPrincipal = Depends(require_user)):
    book = get_uploaded_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="未找到该书籍版本")
    return {"book": book}


@router.post("/knowledge/books/{book_id}/retry")
def book_retry(book_id: str, principal: AuthPrincipal = Depends(require_book_manager)):
    book = retry_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="未找到该书籍版本")
    return {"book": book, "message": "已重新加入知识库解析队列"}
