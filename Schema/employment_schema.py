"""
就业 Pydantic 校验模型 — P5 负责
=================================
三层 Schema 设计：
  EmploymentCreate  → 创建/更新就业信息（POST Upsert 用）
  EmploymentUpdate  → 单独修改就业信息（PUT 用）
  EmploymentResponse → API 返回给前端的格式

设计原因：
  - Create 和 Update 分开：Create 所有字段都可选（Upsert），Update 粒度更细
  - from_attributes=True：让 Pydantic 能直接从 ORM 对象提取字段
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# 创建（Upsert）— 所有字段可选
# ============================================================
class EmploymentCreate(BaseModel):
    """
    创建/更新就业信息（POST /employment/students/{student_id}）
    存在则更新，不存在则新建。
    所有字段可选 — 兼容 Upsert 的"选择性更新"场景。
    company/salary 的业务必填校验在 API 层处理（仅新增时强制）。
    """
    student_name: Optional[str] = Field(None, max_length=20, description="学生姓名（冗余）")
    class_no: Optional[str] = Field(None, max_length=20, description="班级编号（外键）")
    class_name: Optional[str] = Field(None, max_length=50, description="班级名称（冗余）")
    open_time: Optional[datetime] = Field(None, description="就业开放时间")
    offer_time: Optional[datetime] = Field(None, description="Offer下发时间")
    company: Optional[str] = Field(None, max_length=100, description="就业公司（新增时必填）")
    salary: Optional[Decimal] = Field(None, description="就业薪资（新增时必填，必须大于0）")


# ============================================================
# 更新 — 所有字段可选
# ============================================================
class EmploymentUpdate(BaseModel):
    """
    单独修改就业信息（PUT /employment/{employment_id}）
    exclude_unset=True 确保只更新用户实际传入的字段
    """
    student_name: Optional[str] = Field(None, max_length=20)
    class_no: Optional[str] = Field(None, max_length=20, description="班级编号（外键，修改时校验存在性）")
    class_name: Optional[str] = Field(None, max_length=50)
    open_time: Optional[datetime] = None
    offer_time: Optional[datetime] = None
    company: Optional[str] = Field(None, max_length=100)
    salary: Optional[Decimal] = None


# ============================================================
# 响应 — 返回给前端
# ============================================================
class EmploymentResponse(BaseModel):
    """就业信息响应体"""
    id: int
    student_no: Optional[str] = None
    student_name: Optional[str] = None
    class_no: Optional[str] = None
    class_name: Optional[str] = None
    open_time: Optional[datetime]
    offer_time: Optional[datetime]
    company: Optional[str]
    salary: Optional[Decimal]

    # Pydantic v2 的新写法，替代原来的 orm_mode = True
    model_config = {"from_attributes": True}


# ============================================================
# 就业统计响应模型（原 statistics_employment_schema，合并到此）
# ============================================================

class Top5Salary(BaseModel):
    """就业薪资前5名学生"""
    student_name: str
    class_name: Optional[str]
    offer_time: Optional[datetime]
    company: Optional[str]
    salary: Optional[Decimal]

    model_config = {"from_attributes": True}


class EmploymentDuration(BaseModel):
    """单个学生就业时长"""
    student_name: str
    open_time: Optional[datetime]
    offer_time: Optional[datetime]
    duration_days: Optional[int]

    model_config = {"from_attributes": True}


class ClassAvgDuration(BaseModel):
    """班级平均就业时长"""
    class_name: str
    avg_duration_days: Optional[float]

    model_config = {"from_attributes": True}
