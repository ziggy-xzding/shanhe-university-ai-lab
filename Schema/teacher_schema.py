from typing import Literal,Optional,List
from pydantic import BaseModel, Field,ConfigDict


class TeacherCreate(BaseModel):
    tid: Optional[int] = Field(None, description='老师编号（自增，不填由数据库生成）')
    tname:str = Field(...,max_length=20 ,description="姓名")
    tphone:str = Field(...,min_length=11,max_length=11,description='联系电话')
    tsubject:str = Field(...,description='所授科目')
    t_code:Literal['在职','离职','停用'] = '在职'

class TeacherUpdate(BaseModel):
    tname: Optional[str] = Field(None, max_length=20)
    tphone: Optional[str] = Field(None, min_length=11, max_length=11)
    tsubject: Optional[str] = Field(None, max_length=20)


class TeacherOut(BaseModel):
    tid: int
    tname: str
    tphone: str
    tsubject: str
    t_code: str
    model_config = ConfigDict(from_attributes=True)

class TeacherResponse(BaseModel):
    tid: Optional[int] = None
    tname: Optional[str] = None
    tphone: Optional[str] = None
    tsubject: Optional[str] = None
    t_code: Optional[str] = None
    message: str
    data: Optional[List[TeacherOut]] = None
    model_config = ConfigDict(from_attributes=True)