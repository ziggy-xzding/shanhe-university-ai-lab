"""
部门 Pydantic 校验模型
"""
from typing import Optional
from pydantic import BaseModel, Field

# 部门编号、名称、部门主管、办公位置、联系电话、状态
class DepartmentCreate(BaseModel):
    dept_no: str = Field(...,
                         max_length=20,
                         description="部门编号"
                         )
    dept_name: str = Field(...,
                      max_length=50,
                      description="部门名称"
                      )
    dept_manager: str= Field(...,
                                   max_length=20,
                                   description="部门负责人"
                                   )
    dept_location:str= Field(...,
                                   max_length=50,
                                   description="办公位置"
                                   )


    dept_phone:str= Field(default=" ",
                                   max_length=20,
                                   description="联系电话"
                                   )


class DepartmentUpdate(BaseModel):
    dept_no: Optional[str] = Field(None, max_length=20)
    dept_name: Optional[str] = Field(None, max_length=50)
    dept_manager: Optional[str] = Field(None, max_length=20)
    dept_location: Optional[str] = Field(None, max_length=20)
    dept_phone: Optional[str] = Field(None, max_length=200)


class DepartmentResponse(BaseModel):
    id: int
    dept_no: str
    dept_name: str
    dept_manager: Optional[str]
    dept_location: Optional[str]
    dept_phone: Optional[str]


    model_config = {"from_attributes": True}
