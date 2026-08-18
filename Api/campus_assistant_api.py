"""全角色校园智能助手接口。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from DAO.db import get_db
from Service.auth_service import AuthPrincipal
from Service.authorization import get_current_principal
from Service.campus_assistant_service import answer_campus_query
from Service.risk_detection_service import create_minimal_risk_alert, has_high_risk_signal


class CampusAssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("消息不能为空")
        return value


campus_assistant_router = APIRouter(prefix="/api/campus-assistant", tags=["校园智能助手"])


@campus_assistant_router.post("/chat")
def chat(
    payload: CampusAssistantRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    if principal.role == "student" and has_high_risk_signal(payload.message):
        created = create_minimal_risk_alert(db, principal.subject_id)
        db.commit()
        return {
            "role": principal.role,
            "answer": "我很在意你现在的安全。请立刻联系身边可信任的人、学校心理老师或当地紧急服务；请不要独自承受。",
            "data": {},
            "risk_level": "high",
            "risk_alert_created": created,
        }
    result = answer_campus_query(db, principal, payload.message)
    return {"role": principal.role, "risk_level": "normal", "risk_alert_created": False, **result}
