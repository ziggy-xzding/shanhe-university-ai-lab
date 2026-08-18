"""
就业数据访问层
===============
封装 employment 表的所有数据库操作。
所有查询函数均支持 include_deleted 参数：传 True 时可查看已删除记录。
"""
from typing import Optional
from Model.employment_table import Employment
from Model.student_table import Student


def dao_get_student(db, student_no: str):
    return db.query(Student).filter(
        Student.student_no == student_no, Student.is_deleted == False
    ).first()


def dao_get_employment_by_student(db, student_no: str, include_deleted: bool = False):
    query = db.query(Employment).filter(Employment.student_no == student_no)
    if not include_deleted:
        query = query.filter(Employment.is_deleted == False)
    return query.first()


def dao_get_employment_by_id(db, employment_id: int, include_deleted: bool = False):
    query = db.query(Employment).filter(Employment.id == employment_id)
    if not include_deleted:
        query = query.filter(Employment.is_deleted == False)
    return query.first()


def dao_get_employment_by_class(db, class_name: str, include_deleted: bool = False):
    query = db.query(Employment).filter(Employment.class_name == class_name)
    if not include_deleted:
        query = query.filter(Employment.is_deleted == False)
    return query.all()


def dao_list_employment(
    db,
    student_name=None,
    company=None,
    min_salary=None,
    max_salary=None,
    include_deleted=False,
):
    query = db.query(Employment)
    if not include_deleted:
        query = query.filter(Employment.is_deleted == False)
    if student_name:
        query = query.filter(Employment.student_name == student_name)
    if company:
        query = query.filter(Employment.company.like(f"%{company}%"))
    if min_salary is not None:
        query = query.filter(Employment.salary >= min_salary)
    if max_salary is not None:
        query = query.filter(Employment.salary <= max_salary)
    return query.all()


def dao_create_employment(db, student_no: str, data: dict):
    emp = Employment(student_no=student_no, **data)
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def dao_update_employment(db, emp: Employment, data: dict):
    for key, value in data.items():
        setattr(emp, key, value)
    db.commit()
    db.refresh(emp)
    return emp


def dao_delete_employment(db, emp: Employment):
    emp.is_deleted = True
    db.commit()


# ============================================================
# 就业统计查询（原 statistics_employment_dao，合并到此）
# ============================================================

def _stat_is_del(include_deleted: bool) -> str:
    """统计查询的 is_deleted 过滤条件"""
    return "" if include_deleted else "AND e.is_deleted = 0"


def dao_top5_salary(db, include_deleted: bool = False):
    """查询就业薪资最高的前5名学生"""
    from sqlalchemy import text
    sql = text(f"""
        SELECT e.student_name, e.class_name,
               e.offer_time, e.company, e.salary
        FROM employment e
        WHERE 1=1 {_stat_is_del(include_deleted)}
        ORDER BY e.salary DESC
        LIMIT 5
    """)
    return db.execute(sql).mappings().all()


def dao_employment_duration(db, include_deleted: bool = False):
    """统计每个学生的就业时长（天）"""
    from sqlalchemy import text
    sql = text(f"""
        SELECT e.student_name, e.open_time, e.offer_time,
               DATEDIFF(e.offer_time, e.open_time) AS duration_days
        FROM employment e
        WHERE e.open_time IS NOT NULL
          AND e.offer_time IS NOT NULL
          {_stat_is_del(include_deleted)}
        ORDER BY duration_days ASC
    """)
    return db.execute(sql).mappings().all()


def dao_class_avg_employment_duration(db, include_deleted: bool = False):
    """统计每个班级的平均就业时长"""
    from sqlalchemy import text
    sql = text(f"""
        SELECT e.class_name,
               ROUND(AVG(DATEDIFF(e.offer_time, e.open_time)), 2) AS avg_duration_days
        FROM employment e
        WHERE e.open_time IS NOT NULL
          AND e.offer_time IS NOT NULL
          {_stat_is_del(include_deleted)}
        GROUP BY e.class_name
        ORDER BY avg_duration_days ASC
    """)
    return db.execute(sql).mappings().all()
