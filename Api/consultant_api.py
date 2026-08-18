from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from DAO.db import get_db
from typing import List, Optional
from Schema.consultant_schema import ConsultantBase, ConsultantCreate, ConsultantUpdate, ConsultantManagerResponse
from DAO.consultant_dao import (
    get_consultant_list,
    get_consultant_total,
    get_consultant_by_id,
    create_consultant_item,
    update_consultant_item,
    batch_create_consultants,
    delete_consultant_item,
    get_deleted_consultants,
    restore_consultant_item,
    get_consultant_manager,
)
from Api.api_utils import service_call

router = APIRouter(prefix="/consultant", tags=["顾问管理模块"])


@router.get(
    "/list",
    response_model=List[ConsultantBase],
    summary="获取顾问列表（支持分页和筛选）",
    description="返回所有未删除的顾问信息。可选按部门编号筛选、按姓名模糊搜索、分页。响应头 X-Total-Count 携带满足条件的总条数。",
)
async def list_consultants(
    response: Response,
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(100, ge=1, le=500, description="返回条数上限"),
    dept_no: Optional[str] = Query(None, description="按部门编号筛选"),
    keyword: Optional[str] = Query(None, description="按姓名模糊搜索"),
    db: Session = Depends(get_db),
):
    """分页查询顾问列表，支持按部门和姓名筛选。响应头 X-Total-Count 返回总条数。"""
    async with service_call("获取顾问列表"):
        consultants = get_consultant_list(db, skip=skip, limit=limit, dept_no=dept_no, keyword=keyword)
        total = get_consultant_total(db, dept_no=dept_no, keyword=keyword)
        response.headers["X-Total-Count"] = str(total)
        return consultants


@router.get(
    "/deleted",
    response_model=List[ConsultantBase],
    summary="查询已删除的顾问列表",
    description="返回所有 is_deleted=True 的顾问记录，按删除时间倒序。",
)
async def list_deleted_consultants(db: Session = Depends(get_db)):
    """查询回收站中的顾问。"""
    async with service_call("查询已删除顾问"):
        return get_deleted_consultants(db)


@router.patch(
    "/{consultant_id}/restore",
    response_model=ConsultantBase,
    summary="恢复已删除的顾问",
    description="将指定顾问从回收站恢复为正常状态，只能操作已删除的记录。",
    responses={404: {"description": "顾问不存在或未被删除"}},
)
async def restore_consultant(consultant_id: int, db: Session = Depends(get_db)):
    """从回收站恢复顾问：设置 is_deleted=False。"""
    async with service_call("恢复顾问"):
        return restore_consultant_item(db, consultant_id)


@router.get(
    "/{consultant_no}/manager",
    response_model=ConsultantManagerResponse,
    summary="查询顾问的直属领导",
    description="根据顾问编号（如 CON001），通过部门编号关联 departments 表，返回该顾问所在部门的负责人信息。",
    responses={404: {"description": "顾问不存在或所属部门不存在"}},
)
async def get_manager(consultant_no: str, db: Session = Depends(get_db)):
    """按顾问编号查询其直属领导（部门主管）。"""
    async with service_call("查询直属领导"):
        return get_consultant_manager(db, consultant_no)


@router.get(
    "/{consultant_id}",
    response_model=ConsultantBase,
    summary="查询单个顾问",
    description="根据顾问 ID 返回完整信息。",
    responses={404: {"description": "顾问不存在"}},
)
async def get_consultant(consultant_id: int, db: Session = Depends(get_db)):
    """按 ID 查询顾问详情。"""
    async with service_call("查询顾问"):
        return get_consultant_by_id(db, consultant_id)


@router.post(
    "",
    response_model=ConsultantBase,
    status_code=201,
    summary="新增单个顾问",
    description="向系统添加一名顾问，必填字段：姓名、性别、手机号、部门编号、职称。部门编号必须真实存在。",
    responses={400: {"description": "部门不存在或参数校验失败"}},
)
async def create_consultant(consultant: ConsultantCreate, db: Session = Depends(get_db)):
    """创建一条顾问记录。部门编号会在 departments 表中校验。"""
    async with service_call("创建顾问", value_error_status=400):
        return create_consultant_item(db, consultant)


@router.post(
    "/batch-create",
    response_model=List[ConsultantBase],
    status_code=201,
    summary="批量新增顾问",
    description="一次性创建多条顾问记录，所有部门的 dept_no 都会逐一校验。",
    responses={400: {"description": "部门不存在或参数校验失败"}},
)
async def batch_create_consultant(
    consultants: List[ConsultantCreate], db: Session = Depends(get_db)
):
    """批量创建顾问，同一事务提交，部门编号全部校验通过后才写入。"""
    async with service_call("批量创建顾问", value_error_status=400):
        return batch_create_consultants(db, consultants)


@router.put(
    "/{consultant_id}",
    response_model=ConsultantBase,
    summary="更新顾问信息",
    description="根据顾问 ID 部分更新字段。如果修改部门编号，会校验新部门是否存在。",
    responses={400: {"description": "部门不存在"}, 404: {"description": "顾问不存在"}},
)
async def update_consultant(
    consultant_id: int, consultant: ConsultantUpdate, db: Session = Depends(get_db)
):
    """按 ID 部分更新顾问信息。变更 dept_no 时自动校验部门存在性。"""
    async with service_call("更新顾问"):
        # ValueError 需区分 404（记录不存在）和 400（业务校验失败），先转成 HTTPException
        # service_call 会透传 HTTPException，再兜底处理其他异常
        try:
            return update_consultant_item(db, consultant_id, consultant)
        except ValueError as e:
            msg = str(e)
            raise HTTPException(status_code=404 if "顾问不存在" in msg else 400, detail=msg)


@router.delete(
    "/{consultant_id}",
    summary="删除顾问（伪删除）",
    description="将指定顾问标记为已删除，数据仍保留在数据库中，可随时恢复。",
    responses={404: {"description": "顾问不存在"}},
)
async def delete_consultant(consultant_id: int, db: Session = Depends(get_db)):
    """逻辑删除：设置 is_deleted=True，不物理删除记录。"""
    async with service_call("删除顾问"):
        delete_consultant_item(db, consultant_id)
        return {"message": f"顾问（ID={consultant_id}）已删除"}
