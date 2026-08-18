from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from Model.consultant_table import Consultant
from Model.department_table import Department
from typing import List, Dict
from Schema.consultant_schema import ConsultantCreate, ConsultantUpdate
from DAO.department_dao import dao_get_by_no
from datetime import datetime


def _validate_dept_no(db: Session, dept_no: str) -> None:
    """校验部门编号是否存在（业务层兜底）。"""
    dept = db.query(Department).filter(
        Department.dept_no == dept_no,
        Department.is_deleted == False,
    ).first()
    if not dept:
        raise ValueError(f"部门编号 {dept_no} 不存在")


def _build_consultant_query(db: Session, dept_no: str | None, keyword: str | None):
    """构建顾问过滤查询（供 list 和 count 复用）。"""
    query = db.query(Consultant).filter(Consultant.is_deleted == False)
    if dept_no:
        query = query.filter(Consultant.dept_no == dept_no)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            Consultant.name.like(kw)
            | Consultant.consultant_no.like(kw)
            | Consultant.dept_no.like(kw)
            | Consultant.title.like(kw)
        )
    return query


def get_consultant_list(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    dept_no: str | None = None,
    keyword: str | None = None,
) -> List[Consultant]:
    return (
        _build_consultant_query(db, dept_no, keyword)
        .order_by(desc(Consultant.create_time))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_consultant_total(
    db: Session,
    dept_no: str | None = None,
    keyword: str | None = None,
) -> int:
    """返回满足条件的顾问总条数，供分页接口返回 X-Total-Count 响应头。"""
    return _build_consultant_query(db, dept_no, keyword).count()


def get_consultant_by_id(db: Session, consultant_id: int) -> Consultant:
    consultant = db.query(Consultant).filter(
        Consultant.consultant_id == consultant_id,
        Consultant.is_deleted == False,
    ).first()
    if not consultant:
        raise ValueError(f"顾问不存在: {consultant_id}")
    return consultant


def get_consultant_by_no(db: Session, consultant_no: str) -> Consultant:
    consultant = db.query(Consultant).filter(
        Consultant.consultant_no == consultant_no,
        Consultant.is_deleted == False,
    ).first()
    if not consultant:
        raise ValueError(f"顾问不存在: {consultant_no}")
    return consultant


def create_consultant_item(db: Session, consultant: ConsultantCreate) -> Consultant:
    _validate_dept_no(db, consultant.dept_no)
    new_consultant = Consultant(**consultant.model_dump())
    db.add(new_consultant)
    db.commit()
    db.refresh(new_consultant)
    return new_consultant


def batch_create_consultants(db: Session, consultants: List[ConsultantCreate]) -> List[Consultant]:
    dept_nos = {c.dept_no for c in consultants}
    for dno in dept_nos:
        _validate_dept_no(db, dno)
    new_consultants = [Consultant(**c.model_dump()) for c in consultants]
    db.add_all(new_consultants)
    db.commit()
    for c in new_consultants:
        db.refresh(c)
    return new_consultants


def update_consultant_item(db: Session, consultant_id: int, data: ConsultantUpdate) -> Consultant:
    db_consultant = db.query(Consultant).filter(
        Consultant.consultant_id == consultant_id,
        Consultant.is_deleted == False,
    ).first()
    if not db_consultant:
        raise ValueError(f"顾问不存在: {consultant_id}")
    update_data = data.model_dump(exclude_unset=True)
    if "dept_no" in update_data:
        _validate_dept_no(db, update_data["dept_no"])
    for key, value in update_data.items():
        setattr(db_consultant, key, value)
    db.commit()
    db.refresh(db_consultant)
    return db_consultant


def get_deleted_consultants(db: Session) -> List[Consultant]:
    """查询所有已逻辑删除的顾问，按删除时间倒序。"""
    return (
        db.query(Consultant)
        .filter(Consultant.is_deleted == True)
        .order_by(desc(Consultant.update_time))
        .all()
    )


def restore_consultant_item(db: Session, consultant_id: int) -> Consultant:
    """将已删除的顾问恢复为正常状态，只能操作 is_deleted=True 的记录。"""
    db_consultant = db.query(Consultant).filter(
        Consultant.consultant_id == consultant_id,
        Consultant.is_deleted == True,
    ).first()
    if not db_consultant:
        raise ValueError(f"顾问不存在或未被删除: {consultant_id}")
    db_consultant.is_deleted = False
    db_consultant.update_time = datetime.now()
    db.commit()
    db.refresh(db_consultant)
    return db_consultant


def delete_consultant_item(db: Session, consultant_id: int) -> None:
    db_consultant = db.query(Consultant).filter(
        Consultant.consultant_id == consultant_id,
        Consultant.is_deleted == False,
    ).first()
    if not db_consultant:
        raise ValueError(f"顾问不存在: {consultant_id}")
    db_consultant.is_deleted = True
    db_consultant.update_time = datetime.now()
    db.commit()


def get_consultant_manager(db: Session, consultant_no: str) -> Dict:
    """根据顾问编号查询其直属领导（同部门的管理者）。"""
    consultant = get_consultant_by_no(db, consultant_no)

    department = dao_get_by_no(db, consultant.dept_no)
    if not department:
        raise ValueError(f"顾问所属部门 {consultant.dept_no} 不存在或已删除")

    return {
        "consultant_id": consultant.consultant_id,
        "consultant_no": consultant.consultant_no,
        "consultant_name": consultant.name,
        "consultant_title": consultant.title,
        "dept_no": consultant.dept_no,
        "dept_name": department.dept_name,
        "manager_name": department.dept_manager,
    }