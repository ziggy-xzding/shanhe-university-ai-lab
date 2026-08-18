"""创建 Milvus 数据库、双 Collection、BM25 Function 和向量索引。"""

from typing import Any

from pymilvus import DataType, Function, FunctionType, MilvusClient

from rag_core.config import RAGSettings, get_settings


DOCUMENT_COLLECTION = "novel_chunks"
QA_COLLECTION = "sanguo_qa_pairs"
CHINESE_ANALYZER = {"type": "chinese"}


def _client_kwargs(settings: RAGSettings) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "uri": settings.milvus_uri,
        "timeout": settings.milvus_timeout_seconds,
    }
    if settings.milvus_token:
        kwargs["token"] = settings.milvus_token
    return kwargs


def connect_milvus(
    settings: RAGSettings | None = None,
    *,
    ensure_database: bool = False,
) -> MilvusClient:
    """连接 Milvus；只有显式要求时才创建数据库。"""
    cfg = settings or get_settings()
    client = MilvusClient(**_client_kwargs(cfg))
    databases = set(client.list_databases())
    if cfg.milvus_database not in databases:
        if not ensure_database:
            return client
        client.create_database(cfg.milvus_database)
    client.use_database(cfg.milvus_database)
    return client


def build_document_schema(embedding_dim: int = 1024):
    schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field(
        "content",
        DataType.VARCHAR,
        max_length=8192,
        enable_analyzer=True,
        analyzer_params=CHINESE_ANALYZER,
    )
    schema.add_field("book_name", DataType.VARCHAR, max_length=128)
    schema.add_field("chapter", DataType.VARCHAR, max_length=512)
    schema.add_field("source", DataType.VARCHAR, max_length=1024)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("char_count", DataType.INT64)
    schema.add_field("content_hash", DataType.VARCHAR, max_length=64)
    schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=embedding_dim)
    schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
    schema.add_function(
        Function(
            name="content_bm25",
            function_type=FunctionType.BM25,
            input_field_names=["content"],
            output_field_names=["sparse_vector"],
        )
    )
    return schema


def build_qa_schema(embedding_dim: int = 1024):
    schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field("question", DataType.VARCHAR, max_length=2048)
    schema.add_field("answer", DataType.VARCHAR, max_length=8192)
    schema.add_field("explanation", DataType.VARCHAR, max_length=8192)
    schema.add_field("evidence", DataType.VARCHAR, max_length=8192)
    schema.add_field(
        "retrieval_text",
        DataType.VARCHAR,
        max_length=16384,
        enable_analyzer=True,
        analyzer_params=CHINESE_ANALYZER,
    )
    schema.add_field("source_book", DataType.VARCHAR, max_length=128)
    schema.add_field("source_chapter", DataType.VARCHAR, max_length=512)
    schema.add_field("qa_hash", DataType.VARCHAR, max_length=64)
    schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=embedding_dim)
    schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
    schema.add_function(
        Function(
            name="qa_bm25",
            function_type=FunctionType.BM25,
            input_field_names=["retrieval_text"],
            output_field_names=["sparse_vector"],
        )
    )
    return schema


def build_hybrid_indexes():
    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name="dense_vector",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )
    index_params.add_index(
        field_name="sparse_vector",
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="BM25",
        params={
            "inverted_index_algo": "DAAT_MAXSCORE",
            "bm25_k1": 1.2,
            "bm25_b": 0.75,
        },
    )
    return index_params


def create_document_collection(
    client: MilvusClient,
    *,
    embedding_dim: int = 1024,
    recreate: bool = False,
) -> bool:
    exists = client.has_collection(DOCUMENT_COLLECTION)
    if exists and not recreate:
        return False
    if exists:
        client.drop_collection(DOCUMENT_COLLECTION)
    client.create_collection(
        collection_name=DOCUMENT_COLLECTION,
        schema=build_document_schema(embedding_dim),
        index_params=build_hybrid_indexes(),
    )
    return True


def create_qa_collection(
    client: MilvusClient,
    *,
    embedding_dim: int = 1024,
    recreate: bool = False,
) -> bool:
    exists = client.has_collection(QA_COLLECTION)
    if exists and not recreate:
        return False
    if exists:
        client.drop_collection(QA_COLLECTION)
    client.create_collection(
        collection_name=QA_COLLECTION,
        schema=build_qa_schema(embedding_dim),
        index_params=build_hybrid_indexes(),
    )
    return True


def create_all_collections(
    client: MilvusClient | None = None,
    *,
    settings: RAGSettings | None = None,
    recreate: bool = False,
) -> dict[str, bool]:
    cfg = settings or get_settings()
    active_client = client or connect_milvus(cfg, ensure_database=True)
    return {
        DOCUMENT_COLLECTION: create_document_collection(
            active_client,
            embedding_dim=cfg.embedding_dim,
            recreate=recreate,
        ),
        QA_COLLECTION: create_qa_collection(
            active_client,
            embedding_dim=cfg.embedding_dim,
            recreate=recreate,
        ),
    }


if __name__ == "__main__":
    print(create_all_collections())
