"""职员账户管理数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from Model.department_table import Department
from Model.staff_account_table import StaffAccount
from Model.university_tables import College, StaffProfile


def list_staff_accounts(db: Session, page: int = 1, page_size: int = 20, keyword: str | None = None):
    filters = []
    if keyword:
        value = f"%{keyword.strip()}%"
        filters.append((StaffAccount.staff_no.like(value)) | (StaffAccount.username.like(value)) | (StaffAccount.display_name.like(value)))
    total = db.execute(select(func.count(StaffAccount.id)).where(*filters)).scalar_one()
    rows = db.execute(
        select(StaffAccount, StaffProfile, College, Department)
        .outerjoin(StaffProfile, StaffProfile.staff_no == StaffAccount.staff_no)
        .outerjoin(College, College.id == StaffProfile.college_id)
        .outerjoin(Department, Department.id == StaffProfile.department_id)
        .where(*filters).order_by(StaffAccount.role, StaffAccount.staff_no)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return total, rows


def get_staff_account(db: Session, account_id: int) -> StaffAccount | None:
    return db.get(StaffAccount, account_id)
