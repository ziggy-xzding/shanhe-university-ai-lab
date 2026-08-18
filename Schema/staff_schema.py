"""管理员职员账户接口模型。"""

from typing import Literal

from pydantic import BaseModel, Field

StaffRole = Literal[
    "admin", "college_admin", "academic_admin", "student_affairs",
    "counselor", "teacher", "archive_admin", "staff",
]


class StaffAccountCreate(BaseModel):
    staff_no: str = Field(..., max_length=20)
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., max_length=50)
    role: StaffRole
    teacher_id: int | None = None
    college_id: int | None = None
    department_id: int | None = None
    position: str | None = Field(None, max_length=100)
    status: Literal["active", "disabled"] = "active"


class StaffAccountUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=50)
    role: StaffRole | None = None
    teacher_id: int | None = None
    college_id: int | None = None
    department_id: int | None = None
    position: str | None = Field(None, max_length=100)
    status: Literal["active", "disabled"] | None = None


class ResetPasswordRequest(BaseModel):
    password: str = Field("Demo@123456", min_length=6, max_length=128)
