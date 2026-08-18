"""
学生 Pydantic 校验模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    """创建学生 — 12个字段"""
    student_no: str = Field(..., max_length=20, description="学生编号")
    name: str = Field(..., max_length=20, description="姓名")
    class_id: Optional[int] = Field(None, description="班级ID")
    hometown: Optional[str] = Field(None, max_length=50, description="籍贯")
    graduate_school: Optional[str] = Field(None, max_length=50, description="毕业院校")
    major: Optional[str] = Field(None, max_length=50, description="专业")
    enrollment_time: Optional[datetime] = Field(None, description="入学时间")
    graduation_time: Optional[datetime] = Field(None, description="毕业时间")
    education: Optional[str] = Field(None, max_length=10, description="学历")
    advisor_id: Optional[int] = Field(None, description="顾问编号")
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, max_length=3, description="性别")


class StudentUpdate(BaseModel):
    """更新学生 — 全部字段可选"""
    student_no: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=20)
    class_id: Optional[int] = None
    hometown: Optional[str] = Field(None, max_length=50)
    graduate_school: Optional[str] = Field(None, max_length=50)
    major: Optional[str] = Field(None, max_length=50)
    enrollment_time: Optional[datetime] = None
    graduation_time: Optional[datetime] = None
    education: Optional[str] = Field(None, max_length=10)
    advisor_id: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = Field(None, max_length=5)


class StudentResponse(BaseModel):
    """学生响应"""
    id: int
    student_no: str
    name: str
    class_id: Optional[int]
    hometown: Optional[str]
    graduate_school: Optional[str]
    major: Optional[str]
    enrollment_time: Optional[datetime]
    graduation_time: Optional[datetime]
    education: Optional[str]
    advisor_id: Optional[int]
    age: Optional[int]
    gender: Optional[str]

    model_config = {"from_attributes": True}
