"""三国演义问答兼容路由。正式接口位于 /api/rag。"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException

from Schema.qa_schema import AskRequest, AskResponse, StatusResponse
from rag_core.errors import RAGConfigurationError, RAGServiceUnavailableError
from rag_core.services.rag_service import RAGService, get_rag_service

sanguo_router = APIRouter(prefix="/sanguo", tags=["三国问答"])


@sanguo_router.post("/ask", response_model=AskResponse,
                    summary="向三国演义知识库提问")
async def sanguo_ask(req: AskRequest, svc: RAGService = Depends(get_rag_service)):
    try:
        return await asyncio.to_thread(svc.ask_sanguo, req.question, req.top_k)
    except (RAGConfigurationError, RAGServiceUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@sanguo_router.get("/status", response_model=StatusResponse,
                   summary="查看三国知识库状态")
async def sanguo_status(svc: RAGService = Depends(get_rag_service)):
    return await asyncio.to_thread(svc.get_status)
