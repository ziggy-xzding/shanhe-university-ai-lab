import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


class _ConsultantValidatorMixin(BaseModel):
    """公共字段校验逻辑，由 ConsultantCreate / ConsultantUpdate 共同继承，避免重复定义。"""

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "" and not _EMAIL_RE.match(v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("phone", mode="before", check_fields=False)
    @classmethod
    def _check_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("手机号只能包含数字")
        return v


class ConsultantBase(BaseModel):
    model_config = {"from_attributes": True}

    consultant_id: int
    consultant_no: str
    name: str
    gender: str
    phone: str
    email: Optional[str] = None
    dept_no: str
    title: str
    region: Optional[str] = None
    create_time: datetime
    update_time: datetime


class ConsultantCreate(_ConsultantValidatorMixin):
    consultant_no: str = Field(..., min_length=1, max_length=10, examples=["CON001"])
    name: str = Field(..., min_length=1, max_length=20, examples=["张三"])
    gender: Literal["男", "女"] = Field(..., examples=["男"])
    phone: str = Field(..., min_length=11, max_length=11, examples=["13800138000"])
    email: Optional[str] = Field(None, examples=["zhangsan@example.com"])
    dept_no: str = Field(..., examples=["D001"])
    title: str = Field(..., examples=["高级顾问"])
    region: Optional[str] = Field(None, examples=["华北"])


class ConsultantUpdate(_ConsultantValidatorMixin):
    consultant_no: Optional[str] = Field(None, max_length=10, examples=["CON001"])
    name: Optional[str] = Field(None, max_length=20, examples=["张三"])
    gender: Optional[Literal["男", "女"]] = Field(None, examples=["男"])
    phone: Optional[str] = Field(None, min_length=11, max_length=11, examples=["13800138000"])
    email: Optional[str] = Field(None, examples=["zhangsan@example.com"])
    dept_no: Optional[str] = Field(None, examples=["D001"])
    title: Optional[str] = Field(None, examples=["高级顾问"])
    region: Optional[str] = Field(None, examples=["华北"])


class ConsultantManagerResponse(BaseModel):
    """查询顾问直属领导的响应模型"""
    model_config = {"from_attributes": True}

    consultant_id: int
    consultant_no: str
    consultant_name: str
    consultant_title: str
    dept_no: str
    dept_name: str
    manager_name: str
