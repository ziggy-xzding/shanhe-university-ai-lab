"""
部门数据访问层
"""
from sqlalchemy.orm import Session
from Model.department_table import Department


def dao_create(db: Session, data: dict) -> Department:
    """新增部门"""
    dept = Department(**data)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def dao_delete(db: Session, dept: Department) -> None:
    """逻辑删除部门"""
    dept.is_deleted = True
    db.commit()


def dao_update(db: Session, dept: Department, data: dict) -> Department:
    """更新部门信息"""
    for key, value in data.items():
        setattr(dept, key, value)
    db.commit()
    db.refresh(dept)
    return dept


def dao_get_all(db: Session) -> list[Department]:
    """获取所有未删除的部门"""
    return db.query(Department).filter(Department.is_deleted == False).all()


def dao_get_by_id(db: Session, dept_id: int) -> Department | None:
    """按ID查询部门"""
    return db.query(Department).filter(
        Department.id == dept_id, Department.is_deleted == False
    ).first()


def dao_get_by_no(db: Session, dept_no: str) -> Department | None:
    """按部门编号查询"""
    return db.query(Department).filter(
        Department.dept_no == dept_no, Department.is_deleted == False
    ).first()
