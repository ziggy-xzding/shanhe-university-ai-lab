"""三国问答、文档检索和只读状态编排。"""

from functools import lru_cache
from typing import Any

from db.vdb_init_milvus import DOCUMENT_COLLECTION, QA_COLLECTION, connect_milvus
from rag_core.clients.llm_client import LLMClient
from rag_core.config import RAGSettings, get_settings
from rag_core.retrievers.milvus_retriever import MilvusHybridRetriever


class RAGService:
    def __init__(
        self,
        settings: RAGSettings | None = None,
        *,
        retriever: MilvusHybridRetriever | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.settings = settings or get_settings()
        self._retriever = retriever
        self._llm_client = llm_client

    @property
    def retriever(self) -> MilvusHybridRetriever:
        if self._retriever is None:
            self._retriever = MilvusHybridRetriever(self.settings)
        return self._retriever

    @property
    def llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient(self.settings)
        return self._llm_client

    def search_documents(
        self,
        query: str,
        top_k: int = 5,
        book_name: str | None = None,
    ) -> list[dict]:
        return self.retriever.search_documents(query, top_k, book_name)

    def ask_sanguo(self, question: str, top_k: int = 5) -> dict[str, Any]:
        question = question.strip()
        query_vector = self.retriever.embed_query(question)
        qa_sources = self.retriever.search_qa_pairs(
            question,
            top_k,
            query_vector=query_vector,
        )
        document_sources = self.retriever.search_documents(
            question,
            top_k,
            "三国演义",
            query_vector=query_vector,
        )
        answer = self.llm_client.generate_rag_answer(
            question,
            qa_sources,
            document_sources,
        )
        return {
            "question": question,
            "answer": answer,
            "qa_sources": qa_sources,
            "document_sources": document_sources,
            "sources": document_sources,
        }

    def get_status(self) -> dict[str, Any]:
        base = {
            "ready": False,
            "milvus_connected": False,
            "database": self.settings.milvus_database,
            "document_collection": DOCUMENT_COLLECTION,
            "qa_collection": QA_COLLECTION,
            "document_count": 0,
            "qa_count": 0,
            "embedding_model": self.settings.embedding_model,
            "embedding_dim": self.settings.embedding_dim,
            "llm_model": self.settings.llm_model,
            "message": "",
        }
        try:
            client = connect_milvus(self.settings, ensure_database=False)
            databases = set(client.list_databases())
            base["milvus_connected"] = True
            if self.settings.milvus_database not in databases:
                base["message"] = "Milvus 已连接，但 ai0522 数据库尚未初始化"
                return base
            client.use_database(self.settings.milvus_database)
            doc_exists = client.has_collection(DOCUMENT_COLLECTION)
            qa_exists = client.has_collection(QA_COLLECTION)
            if doc_exists:
                base["document_count"] = int(
                    client.get_collection_stats(DOCUMENT_COLLECTION).get("row_count", 0)
                )
            if qa_exists:
                base["qa_count"] = int(
                    client.get_collection_stats(QA_COLLECTION).get("row_count", 0)
                )
            base["ready"] = bool(
                doc_exists
                and qa_exists
                and base["document_count"] > 0
                and base["qa_count"] == 50
            )
            base["message"] = (
                "知识库就绪"
                if base["ready"]
                else "Collection 尚未完成入库，请运行 python scripts/init_rag.py"
            )
            return base
        except Exception as exc:
            base["message"] = "Milvus 不可用，请确认 Docker 服务已启动且 19530 端口可访问"
            return base


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService()
