"""
部门管理 API
"""
from sqlalchemy import func
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from DAO.db import get_db
from Schema.department_schema import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from DAO import department_dao
from Model.department_table import Department
from Model.consultant_table import Consultant


app_department = APIRouter(tags=["部门管理模块"])


@app_department.post(
    "/departments",
    response_model=List[DepartmentResponse],
    status_code=201,
    summary="批量创建部门",
    description="一次性可创建多条部门记录。",
)
def create_department(data: List[DepartmentCreate], db: Session = Depends(get_db)):
    """批量创建部门"""
    try:
        results = []
        for item in data:
            if department_dao.dao_get_by_no(db, item.dept_no):
                raise HTTPException(400, f"部门编号 '{item.dept_no}' 已存在")
            results.append(department_dao.dao_create(db, item.model_dump()))
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量创建部门失败: {str(e)}")


@app_department.get(
    "/departments",
    response_model=List[DepartmentResponse],
    summary="部门列表",
    description="查询所有未删除的部门信息。",
)
def list_departments(db: Session = Depends(get_db)):
    """获取部门列表"""
    try:
        return department_dao.dao_get_all(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取部门列表失败: {str(e)}")


@app_department.get(
    "/departments/{dept_id}",
    response_model=DepartmentResponse,
    summary="部门详情",
    description="通过输入dept_id查询部门信息。",
)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    """查询单个部门"""
    try:
        dept = department_dao.dao_get_by_id(db, dept_id)
        if not dept:
            raise HTTPException(404, "部门不存在")
        return dept
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询部门失败: {str(e)}")


@app_department.get(
    "/departments/{dept_no}/count",
    summary="部门人数",
    description="输入dept_no查询部门人数。",
)
def get_department_count(dept_no: str, db: Session = Depends(get_db)):
    """查询部门人数统计"""
    try:
        result = db.query(
            Department.dept_no,
            Department.dept_name,
            Department.dept_manager,
            func.count(Consultant.consultant_id).label("consultant_count")
        ).join(
            Consultant,
            (Department.dept_no == Consultant.dept_no) & (Consultant.is_deleted == 0)
        ).filter(
            Department.dept_no == dept_no,
            Department.is_deleted == False
        ).group_by(
            Department.dept_no,
            Department.dept_name,
            Department.dept_manager
        ).first()
        if not result:
            raise HTTPException(404, f"部门编号 '{dept_no}' 不存在或无顾问")
        return {
            '部门编号': result.dept_no,
            '部门名称': result.dept_name,
            '部门主管': result.dept_manager,
            '部门人数': result.consultant_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询部门人数失败: {str(e)}")


@app_department.put(
    "/departments/{dept_id}",
    response_model=DepartmentResponse,
    summary="更新部门",
    description="根据dept_id部分更新字段，只修改请求体中实际传入的字段，其余保持原值。",
)
def update_department(dept_id: int, data: DepartmentUpdate, db: Session = Depends(get_db)):
    """更新部门信息"""
    try:
        dept = department_dao.dao_get_by_id(db, dept_id)
        if not dept:
            raise HTTPException(404, "部门不存在")
        update_data = data.model_dump(exclude_unset=True)
        if "dept_no" in update_data:
            conflict = department_dao.dao_get_by_no(db, update_data["dept_no"])
            if conflict and conflict.id != dept_id:
                raise HTTPException(400, f"部门编号 '{update_data['dept_no']}' 已被占用")
        return department_dao.dao_update(db, dept, update_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新部门失败: {str(e)}")


@app_department.delete(
    "/departments/{dept_id}",
    summary="删除部门",
    description="将指定部门标记为已删除，数据仍保留在数据库中，可随时恢复。",
)
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    """逻辑删除部门"""
    try:
        dept = department_dao.dao_get_by_id(db, dept_id)
        if not dept:
            raise HTTPException(404, "部门不存在")
        department_dao.dao_delete(db, dept)
        return {"message": f"部门 '{dept.dept_name}' 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除部门失败: {str(e)}")
