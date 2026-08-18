# Schema/Score.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ScoreBase(BaseModel):
    student_no: str = Field(..., min_length=1, max_length=20, description="学号")
    exam_seq: int = Field(..., ge=1, description="考试序次")
    score: float = Field(..., ge=0, le=100, description="成绩分数")


class ScoreCreate(ScoreBase):
    """创建成绩请求模型"""
    pass


class ScoreUpdate(BaseModel):
    student_no: str = Field(..., min_length=1, max_length=20, description="学号")
    exam_seq: int = Field(..., ge=1, description="考试序次")
    new_score: float = Field(..., ge=0, le=100, description="新成绩分数")


class ScoreResponse(BaseModel):
    id: int
    student_no: str
    exam_seq: int
    score: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
