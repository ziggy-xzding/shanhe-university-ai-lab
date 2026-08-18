"""Milvus 1024 维稠密检索 + BM25 稀疏检索 + RRF。"""

from typing import Any

from pymilvus import AnnSearchRequest, Function, FunctionType, MilvusClient

from db.vdb_init_milvus import DOCUMENT_COLLECTION, QA_COLLECTION, connect_milvus
from rag_core.clients.embedding_client import EmbeddingClient
from rag_core.config import RAGSettings, get_settings
from rag_core.errors import RAGServiceUnavailableError


def _escape_milvus_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MilvusHybridRetriever:
    def __init__(
        self,
        settings: RAGSettings | None = None,
        *,
        client: MilvusClient | None = None,
        embedding_client: EmbeddingClient | None = None,
    ):
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
        else:
            try:
                self.client = connect_milvus(self.settings, ensure_database=False)
            except Exception as exc:
                raise RAGServiceUnavailableError(
                    "无法连接 Milvus，请确认 Docker 服务已启动且 MILVUS_URI 配置正确"
                ) from exc
        self.embedding_client = embedding_client or EmbeddingClient(self.settings)
        self._loaded: set[str] = set()

    def embed_query(self, query: str) -> list[float]:
        if not query or not query.strip():
            raise ValueError("query 不能为空")
        return self.embedding_client.embed_text(query.strip())

    def _load(self, collection_name: str) -> None:
        if collection_name in self._loaded:
            return
        if not self.client.has_collection(collection_name):
            raise RAGServiceUnavailableError(
                f"Milvus Collection {collection_name} 不存在，请先运行 python scripts/init_rag.py"
            )
        self.client.load_collection(collection_name)
        self._loaded.add(collection_name)

    def _hybrid_search(
        self,
        *,
        collection_name: str,
        query: str,
        query_vector: list[float],
        top_k: int,
        output_fields: list[str],
        filter_expression: str = "",
    ) -> list[dict]:
        if not 1 <= top_k <= 20:
            raise ValueError("top_k 必须在 1~20 之间")
        if len(query_vector) != self.settings.embedding_dim:
            raise ValueError(
                f"查询向量维度为 {len(query_vector)}，预期 {self.settings.embedding_dim}"
            )
        self._load(collection_name)
        request_limit = min(max(top_k * 2, top_k), 50)
        common: dict[str, Any] = {"limit": request_limit}
        if filter_expression:
            common["expr"] = filter_expression
        dense_request = AnnSearchRequest(
            data=[query_vector],
            anns_field="dense_vector",
            param={"metric_type": "COSINE", "params": {}},
            **common,
        )
        sparse_request = AnnSearchRequest(
            data=[query],
            anns_field="sparse_vector",
            param={"metric_type": "BM25", "params": {}},
            **common,
        )
        ranker = Function(
            name="rrf_ranker",
            input_field_names=[],
            function_type=FunctionType.RERANK,
            params={"reranker": "rrf", "k": self.settings.rrf_k},
        )
        try:
            result = self.client.hybrid_search(
                collection_name=collection_name,
                reqs=[dense_request, sparse_request],
                ranker=ranker,
                limit=top_k,
                output_fields=output_fields,
            )
        except Exception as exc:
            raise RAGServiceUnavailableError(f"Milvus 混合检索失败：{exc}") from exc

        hits = result[0] if result else []
        normalized: list[dict] = []
        for hit in hits:
            entity = hit.get("entity") or {}
            item = dict(entity)
            item["id"] = hit.get("id")
            item["score"] = round(float(hit.get("distance", 0.0)), 6)
            normalized.append(item)
        return normalized

    def search_documents(
        self,
        query: str,
        top_k: int = 5,
        book_name: str | None = None,
        *,
        query_vector: list[float] | None = None,
    ) -> list[dict]:
        expression = ""
        if book_name:
            expression = f'book_name == "{_escape_milvus_string(book_name)}"'
        vector = query_vector or self.embed_query(query)
        return self._hybrid_search(
            collection_name=DOCUMENT_COLLECTION,
            query=query,
            query_vector=vector,
            top_k=top_k,
            filter_expression=expression,
            output_fields=[
                "content",
                "book_name",
                "chapter",
                "source",
                "chunk_index",
                "char_count",
            ],
        )

    def search_qa_pairs(
        self,
        query: str,
        top_k: int = 5,
        *,
        query_vector: list[float] | None = None,
    ) -> list[dict]:
        vector = query_vector or self.embed_query(query)
        return self._hybrid_search(
            collection_name=QA_COLLECTION,
            query=query,
            query_vector=vector,
            top_k=top_k,
            output_fields=[
                "question",
                "answer",
                "explanation",
                "evidence",
                "source_book",
                "source_chapter",
            ],
        )
