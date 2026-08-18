"""学生成长 Agent 的请求模型。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("消息不能为空")
        return value


class AgentReportRequest(BaseModel):
    report_type: Literal["latest_score", "weekly", "manual"] = "latest_score"
