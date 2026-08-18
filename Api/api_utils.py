"""
通用 API 异常处理工具
====================
提供 service_call 异步上下文管理器，统一将 DAO/Service 层抛出的异常
映射为标准 HTTP 响应，消除各接口重复的 try/except 样板代码。

使用示例：
    async with service_call("获取顾问列表"):
        return get_consultant_list(db)

    # ValueError 默认映射 404；若业务上应返回 400，传 value_error_status=400
    async with service_call("创建顾问", value_error_status=400):
        return create_consultant_item(db, data)

    # 需要区分 404/400 的特殊 ValueError，在 async with 内先转成 HTTPException
    async with service_call("更新顾问"):
        try:
            return update_consultant_item(db, id, data)
        except ValueError as e:
            msg = str(e)
            raise HTTPException(404 if "不存在" in msg else 400, detail=msg)
"""
from contextlib import asynccontextmanager
from fastapi import HTTPException


@asynccontextmanager
async def service_call(action: str, value_error_status: int = 404):
    """
    统一处理 DAO/Service 层异常并转换为 HTTPException。

    - HTTPException  → 直接透传，不做修改
    - ValueError     → value_error_status（默认 404）
    - 其他 Exception → 500，detail 携带 action 描述
    """
    try:
        yield
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=value_error_status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{action}失败: {str(e)}")
