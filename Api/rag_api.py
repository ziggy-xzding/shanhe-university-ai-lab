"""四大名著 RAG 正式 API。"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from rag_core.errors import RAGConfigurationError, RAGServiceUnavailableError
from rag_core.services.rag_service import RAGService, get_rag_service
from Schema.qa_schema import (
    AskRequest,
    AskResponse,
    DocumentSearchRequest,
    DocumentSourceItem,
    StatusResponse,
)


rag_router = APIRouter(prefix="/api/rag", tags=["四大名著 RAG"])


def _service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (RAGConfigurationError, RAGServiceUnavailableError)):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="RAG 服务发生未预期错误")


@rag_router.post("/sanguo/ask", response_model=AskResponse, summary="三国演义 RAG 问答")
async def ask_sanguo(
    request: AskRequest,
    service: RAGService = Depends(get_rag_service),
):
    try:
        return await asyncio.to_thread(
            service.ask_sanguo,
            request.question,
            request.top_k,
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@rag_router.post(
    "/documents/search",
    response_model=list[DocumentSourceItem],
    summary="四大名著文档混合检索",
)
async def search_documents(
    request: DocumentSearchRequest,
    service: RAGService = Depends(get_rag_service),
):
    try:
        return await asyncio.to_thread(
            service.search_documents,
            request.query,
            request.top_k,
            request.book_name,
        )
    except Exception as exc:
        raise _service_error(exc) from exc


@rag_router.get("/status", response_model=StatusResponse, summary="RAG 知识库状态")
async def rag_status(service: RAGService = Depends(get_rag_service)):
    return await asyncio.to_thread(service.get_status)
