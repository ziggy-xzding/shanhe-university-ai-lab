"""Local FAISS knowledge service using Ollama embeddings and DeepSeek generation."""

from __future__ import annotations

import io
import os
import re
import sys
import time

import pdfplumber

from .embedding_client import get_embedding
from .llm_client import get_llm
from .milvus_client import COLLECTIONS, FAISSManager, get_milvus


class KnowledgeService:
    """Small local RAG service kept for the demo compatibility API."""

    def _get_store(self) -> FAISSManager:
        return get_milvus()

    def ask(self, collection_key: str, question: str, top_k: int = 5) -> dict:
        store = self._get_store()
        collection = COLLECTIONS.get(collection_key, collection_key)
        if not store.has_collection(collection):
            return {"question": question, "answer": "知识库尚未初始化，请先上传或导入文档。", "sources": []}

        try:
            query_vec = get_embedding().encode(question)
        except Exception as exc:
            return {"question": question, "answer": f"向量编码失败：{exc}", "sources": []}

        hits = store.search(collection, query_vec, top_k=top_k)
        if not hits:
            return {"question": question, "answer": "未找到相关文档内容，请换一个更具体的问法。", "sources": []}

        try:
            answer = get_llm().generate_rag_answer(question, hits[:5])
        except Exception as exc:
            answer = "以下是检索到的相关原文片段：\n\n" + "\n\n".join(
                f"【片段 {index}】{hit['text'][:300]}..." for index, hit in enumerate(hits[:3], start=1)
            )
            answer += f"\n\n（LLM 生成失败：{exc}）"
        return {"question": question, "answer": answer, "sources": hits[:10]}

    def get_status(self, collection_key: str) -> dict:
        store = self._get_store()
        collection = COLLECTIONS.get(collection_key, collection_key)
        model = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
        llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
        if not store.has_collection(collection):
            return {
                "ready": False,
                "collection": collection,
                "total_chunks": 0,
                "message": "知识库未初始化",
                "embedding_model": model,
                "embedding_dim": 1024,
                "llm_model": llm_model,
            }
        count = store.count(collection)
        return {
            "ready": True,
            "collection": collection,
            "total_chunks": count,
            "message": f"知识库已就绪，共 {count} 条",
            "embedding_model": model,
            "embedding_dim": 1024,
            "llm_model": llm_model,
        }

    def rebuild_sanguo(self) -> dict:
        """Rebuild the demo corpus from NOVEL_SOURCE_FILE or data/novels."""
        source_file = os.getenv(
            "NOVEL_SOURCE_FILE",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "novels", "三国演义.txt"),
        )
        with open(source_file, "r", encoding="utf-8") as handle:
            text = handle.read()
        body = text.split("========正文========", 1)[-1].strip()
        body = re.sub(r"</?p>", "", body).strip()
        sentences = re.split(r"(?<=[。！？；])", body)
        chunks, current = [], ""
        for sentence in sentences:
            if len(current) + len(sentence) <= 500:
                current += sentence
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = (current[-50:] if len(current) > 50 else "") + sentence
        if current.strip():
            chunks.append(current.strip())

        store = self._get_store()
        embedding = get_embedding()
        collection = COLLECTIONS["sanguo"]
        store.create_collection(collection)
        for start in range(0, len(chunks), 10):
            batch = chunks[start : start + 10]
            vectors = []
            for item in batch:
                vectors.append(embedding.encode(item))
                time.sleep(0.15)
            metadata = [{"chunk_index": start + index, "book_name": "三国演义"} for index in range(len(batch))]
            store.add_batch(collection, batch, vectors, metadata)
        return {"success": True, "total_chunks": store.count(collection), "collection": collection}

    def ingest_pdf(self, pdf_bytes: bytes, filename: str) -> dict:
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    pages.append(f"[第 {index} 页]\n{text}")
        full_text = "\n\n".join(pages)
        sentences = re.split(r"(?<=[。！？；])", full_text)
        chunks, current = [], ""
        for sentence in sentences:
            if len(current) + len(sentence) <= 500:
                current += sentence
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = (current[-50:] if len(current) > 50 else "") + sentence
        if current.strip():
            chunks.append(current.strip())

        store = self._get_store()
        embedding = get_embedding()
        collection = COLLECTIONS["windfarm"]
        store.create_collection(collection)
        for start in range(0, len(chunks), 5):
            batch = chunks[start : start + 5]
            vectors = [embedding.encode(item) for item in batch]
            metadata = [{"source": filename, "page": 0, "chunk_index": start + index} for index in range(len(batch))]
            store.add_batch(collection, batch, vectors, metadata)
        return {
            "success": True,
            "total_chunks": len(chunks),
            "inserted": store.count(collection),
            "collection": collection,
            "filename": filename,
        }

    def clear(self, collection_key: str) -> dict:
        collection = COLLECTIONS.get(collection_key, collection_key)
        ok = self._get_store().delete_collection(collection)
        return {"success": ok, "collection": collection, "message": "知识库已清空"}


_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service

