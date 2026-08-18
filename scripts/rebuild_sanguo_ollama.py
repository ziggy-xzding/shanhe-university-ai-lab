"""Rebuild the local 三国演义 FAISS index with the Ollama embedding model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Engine.embedding_client import get_embedding
from Engine.milvus_client import COLLECTIONS, get_milvus
from Service.multi_agent_service import _sanguo_documents


def main() -> None:
    documents = _sanguo_documents()
    if not documents:
        raise SystemExit("未找到 data/faiss/sanguo_chunks.pkl 中的原文片段")
    store = get_milvus()
    embedding = get_embedding()
    collection = COLLECTIONS["sanguo"]
    store.create_collection(collection)
    batch_size = 10
    for start in range(0, len(documents), batch_size):
        batch = documents[start : start + batch_size]
        texts = [item.get("content", "") for item in batch]
        vectors = embedding.encode_batch(texts, batch_size=batch_size)
        metadata = [
            {
                "chunk_index": start + index,
                "book_name": item.get("book_name") or "三国演义",
                "chapter": item.get("chapter", ""),
            }
            for index, item in enumerate(batch)
        ]
        store.add_batch(collection, texts, vectors, metadata)
        print(f"[{min(start + batch_size, len(documents))}/{len(documents)}]")
    print(f"已使用 Ollama/{embedding.model} 重建 {store.count(collection)} 个知识片段")


if __name__ == "__main__":
    main()
