"""教师工作台接口。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from DAO.db import get_db
from DAO.teacher_workbench_dao import (
    class_score_analysis,
    list_class_students,
    list_teacher_classes,
    teacher_class_ids,
)
from Service.auth_service import AuthPrincipal
from Service.authorization import require_roles


teacher_workbench_router = APIRouter(prefix="/api/teacher", tags=["教师工作台"])
require_teacher_or_admin = require_roles("teacher", "admin")


def ensure_teacher_can_access_class(
    db: Session,
    principal: AuthPrincipal,
    class_id: int,
) -> None:
    if principal.role == "admin":
        return
    if class_id not in teacher_class_ids(db, principal.teacher_id):
        raise HTTPException(status_code=403, detail="当前身份无权访问该班级")


@teacher_workbench_router.get("/workbench/overview")
def workbench_overview(
    principal: AuthPrincipal = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    classes = list_teacher_classes(db, principal.teacher_id) if principal.role == "teacher" else []
    return {
        "teacher_id": principal.teacher_id,
        "display_name": principal.display_name,
        "classes": classes,
        "class_count": len(classes),
        "student_count": sum(item["student_count"] for item in classes),
    }


@teacher_workbench_router.get("/classes")
def classes(
    principal: AuthPrincipal = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    if principal.role == "admin":
        from sqlalchemy import select
        from Model.class_table import Class

        rows = db.execute(
            select(Class).where(Class.is_deleted == 0).order_by(Class.class_no)
        ).scalars()
        return [
            {"id": item.id, "class_no": item.class_no, "name": item.name}
            for item in rows
        ]
    return list_teacher_classes(db, principal.teacher_id)


@teacher_workbench_router.get("/classes/{class_id}/students")
def class_students(
    class_id: int,
    principal: AuthPrincipal = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    ensure_teacher_can_access_class(db, principal, class_id)
    return list_class_students(db, class_id)


@teacher_workbench_router.get("/classes/{class_id}/score-analysis")
def score_analysis(
    class_id: int,
    principal: AuthPrincipal = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db),
):
    ensure_teacher_can_access_class(db, principal, class_id)
    return class_score_analysis(db, class_id)
