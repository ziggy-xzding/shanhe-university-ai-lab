"""
班级管理 API 路由
==================
提供班级信息的增删改查 RESTful 接口。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from DAO.db import get_db
from Schema.class_schema import ClassCreate, ClassUpdate, ClassResponse
from DAO import class_dao
from DAO.class_dao import dao_update_class


approuter_class = APIRouter(tags=["班级管理模块"])

from Model.class_table import Class
@approuter_class.post("/classes", response_model=ClassResponse, status_code=201, summary="创建班级")
def create_class(data: ClassCreate, db: Session = Depends(get_db)):
    """创建新班级，class_no 必须唯一"""
    exist_class=db.query(Class).filter(Class.class_no==data.class_no).first()
    if exist_class:
        raise HTTPException(status_code=400, detail=f"班级编号 '{data.class_no}' 已存在")
    return class_dao.dao_create_class(db, data.model_dump())


from DAO.class_dao import dao_get_class
@approuter_class.get("/classes",summary="获取班级详情")
def get_class(id:int|None=None,db=Depends(get_db)):
    classinfo=dao_get_class(id, db)
    if classinfo:
        return classinfo
    raise HTTPException(status_code=404,detail="查询的班级不存在")


@approuter_class.put("/classes/{class_id}")
async def update_class(id:int,c:ClassUpdate,db=Depends(get_db)):
    rows=dao_update_class(id,c,db)
    if rows:
        return f'更新成功，影响了{rows}行'
    raise HTTPException(status_code=404,detail='更新失败')



from DAO.class_dao import dao_delete_class
@approuter_class.delete("/classes/{id}")
async def update_classes(id:int,db=Depends(get_db)):
    rows=dao_delete_class(id, db)
    if rows:
        return f'删除成功，影响了{rows}行'
    raise HTTPException(status_code=404,detail='删除失败')

