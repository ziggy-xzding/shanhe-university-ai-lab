"""RAG 知识问答模块的 Pydantic 请求/响应模型。"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """提问请求"""
    question: str = Field(..., min_length=1, max_length=2000,
                          examples=["桃园三结义是哪三个人？"])
    top_k: int = Field(5, ge=1, le=20, description="检索返回的段落数")


class SourceItem(BaseModel):
    """兼容旧页面的文档来源片段。"""
    id: int | str | None = None
    text: str = ""
    content: str = ""
    score: float
    page: int = 0
    source: str = ""
    file_name: str = ""
    chunk_index: int = 0
    book_name: str = ""
    chapter: str = ""


class QASourceItem(BaseModel):
    id: int | str | None = None
    question: str
    answer: str
    explanation: str = ""
    evidence: str = ""
    source_book: str = ""
    source_chapter: str = ""
    score: float


class DocumentSourceItem(BaseModel):
    id: int | str | None = None
    content: str
    score: float
    book_name: str = ""
    chapter: str = ""
    source: str = ""
    chunk_index: int = 0
    char_count: int = 0


class AskResponse(BaseModel):
    """问答响应"""
    question: str
    answer: str
    qa_sources: list[QASourceItem] = Field(default_factory=list)
    document_sources: list[DocumentSourceItem] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)


class StatusResponse(BaseModel):
    """知识库状态"""
    ready: bool
    milvus_connected: bool = False
    database: str = ""
    document_collection: str = ""
    qa_collection: str = ""
    document_count: int = 0
    qa_count: int = 0
    collection: str = ""
    total_chunks: int = 0
    embedding_model: str = ""
    embedding_dim: int = 0
    llm_model: str = ""
    message: str = ""


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    book_name: str | None = Field(None, max_length=128)


class IngestResponse(BaseModel):
    """入库响应"""
    success: bool
    total_chunks: int = 0
    inserted: int = 0
    collection: str = ""
    filename: str = ""
    message: str = ""


class ClearResponse(BaseModel):
    """清空响应"""
    success: bool
    collection: str = ""
    message: str = ""
