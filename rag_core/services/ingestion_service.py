"""四本原著和 50 条三国问答的幂等入库服务。"""

import hashlib
import json
from pathlib import Path
import time
from typing import Any

from pymilvus import MilvusClient

from db.vdb_init_milvus import (
    DOCUMENT_COLLECTION,
    QA_COLLECTION,
    connect_milvus,
    create_document_collection,
    create_qa_collection,
)
from rag_core.clients.embedding_client import EmbeddingClient
from rag_core.config import PROJECT_ROOT, RAGSettings, get_settings
from rag_core.utils.file_utils import read_document
from rag_core.utils.text_splitter import TextChunker


NOVEL_FILES = {
    "三国演义": "《三国演义》.txt",
    "水浒传": "水浒传.txt",
    "红楼梦": "红楼梦.txt",
    "西游记": "西游记.txt",
}
DEFAULT_QA_PATH = PROJECT_ROOT / "data" / "qa_pairs.json"


def _sha256(*values: str) -> str:
    payload = "\0".join(values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _retrieval_text(item: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"问题：{item['question']}",
            f"答案：{item['answer']}",
            f"说明：{item['explanation']}",
            f"原文依据：{item['evidence']}",
        ]
    )


def load_qa_pairs(path: str | Path = DEFAULT_QA_PATH) -> list[dict[str, str]]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list) or len(data) != 50:
        raise ValueError(f"{file_path} 必须是恰好包含 50 条数据的 JSON 数组")
    required = {
        "question",
        "answer",
        "explanation",
        "evidence",
        "source_book",
        "source_chapter",
    }
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(data, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"第 {index} 条问答不是 JSON 对象")
        missing = required - raw.keys()
        if missing:
            raise ValueError(f"第 {index} 条问答缺少字段：{', '.join(sorted(missing))}")
        item = {key: str(raw[key]).strip() for key in required}
        if any(not item[key] for key in required):
            raise ValueError(f"第 {index} 条问答存在空字段")
        if item["source_book"] != "三国演义":
            raise ValueError(f"第 {index} 条问答 source_book 必须为“三国演义”")
        if item["question"] in seen:
            raise ValueError(f"问答问题重复：{item['question']}")
        seen.add(item["question"])
        normalized.append(item)
    return normalized


class IngestionService:
    def __init__(
        self,
        settings: RAGSettings | None = None,
        *,
        client: MilvusClient | None = None,
        embedding_client: EmbeddingClient | None = None,
    ):
        self.settings = settings or get_settings()
        self.client = client or connect_milvus(self.settings, ensure_database=True)
        self.embedding_client = embedding_client or EmbeddingClient(self.settings)
        self.chunker = TextChunker(
            self.settings.chunk_size,
            self.settings.chunk_overlap,
        )

    def _existing_hashes(
        self,
        collection: str,
        field: str,
        hashes: list[str],
    ) -> set[str]:
        if not hashes:
            return set()
        values = ", ".join(json.dumps(value) for value in hashes)
        rows = self.client.query(
            collection_name=collection,
            filter=f"{field} in [{values}]",
            output_fields=[field],
            limit=len(hashes),
        )
        return {str(row[field]) for row in rows}

    def _insert_with_retry(self, collection: str, rows: list[dict]) -> int:
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                result = self.client.insert(collection_name=collection, data=rows)
                return int(result.get("insert_count", len(rows)))
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"写入 {collection} 失败：{last_error}") from last_error

    def ingest_novels(self, *, recreate: bool = False) -> dict[str, Any]:
        create_document_collection(
            self.client,
            embedding_dim=self.settings.embedding_dim,
            recreate=recreate,
        )
        self.client.load_collection(DOCUMENT_COLLECTION)
        source_dir = self.settings.novel_source_dir
        results: dict[str, Any] = {}
        total_inserted = 0
        for book_name, filename in NOVEL_FILES.items():
            started = time.monotonic()
            path = source_dir / filename
            text = read_document(path)
            chunks = self.chunker.split(
                text,
                {"book_name": book_name, "source": str(path)},
            )
            for chunk in chunks:
                chunk["content_hash"] = _sha256(
                    book_name,
                    chunk["chapter"],
                    chunk["content"],
                )

            inserted = 0
            skipped = 0
            for start in range(0, len(chunks), self.settings.batch_size):
                batch = chunks[start : start + self.settings.batch_size]
                hashes = [item["content_hash"] for item in batch]
                existing = self._existing_hashes(
                    DOCUMENT_COLLECTION,
                    "content_hash",
                    hashes,
                )
                pending = [item for item in batch if item["content_hash"] not in existing]
                skipped += len(batch) - len(pending)
                if not pending:
                    continue
                vectors = self.embedding_client.embed_texts(
                    [item["content"] for item in pending]
                )
                rows = []
                for item, vector in zip(pending, vectors):
                    rows.append(
                        {
                            "content": item["content"],
                            "book_name": item["book_name"],
                            "chapter": item["chapter"],
                            "source": item["source"],
                            "chunk_index": item["chunk_index"],
                            "char_count": item["char_count"],
                            "content_hash": item["content_hash"],
                            "dense_vector": vector,
                        }
                    )
                inserted += self._insert_with_retry(DOCUMENT_COLLECTION, rows)
                processed = min(start + len(batch), len(chunks))
                if processed % 100 == 0 or processed == len(chunks):
                    print(
                        f"[{book_name}] {processed}/{len(chunks)} "
                        f"inserted={inserted} skipped={skipped}",
                        flush=True,
                    )
            total_inserted += inserted
            results[book_name] = {
                "chunks": len(chunks),
                "inserted": inserted,
                "skipped": skipped,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            }
        self.client.flush(DOCUMENT_COLLECTION)
        self.client.load_collection(DOCUMENT_COLLECTION)
        return {"collection": DOCUMENT_COLLECTION, "inserted": total_inserted, "books": results}

    def ingest_qa_pairs(
        self,
        path: str | Path = DEFAULT_QA_PATH,
        *,
        recreate: bool = False,
    ) -> dict[str, Any]:
        create_qa_collection(
            self.client,
            embedding_dim=self.settings.embedding_dim,
            recreate=recreate,
        )
        self.client.load_collection(QA_COLLECTION)
        items = load_qa_pairs(path)
        rows: list[dict[str, Any]] = []
        for item in items:
            retrieval_text = _retrieval_text(item)
            rows.append(
                {
                    **item,
                    "retrieval_text": retrieval_text,
                    "qa_hash": _sha256(item["question"], item["answer"]),
                }
            )

        inserted = 0
        skipped = 0
        for start in range(0, len(rows), self.settings.batch_size):
            batch = rows[start : start + self.settings.batch_size]
            hashes = [item["qa_hash"] for item in batch]
            existing = self._existing_hashes(QA_COLLECTION, "qa_hash", hashes)
            pending = [item for item in batch if item["qa_hash"] not in existing]
            skipped += len(batch) - len(pending)
            if not pending:
                continue
            vectors = self.embedding_client.embed_texts(
                [item["retrieval_text"] for item in pending]
            )
            for item, vector in zip(pending, vectors):
                item["dense_vector"] = vector
            inserted += self._insert_with_retry(QA_COLLECTION, pending)
            print(
                f"[三国问答] {min(start + len(batch), len(rows))}/{len(rows)} "
                f"inserted={inserted} skipped={skipped}",
                flush=True,
            )
        self.client.flush(QA_COLLECTION)
        self.client.load_collection(QA_COLLECTION)
        return {
            "collection": QA_COLLECTION,
            "total": len(rows),
            "inserted": inserted,
            "skipped": skipped,
        }
