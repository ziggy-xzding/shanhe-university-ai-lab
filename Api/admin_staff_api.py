"""管理员职员账户接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from DAO.db import get_db
from DAO.staff_account_dao import get_staff_account, list_staff_accounts
from Model.department_table import Department
from Model.agent_report_table import AgentReport
from Model.staff_account_table import StaffAccount
from Model.teacher_table import teacher_table
from Model.university_tables import College, StaffProfile
from Schema.staff_schema import (
    ResetPasswordRequest,
    StaffAccountCreate,
    StaffAccountUpdate,
)
from Service.auth_service import hash_password
from Service.authorization import require_roles


admin_staff_router = APIRouter(prefix="/api/admin", tags=["管理员"])
require_admin = require_roles("admin")


def _serialize_staff(account: StaffAccount, profile: StaffProfile | None = None, college_name: str | None = None, department_name: str | None = None) -> dict:
    return {
        "id": account.id,
        "staff_no": account.staff_no,
        "username": account.username,
        "display_name": account.display_name,
        "role": account.role,
        "teacher_id": account.teacher_id,
        "status": account.status,
        "last_login_at": account.last_login_at,
        "college_id": profile.college_id if profile else None,
        "college_name": college_name,
        "department_id": profile.department_id if profile else None,
        "department_name": department_name,
        "position": profile.position if profile else None,
    }


def _get_profile(db: Session, staff_no: str) -> StaffProfile | None:
    return db.query(StaffProfile).filter(StaffProfile.staff_no == staff_no).one_or_none()


def _validate_college(db: Session, college_id: int | None) -> None:
    if college_id is not None and db.get(College, college_id) is None:
        raise HTTPException(status_code=422, detail="学院不存在")


def _validate_department(db: Session, department_id: int | None) -> None:
    if department_id is not None:
        department = db.get(Department, department_id)
        if department is None or department.is_deleted:
            raise HTTPException(status_code=422, detail="部门不存在或已停用")


def _validate_teacher_reference(db: Session, role: str, teacher_id: int | None) -> None:
    if role == "teacher" and teacher_id is None:
        raise HTTPException(status_code=422, detail="教师账户必须关联教师档案")
    if teacher_id is not None and not db.execute(
        select(teacher_table.tid).where(teacher_table.tid == teacher_id)
    ).scalar_one_or_none():
        raise HTTPException(status_code=422, detail="关联教师档案不存在")


@admin_staff_router.get("/staff-accounts")
def staff_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, min_length=1, max_length=50),
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total, rows = list_staff_accounts(db, page=page, page_size=page_size, keyword=keyword)
    return {
        "page": page, "page_size": page_size, "total": total,
        "items": [_serialize_staff(account, profile, college.name if college else None, department.dept_name if department else None) for account, profile, college, department in rows],
    }


@admin_staff_router.post("/staff-accounts", status_code=201)
def create_staff_account(
    payload: StaffAccountCreate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _validate_college(db, payload.college_id)
    _validate_department(db, payload.department_id)
    _validate_teacher_reference(db, payload.role, payload.teacher_id)
    account = StaffAccount(
        staff_no=payload.staff_no,
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=payload.role,
        teacher_id=payload.teacher_id,
        status=payload.status,
    )
    db.add(account)
    profile = StaffProfile(
        staff_no=payload.staff_no,
        college_id=payload.college_id,
        department_id=payload.department_id,
        position=payload.position,
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="职员账号或工号已存在") from exc
    db.refresh(account)
    db.refresh(profile)
    college = db.get(College, profile.college_id) if profile.college_id else None
    department = db.get(Department, profile.department_id) if profile.department_id else None
    return _serialize_staff(account, profile, college.name if college else None, department.dept_name if department else None)


@admin_staff_router.put("/staff-accounts/{account_id}")
def update_staff_account(
    account_id: int,
    payload: StaffAccountUpdate,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
):
    account = get_staff_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="职员账户不存在")
    values = payload.model_dump(exclude_unset=True)
    _validate_college(db, values.get("college_id"))
    _validate_department(db, values.get("department_id"))
    _validate_teacher_reference(
        db,
        values.get("role", account.role),
        values.get("teacher_id", account.teacher_id),
    )
    for field, value in values.items():
        if field not in {"college_id", "department_id", "position"}:
            setattr(account, field, value)
    profile_fields = {key: values[key] for key in {"college_id", "department_id", "position"} & values.keys()}
    profile = _get_profile(db, account.staff_no)
    if profile_fields and profile is None:
        profile = StaffProfile(staff_no=account.staff_no)
        db.add(profile)
    if profile:
        for field, value in profile_fields.items():
            setattr(profile, field, value)
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    profile = _get_profile(db, account.staff_no)
    college = db.get(College, profile.college_id) if profile and profile.college_id else None
    department = db.get(Department, profile.department_id) if profile and profile.department_id else None
    return _serialize_staff(account, profile, college.name if college else None, department.dept_name if department else None)


@admin_staff_router.post("/staff-accounts/{account_id}/reset-password")
def reset_staff_password(
    account_id: int,
    payload: ResetPasswordRequest,
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
):
    account = get_staff_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="职员账户不存在")
    account.password_hash = hash_password(payload.password)
    db.commit()
    return {"message": "密码已重置"}


@admin_staff_router.get("/agent-statistics")
def agent_statistics(
    _: object = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func, select

    rows = db.execute(
        select(AgentReport.attention_level, func.count(AgentReport.id))
        .group_by(AgentReport.attention_level)
    ).all()
    return {
        "report_count": sum(int(row[1]) for row in rows),
        "attention_levels": {row[0]: int(row[1]) for row in rows},
    }
