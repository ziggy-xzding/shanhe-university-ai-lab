"""Background book ingestion for the campus knowledge base.

The registry is intentionally file-backed for the local demo. The service keeps
the state transitions explicit so it can be moved to a queue and a database
without changing the API contract later.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import threading
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "data" / "knowledge_books"
CHUNK_DIR = BOOK_DIR / "chunks"
REGISTRY_PATH = BOOK_DIR / "registry.json"
_LOCK = threading.RLock()
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="knowledge-book")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)


def _read_registry() -> list[dict]:
    _ensure_dirs()
    if not REGISTRY_PATH.exists():
        return []
    try:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, ValueError):
        return []


def _write_registry(items: list[dict]) -> None:
    _ensure_dirs()
    temporary = REGISTRY_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REGISTRY_PATH)


def _update(book_id: str, **changes) -> dict | None:
    with _LOCK:
        items = _read_registry()
        target = next((item for item in items if item.get("book_id") == book_id), None)
        if not target:
            return None
        target.update(changes)
        target["updated_at"] = _now()
        _write_registry(items)
        return dict(target)


def _get(book_id: str) -> dict | None:
    with _LOCK:
        return next((dict(item) for item in _read_registry() if item.get("book_id") == book_id), None)


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value.strip())
    return cleaned[:80] or "未命名书籍"


def _read_text(path: Path) -> str:
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if path.suffix.lower() == ".docx":
        from docx import Document
        return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    return ""


def _split_text(text: str, chunk_size: int = 900, overlap: int = 140) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not normalized:
        return []
    step = max(1, chunk_size - overlap)
    return [normalized[index : index + chunk_size].strip() for index in range(0, len(normalized), step) if normalized[index : index + chunk_size].strip()]


def _chunk_path(book_id: str) -> Path:
    return CHUNK_DIR / f"{book_id}.json"


def _collection_name(book_id: str) -> str:
    return f"book_{book_id[:24]}"


def _process_book(book_id: str) -> None:
    book = _get(book_id)
    if not book:
        return
    try:
        _update(book_id, status="processing", stage="extracting", progress=10, error=None)
        source_path = BOOK_DIR / book["storage_name"]
        text = _read_text(source_path)
        if not text.strip():
            raise ValueError("书籍未解析出可用文本")

        _update(book_id, stage="chunking", progress=35)
        chunks = []
        for index, content in enumerate(_split_text(text)):
            chunks.append({
                "book_id": book_id,
                "book_name": book["book_name"],
                "version": book["version"],
                "chapter": f"片段 {index + 1}",
                "chunk_index": index,
                "char_count": len(content),
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "content": content,
            })
        _chunk_path(book_id).write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
        _update(book_id, stage="vectorizing", progress=55, chunks=len(chunks), embedded_chunks=0)

        from Engine.embedding_client import get_embedding
        from Engine.milvus_client import get_milvus

        texts = [item["content"] for item in chunks]
        vectors = get_embedding().encode_batch(texts, batch_size=10)
        store = get_milvus()
        collection = _collection_name(book_id)
        if store.has_collection(collection):
            store.delete_collection(collection)
        store.create_collection(collection)
        metadata = [
            {key: item[key] for key in ("book_id", "book_name", "version", "chapter", "chunk_index", "content_hash")}
            for item in chunks
        ]
        store.add_batch(collection, texts, vectors, metadata)
        _update(book_id, status="ready", stage="ready", progress=100, embedded_chunks=len(vectors), collection=collection, error=None)
    except Exception as exc:
        _update(book_id, status="failed", stage="failed", error=str(exc)[:500])


def create_uploaded_book(filename: str, book_name: str, content: bytes, uploaded_by: str) -> dict:
    extension = Path(filename).suffix.lower()
    if extension not in {".txt", ".pdf", ".docx"}:
        raise ValueError("知识库仅支持 .txt、.pdf、.docx 书籍文件")
    safe_name = _safe_name(book_name)
    with _LOCK:
        items = _read_registry()
        versions = [item.get("version", 0) for item in items if item.get("book_name") == safe_name]
        version = max(versions or [0]) + 1
        book_id = uuid4().hex
        storage_name = f"{book_id}{extension}"
        _ensure_dirs()
        (BOOK_DIR / storage_name).write_bytes(content)
        entry = {
            "book_id": book_id,
            "book_name": safe_name,
            "version": version,
            "is_latest": True,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "source": filename,
            "storage_name": storage_name,
            "uploaded_by": uploaded_by,
            "uploaded_at": _now(),
            "updated_at": _now(),
            "chunks": 0,
            "embedded_chunks": 0,
            "error": None,
        }
        for item in items:
            if item.get("book_name") == safe_name:
                item["is_latest"] = False
        items.append(entry)
        _write_registry(items)
    _EXECUTOR.submit(_process_book, book_id)
    return dict(entry)


def retry_book(book_id: str) -> dict | None:
    book = _get(book_id)
    if not book:
        return None
    _update(book_id, status="queued", stage="queued", progress=0, error=None)
    _EXECUTOR.submit(_process_book, book_id)
    return _get(book_id)


def list_uploaded_books() -> list[dict]:
    with _LOCK:
        return [dict(item) for item in _read_registry()]


def get_uploaded_book(book_id: str) -> dict | None:
    return _get(book_id)


def uploaded_documents() -> list[dict]:
    documents = []
    for book in list_uploaded_books():
        path = _chunk_path(book.get("book_id", ""))
        if not path.exists():
            continue
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        documents.extend(items)
    return documents


def search_uploaded_books(question: str, limit: int = 3) -> list[dict]:
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", question.lower()))
    terms = {chinese[index : index + 2] for index in range(max(0, len(chinese) - 1))}
    terms.update(re.findall(r"[A-Za-z0-9]+", question.lower()))
    scored = []
    for item in uploaded_documents():
        score = sum(item["content"].lower().count(term) for term in terms)
        if score:
            scored.append((score, {**item, "score": round(min(.99, score / 10), 3)}))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def vector_search_uploaded_books(question: str, limit: int = 3) -> list[dict]:
    try:
        from Engine.embedding_client import get_embedding
        from Engine.milvus_client import get_milvus

        query = get_embedding().encode(question)
        store = get_milvus()
        hits = []
        for book in list_uploaded_books():
            if book.get("status") != "ready" or not book.get("collection"):
                continue
            for item in store.search(book["collection"], query, top_k=limit):
                hits.append({
                    "book_id": book["book_id"],
                    "book_name": item.get("book_name") or book["book_name"],
                    "version": item.get("version") or book["version"],
                    "chapter": item.get("chapter") or "片段",
                    "content": item.get("text", "")[:420],
                    "score": item.get("score", 0),
                })
        hits.sort(key=lambda item: item.get("score", 0), reverse=True)
        return hits[:limit]
    except Exception:
        return []
