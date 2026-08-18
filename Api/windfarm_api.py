"""风电工程文档知识库 API"""
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from Api.api_utils import service_call
from Schema.qa_schema import AskRequest, AskResponse, StatusResponse, IngestResponse, ClearResponse
from Engine.knowledge_service import get_knowledge_service, KnowledgeService

windfarm_router = APIRouter(prefix="/windfarm", tags=["风电知识库"])


def get_service() -> KnowledgeService:
    return get_knowledge_service()


@windfarm_router.post("/ask", response_model=AskResponse,
                      summary="向风电工程知识库提问")
async def windfarm_ask(req: AskRequest, svc=Depends(get_service)):
    """基于风电工程文档进行 RAG 问答"""
    async with service_call("风电知识问答"):
        return svc.ask("windfarm", req.question, req.top_k)


@windfarm_router.post("/ingest", response_model=IngestResponse,
                      summary="上传风电文档 PDF 入库")
async def windfarm_ingest(file: UploadFile = File(...), svc=Depends(get_service)):
    """上传 PDF 文档，自动分块向量化并存入 Milvus 知识库"""
    async with service_call("风电文档入库", value_error_status=400):
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise ValueError("上传文件为空")
        return svc.ingest_pdf(pdf_bytes, file.filename or "unknown.pdf")


@windfarm_router.get("/status", response_model=StatusResponse,
                     summary="查看风电知识库状态")
async def windfarm_status(svc=Depends(get_service)):
    async with service_call("查询风电知识库状态"):
        return svc.get_status("windfarm")


@windfarm_router.delete("/clear", response_model=ClearResponse,
                        summary="清空风电知识库")
async def windfarm_clear(svc=Depends(get_service)):
    async with service_call("清空风电知识库"):
        return svc.clear("windfarm")
