"""仅向负责该学生的辅导员展示心理风险处置提醒。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.risk_alert_tables import RiskAlert
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles


risk_alert_router = APIRouter(prefix="/api/risk-alerts", tags=["心理风险预警"])
require_counselor = require_roles("counselor")


class RiskAlertDispositionRequest(BaseModel):
    status: str = Field(pattern="^(reviewed|closed)$")
    disposition: str = Field(min_length=1, max_length=2000)


@risk_alert_router.get("")
def list_my_risk_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    principal: AuthPrincipal = Depends(require_counselor),
    db: Session = Depends(get_db),
):
    alerts = list(
        db.execute(
            select(RiskAlert)
            .where(RiskAlert.counselor_staff_no == principal.subject_id)
            .order_by(RiskAlert.created_at.desc(), RiskAlert.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": alert.id,
                "student_no": alert.student_no,
                "risk_level": alert.risk_level,
                "status": alert.status,
                "trigger_summary": alert.trigger_summary,
                "disposition": alert.disposition,
                "created_at": alert.created_at,
                "updated_at": alert.updated_at,
            }
            for alert in alerts
        ],
    }


@risk_alert_router.patch("/{alert_id}")
def record_risk_alert_disposition(
    alert_id: int,
    payload: RiskAlertDispositionRequest,
    principal: AuthPrincipal = Depends(require_counselor),
    db: Session = Depends(get_db),
):
    alert = db.execute(
        select(RiskAlert).where(
            RiskAlert.id == alert_id,
            RiskAlert.counselor_staff_no == principal.subject_id,
        )
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="心理风险预警不存在或无权处理")
    alert.status = payload.status
    alert.disposition = payload.disposition.strip()
    db.commit()
    return {"id": alert.id, "status": alert.status, "disposition": alert.disposition}
