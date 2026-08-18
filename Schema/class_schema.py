"""
班级 Pydantic 校验模型,请求响应模型层
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    """创建班级请求体"""
    class_no: str = Field(..., max_length=20, description="班级编号")
    name: str = Field(..., max_length=50, description="班级名称")
    start_date: Optional[datetime] = Field(None, description="开课时间")
    head_teacher_id: Optional[int] = Field(None,  description="班主任")
    instructor_id: Optional[int] = Field(None,  description="授课老师")


class ClassUpdate(BaseModel):
    """更新班级请求体"""
    class_no: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=50)
    start_date: Optional[datetime] = None
    head_teacher_id: Optional[int] = None
    instructor_id: Optional[int] = None


class ClassResponse(BaseModel):
    """班级响应模型"""
    id: int
    class_no: str
    name: str
    start_date: Optional[datetime]
    head_teacher_id: Optional[int]
    instructor_id: Optional[int]

from pydantic import ConfigDict
model_config = ConfigDict(from_attributes=True)
