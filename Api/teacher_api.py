from typing import List

from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from DAO import teacher_dao
from DAO.db import get_db
from DAO.teacher_dao import dao_update_teacher_batch
from Schema.teacher_schema import TeacherCreate, TeacherUpdate, TeacherResponse

teacher_router = APIRouter(prefix='/teacher',tags=['老师管理模块'])

# 获取老师信息
@teacher_router.get('/teachers',summary='获取老师信息')
async def get_teacher(db:Session = Depends(get_db)):
    return teacher_dao.dao_get_teacher(db)


# 创建老师信息
@teacher_router.post('/teachercrate',status_code=201,summary='创建老师信息')
async def create_teacher(data:TeacherCreate,db:Session = Depends(get_db)):
    if data.tid and teacher_dao.dao_get_teacher_byid(db, data.tid):
        raise HTTPException(status_code=400, detail=f'老师编号{data.tid}已存在')
    teacher_dao.dao_add_teacher(db, data.model_dump())
    return {"message": "创建成功"}


# 批量新增
@teacher_router.post('/teachercrate_batch',
                     status_code=201,
                     summary='批量新增老师'
                     )
async def create_teacher_batch(data:List[TeacherCreate],db:Session = Depends(get_db)):
    try:
        dao_update_teacher_batch(db,data)
        return {"message": "批量创建成功"}
    except Exception as e:
        raise HTTPException(status_code=500,detail=f'批量创建失败：{str(e)}')


# 根据ID获取老师
@teacher_router.get('/teacher/{teacher_id}',summary='根据id获取老师信息')
async def update_teacher(teacher_id:int,db:Session = Depends(get_db)):
    teacher = teacher_dao.dao_get_teacher_byid(db,teacher_id)
    if not teacher:
        raise HTTPException(status_code=404,detail='老师不存在')
    return teacher


# 更新老师信息
@teacher_router.put('/teacher/{teacher_id}', summary='更新老师信息')
async def update_teacher(teacher_id: int,data: TeacherUpdate,db: Session = Depends(get_db)):
    rows = teacher_dao.dao_update_teacher(db, teacher_id, data)
    if rows:
        return {"message": f"更新成功，影响了 {rows} 行"}
    raise HTTPException(status_code=404, detail='老师不存在或无有效更新字段')


# 删除老师
@teacher_router.delete('/teacher/{teacher_id}', summary='删除老师')
async def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = teacher_dao.dao_get_teacher_byid(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="老师不存在")
    if teacher.t_is_delete:
        raise HTTPException(status_code=400, detail="该老师已被删除")
    teacher_dao.dao_delete_teacher(db, teacher)
    return {"message": f"老师 '{teacher.tname}' 已删除"}


