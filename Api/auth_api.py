"""学生与职员的统一认证接口。"""

import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.agent_session_table import AgentSession
from Model.auth_login_log_table import AuthLoginLog
from Model.staff_account_table import StaffAccount
from Model.student_table import Student
from Model.university_tables import StaffProfile
from Schema.auth_schema import StaffLoginRequest, StudentVerifyRequest, UnifiedLoginRequest
from Service.auth_service import (
    AUTH_COOKIE_NAME,
    AuthPrincipal,
    create_access_token,
    decode_access_token,
    token_digest,
    verify_password,
)
from Service.authorization import get_current_principal


auth_router = APIRouter(prefix="/api/auth", tags=["认证与权限"])
STAFF_TOKEN_MINUTES = 8 * 60
STUDENT_TOKEN_MINUTES = 2 * 60


def _redirect_for_role(role: str) -> str:
    if role == "student":
        return "/pages/university-dashboard"
    if role == "teacher":
        return "/pages/teacher-dashboard"
    if role == "admin":
        return "/pages/admin-modules"
    return "/pages/university-dashboard"


def _record_login(
    db: Session,
    *,
    account_type: str,
    account_id: str,
    success: bool,
    role: str | None = None,
    failure_reason: str | None = None,
    request: Request | None = None,
) -> None:
    client_host = request.client.host if request and request.client else ""
    db.add(
        AuthLoginLog(
            account_type=account_type,
            account_id=account_id,
            role=role,
            success=success,
            failure_reason=failure_reason,
            ip_hash=hashlib.sha256(client_host.encode("utf-8")).hexdigest()
            if client_host
            else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )


def _set_auth_cookie(response: Response, token: str, expires_minutes: int) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=expires_minutes * 60,
    )


def _build_staff_principal(db: Session, account: StaffAccount) -> AuthPrincipal:
    profile = db.execute(
        select(StaffProfile).where(StaffProfile.staff_no == account.staff_no)
    ).scalar_one_or_none()
    return AuthPrincipal(
        role=account.role,
        subject_id=account.staff_no,
        display_name=account.display_name,
        teacher_id=account.teacher_id,
        staff_id=account.id,
        college_id=profile.college_id if profile else None,
        department_id=profile.department_id if profile else None,
    )


def _finish_staff_login(
    account: StaffAccount,
    principal: AuthPrincipal,
    response: Response,
    request: Request,
    db: Session,
) -> dict:
    token = create_access_token(principal, STAFF_TOKEN_MINUTES)
    account.last_login_at = datetime.now()
    _record_login(
        db,
        account_type="staff",
        account_id=account.staff_no,
        success=True,
        role=account.role,
        request=request,
    )
    db.commit()
    _set_auth_cookie(response, token, STAFF_TOKEN_MINUTES)
    return {
        "role": account.role,
        "display_name": account.display_name,
        "redirect_to": _redirect_for_role(account.role),
    }


def _finish_student_login(
    student: Student,
    response: Response,
    request: Request,
    db: Session,
) -> dict:
    principal = AuthPrincipal(
        role="student",
        subject_id=student.student_no,
        display_name=student.name,
    )
    token = create_access_token(principal, STUDENT_TOKEN_MINUTES)
    now = datetime.now()
    db.add(
        AgentSession(
            id=str(uuid4()),
            student_no=student.student_no,
            token_hash=token_digest(token),
            status="active",
            expires_at=now + timedelta(minutes=STUDENT_TOKEN_MINUTES),
            last_active_at=now,
        )
    )
    _record_login(
        db,
        account_type="student",
        account_id=student.student_no,
        success=True,
        role="student",
        request=request,
    )
    db.commit()
    _set_auth_cookie(response, token, STUDENT_TOKEN_MINUTES)
    return {
        "role": "student",
        "display_name": student.name,
        "student": {"student_no": student.student_no, "name": student.name, "class_id": student.class_id},
        "redirect_to": _redirect_for_role("student"),
    }


@auth_router.post("/login")
def unified_login(
    payload: UnifiedLoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate staff accounts and students through one account/password form."""
    staff = db.execute(
        select(StaffAccount).where(
            or_(StaffAccount.staff_no == payload.account, StaffAccount.username == payload.account)
        )
    ).scalar_one_or_none()
    if staff and staff.status == "active" and verify_password(payload.password, staff.password_hash):
        return _finish_staff_login(staff, _build_staff_principal(db, staff), response, request, db)

    student = db.execute(
        select(Student).where(
            Student.student_no == payload.account,
            Student.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if student and student.password_hash and verify_password(payload.password, student.password_hash):
        return _finish_student_login(student, response, request, db)

    _record_login(
        db,
        account_type="unified",
        account_id=payload.account,
        success=False,
        failure_reason="invalid_credentials",
        request=request,
    )
    db.commit()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码不正确，请重试")


@auth_router.post("/staff/login")
def staff_login(
    payload: StaffLoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    account = db.execute(
        select(StaffAccount).where(
            or_(
                StaffAccount.staff_no == payload.account,
                StaffAccount.username == payload.account,
            )
        )
    ).scalar_one_or_none()
    if not account or account.status != "active" or not verify_password(
        payload.password,
        account.password_hash if account else "",
    ):
        _record_login(
            db,
            account_type="staff",
            account_id=payload.account,
            success=False,
            failure_reason="invalid_credentials",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身份验证失败或已过期",
        )

    return _finish_staff_login(account, _build_staff_principal(db, account), response, request, db)


@auth_router.post("/student/verify")
def student_verify(
    payload: StudentVerifyRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    student = db.execute(
        select(Student).where(
            Student.student_no == payload.student_no,
            Student.name == payload.name,
            Student.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if not student:
        _record_login(
            db,
            account_type="student",
            account_id=payload.student_no,
            success=False,
            failure_reason="invalid_identity",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="身份验证失败或已过期",
        )

    return _finish_student_login(student, response, request, db)


@auth_router.get("/me")
def current_identity(
    principal: AuthPrincipal = Depends(get_current_principal),
):
    return {
        "role": principal.role,
        "subject_id": principal.subject_id,
        "display_name": principal.display_name,
        "teacher_id": principal.teacher_id,
    }


@auth_router.post("/logout")
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        try:
            principal = decode_access_token(token)
            if principal.role == "student":
                session = db.execute(
                    select(AgentSession).where(
                        AgentSession.token_hash == token_digest(token)
                    )
                ).scalar_one_or_none()
                if session:
                    session.status = "revoked"
                    db.commit()
        except (RuntimeError, ValueError):
            pass
    response.delete_cookie(AUTH_COOKIE_NAME)
    return {"message": "已安全退出登录"}
