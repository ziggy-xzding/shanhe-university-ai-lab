"""
学生管理 API 路由
==================
提供学生信息的增删改查 RESTful 接口。
支持按编号、姓名（模糊）、班级筛选。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from DAO.db import get_db
from Schema.student_schema import StudentCreate, StudentUpdate, StudentResponse
from DAO import student_dao
from DAO.student_dao import get_students_overage,get_sex_num

approuter_student = APIRouter(tags=['学生信息模块'])


@approuter_student.get("/students", response_model=List[StudentResponse], summary="获取学生列表")
def list_students(
    student_no: Optional[str] = Query(None, description="按学生编号筛选"),
    name: Optional[str] = Query(None, description="按学生姓名筛选（模糊匹配）"),
    class_id: Optional[int] = Query(None, description="按班级ID筛选"),
    db: Session = Depends(get_db),
):
    """获取学生列表，支持多条件组合筛选"""
    return student_dao.dao_get_all_students(db, student_no, name, class_id)


@approuter_student.post("/students", response_model=StudentResponse, status_code=201, summary="创建学生")
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    """创建新学生，student_no 必须唯一"""
    if student_dao.dao_get_student_by_no(db, data.student_no):
        raise HTTPException(status_code=400, detail=f"学生编号 '{data.student_no}' 已存在")
    return student_dao.dao_create_student(db, data.model_dump())


@approuter_student.get("/students/{student_id}", response_model=StudentResponse, summary="获取学生详情")
def get_student(student_id: int, db: Session = Depends(get_db)):
    """根据ID获取学生"""
    student = student_dao.dao_get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    return student


@approuter_student.put("/students/{student_id}", response_model=StudentResponse, summary="更新学生")
def update_student(student_id: int, data: StudentUpdate, db: Session = Depends(get_db)):
    """更新学生信息（部分更新）"""
    student = student_dao.dao_get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "student_no" in update_data:
        conflict = student_dao.dao_get_student_by_no(db, update_data["student_no"])
        if conflict and conflict.id != student_id:
            raise HTTPException(status_code=400, detail=f"学生编号 '{update_data['student_no']}' 已被占用")
    return student_dao.dao_update_student(db, student, update_data)


@approuter_student.delete("/students/{student_id}", summary="逻辑删除学生")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    """逻辑删除学生"""
    student = student_dao.dao_get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    student_dao.dao_delete_student(db, student)
    return {"message": f"学生 '{student.name}' 已删除"}


@approuter_student.get('/statistics/overage',summary='查询超龄学生')
def get_stu_over(age: int, db=Depends(get_db)):
        result = get_students_overage(age, db)
        return {"msg": "查询成功", 'data': result}

# 统计人数
@approuter_student.get('/statistics/class_sex_num',summary='统计人数')
def get_sex(db=Depends(get_db)):
    result = get_sex_num(db)
    return {"msg": "统计成功", "data": result}