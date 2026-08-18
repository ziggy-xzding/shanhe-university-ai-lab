"""高校部门字典接口，供教职工归属与组织维护使用。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from DAO.db import get_db
from Model.department_table import Department
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles


department_router = APIRouter(prefix="/api/university/departments", tags=["高校部门管理"])
require_admin = require_roles("admin")


class DepartmentCreateRequest(BaseModel):
    dept_no: str = Field(min_length=1, max_length=20)
    dept_name: str = Field(min_length=1, max_length=50)
    dept_location: str | None = Field(default=None, max_length=50)
    dept_phone: str | None = Field(default=None, max_length=20)


def _serialize(department: Department) -> dict:
    return {
        "id": department.id,
        "dept_no": department.dept_no,
        "dept_name": department.dept_name,
        "dept_location": department.dept_location,
        "dept_phone": department.dept_phone,
    }


@department_router.get("")
def list_departments(
    principal: AuthPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Department)
        .where(Department.is_deleted.is_(False))
        .order_by(Department.dept_no, Department.id)
    ).scalars().all()
    return {"items": [_serialize(row) for row in rows]}


@department_router.post("", status_code=201)
def create_department(
    payload: DepartmentCreateRequest,
    principal: AuthPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    dept_no = payload.dept_no.strip().upper()
    existing = db.execute(
        select(Department).where(Department.dept_no == dept_no, Department.is_deleted.is_(False))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="部门编号已存在")
    department = Department(
        dept_no=dept_no,
        dept_name=payload.dept_name.strip(),
        dept_location=payload.dept_location.strip() if payload.dept_location else None,
        dept_phone=payload.dept_phone.strip() if payload.dept_phone else None,
        is_deleted=False,
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    return _serialize(department)
