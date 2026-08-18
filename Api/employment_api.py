"""
就业管理 API 路由 — P5 负责
=============================
提供就业信息的 RESTful API。
API 层职责：处理 HTTP 请求/响应，调用 DAO 层完成数据库操作。

端点一览：
  GET    /employment                          → 多条件筛选列表
  GET    /employment/students/{student_no}    → 查单个学生的就业信息
  GET    /employment/class/{class_id}         → 查班级所有学生的就业信息
  POST   /employment/students/{student_no}    → Upsert（存在则更新，否则新建）
  PUT    /employment/{employment_id}          → 修改就业信息
  DELETE /employment/{employment_id}          → 逻辑删除

设计亮点：
  1. POST 接口实现 Upsert — 前端不需要先查存在再决定用 POST 还是 PUT
  2. 冗余字段 (student_name, class_name) — 配合按班级查询，避免 JOIN
  3. 多条件筛选 — 公司模糊搜索 + 薪资范围，后端过滤
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from DAO.db import get_db
from Schema.employment_schema import (
    EmploymentCreate,
    EmploymentUpdate,
    EmploymentResponse,
    Top5Salary,
    EmploymentDuration,
    ClassAvgDuration,
)
from DAO import employment_dao
from Model.class_table import Class

# 创建 APIRouter 实例（组长会在 main.py 中注册）
approuter_employment = APIRouter(tags=["就业信息模块"])


# ============================================================
# 1. GET /employment — 就业信息列表（多条件筛选）
# ============================================================
@approuter_employment.get(
    "/employment",
    response_model=List[EmploymentResponse],
    summary="就业信息列表（多条件筛选）",
)
def list_employment(
    student_name: Optional[str] = Query(None, description="按学生姓名精确筛选"),
    company: Optional[str] = Query(None, description="按公司名称模糊搜索"),
    min_salary: Optional[float] = Query(None, description="最低薪资"),
    max_salary: Optional[float] = Query(None, description="最高薪资"),
    include_deleted: bool = Query(False, description="是否包含已删除记录"),
    db: Session = Depends(get_db),
):
    """
    查询就业信息，支持多条件筛选：
    - student_name：精确匹配
    - company：模糊搜索（LIKE '%xxx%'）
    - min_salary / max_salary：薪资范围
    - include_deleted：传 true 可查看已删除记录（回收站）

    示例：
      GET /employment?company=华为           → 搜公司名含"华为"的
      GET /employment?include_deleted=true   → 包含已删除的
    """
    return employment_dao.dao_list_employment(
        db, student_name, company, min_salary, max_salary, include_deleted
    )


# ============================================================
# 2. GET /employment/students/{student_no} — 查单个学生
# ============================================================
@approuter_employment.get(
    "/employment/students/{student_no}",
    response_model=Optional[EmploymentResponse],
    summary="获取学生就业信息",
)
def get_student_employment(
    student_no: str,
    include_deleted: bool = Query(False, description="是否包含已删除记录"),
    db: Session = Depends(get_db),
):
    """
    根据学号获取就业信息。
    如果没有就业记录，返回 null（前端据此判断是否展示"添加"按钮）。
    """
    return employment_dao.dao_get_employment_by_student(db, student_no, include_deleted)


# ============================================================
# 3. GET /employment/class/{class_id} — 按班级查询
# ============================================================
@approuter_employment.get(
    "/employment/class/{class_id}",
    response_model=List[EmploymentResponse],
    summary="获取班级就业信息",
)
def get_class_employment(
    class_id: int,
    include_deleted: bool = Query(False, description="是否包含已删除记录"),
    db: Session = Depends(get_db),
):
    """
    根据班级ID获取该班所有学生的就业信息。
    """
    cls = db.query(Class).filter(
        Class.id == class_id,
        Class.is_deleted == False,
    ).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    return employment_dao.dao_get_employment_by_class(db, cls.name, include_deleted)


# ============================================================
# 4. POST /employment/students/{student_no} — Upsert
# ============================================================
@approuter_employment.post(
    "/employment/students/{student_no}",
    response_model=EmploymentResponse,
    status_code=201,
    summary="添加/更新就业信息（Upsert）",
)
def upsert_employment(
    student_no: str,
    data: EmploymentCreate,
    db: Session = Depends(get_db),
):
    """
    为学生添加或更新就业信息。

    **Upsert 逻辑**（面试常考点）：
      1. 先查该学生是否已有就业记录
      2. 有 → 更新已有记录（PUT 语义）
      3. 无 → 新建记录（POST 语义）

    **前置校验**：学生必须存在。
    """
    # 前置检查：学生是否存在
    if not employment_dao.dao_get_student(db, student_no):
        raise HTTPException(status_code=404, detail=f"学号={student_no} 不存在")

    # 班级编号存在性校验（无论新增还是更新，只要传了 class_no 就校验）
    if data.class_no:
        cls = db.query(Class).filter(
            Class.class_no == data.class_no, Class.is_deleted == 0
        ).first()
        if not cls:
            raise HTTPException(status_code=400, detail=f"班级编号 '{data.class_no}' 不存在，请使用已有班级")

    # 新增场景的业务校验：必须有公司名和薪资
    existing = employment_dao.dao_get_employment_by_student(db, student_no)
    if not existing and not data.company:
        raise HTTPException(status_code=400, detail="新增就业记录时，公司名不能为空")
    if not existing and (data.salary is None or data.salary <= 0):
        raise HTTPException(status_code=400, detail="新增就业记录时，薪资必须大于0")

    if existing:
        # 已存在 → 更新
        return employment_dao.dao_update_employment(
            db, existing, data.model_dump(exclude_unset=True)
        )
    else:
        # 不存在 → 新建
        return employment_dao.dao_create_employment(
            db, student_no, data.model_dump()
        )


# ============================================================
# 5. PUT /employment/{employment_id} — 单独修改
# ============================================================
@approuter_employment.put(
    "/employment/{employment_id}",
    response_model=EmploymentResponse,
    summary="修改就业信息",
)
def update_employment(
    employment_id: int,
    data: EmploymentUpdate,
    db: Session = Depends(get_db),
):
    """
    按就业记录ID修改就业信息。
    只更新用户传入的字段（exclude_unset=True），其余保持不变。
    """
    emp = employment_dao.dao_get_employment_by_id(db, employment_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"就业记录ID={employment_id} 不存在")

    # 业务校验：薪资不能为0或负数
    dumped = data.model_dump(exclude_unset=True)
    if "salary" in dumped and dumped["salary"] is not None and dumped["salary"] <= 0:
        raise HTTPException(status_code=400, detail="薪资必须大于0")
    # 业务校验：班级编号必须存在
    if "class_no" in dumped and dumped["class_no"] is not None:
        cls = db.query(Class).filter(Class.class_no == dumped["class_no"], Class.is_deleted == 0).first()
        if not cls:
            raise HTTPException(status_code=400, detail=f"班级编号 '{dumped['class_no']}' 不存在，请使用已有班级")

    return employment_dao.dao_update_employment(db, emp, dumped)


# ============================================================
# 6. DELETE /employment/{employment_id} — 逻辑删除
# ============================================================
@approuter_employment.delete(
    "/employment/{employment_id}",
    summary="删除就业信息",
)
def delete_employment(employment_id: int, db: Session = Depends(get_db)):
    """
    逻辑删除就业记录（is_deleted = True）。
    数据仍然保留在数据库，可随时恢复。
    """
    emp = employment_dao.dao_get_employment_by_id(db, employment_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"就业记录ID={employment_id} 不存在")

    employment_dao.dao_delete_employment(db, emp)
    return {"message": f"删除成功，影响了1行"}


# ============================================================
# 7-9. 就业统计（原 statistics_employment_api，合并到就业模块）
# ============================================================

@approuter_employment.get(
    "/statistics/employment/top5-salary",
    response_model=List[Top5Salary],
    summary="就业薪资TOP5",
)
def statistics_top5_salary(
    include_deleted: bool = Query(False, description="是否包含已删除记录"),
    db: Session = Depends(get_db),
):
    """查询就业薪资最高的前5名学生。"""
    return [Top5Salary(**row) for row in employment_dao.dao_top5_salary(db, include_deleted)]


@approuter_employment.get(
    "/statistics/employment/duration",
    response_model=List[EmploymentDuration],
    summary="学生就业时长",
)
def statistics_employment_duration(
    include_deleted: bool = Query(False, description="是否包含已删除记录"),
    db: Session = Depends(get_db),
):
    """统计每个学生的就业时长（天）= offer_time - open_time。"""
    return [
        EmploymentDuration(**row)
        for row in employment_dao.dao_employment_duration(db, include_deleted)
    ]


@approuter_employment.get(
    "/statistics/employment/class-avg-duration",
    response_model=List[ClassAvgDuration],
    summary="班级平均就业时长",
)
def statistics_class_avg_employment_duration(
    include_deleted: bool = Query(False, description="是否包含已删除记录"),
    db: Session = Depends(get_db),
):
    """统计每个班级的平均就业时长。"""
    return [
        ClassAvgDuration(**row)
        for row in employment_dao.dao_class_avg_employment_duration(db, include_deleted)
    ]
