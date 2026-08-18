"""向量存储 — FAISS 内存向量索引（无需 Docker，稳定可靠）"""
import os
import pickle
import numpy as np
import faiss

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "faiss")
COLLECTIONS = {
    "sanguo": "sanguo_chunks",
    "windfarm": "windfarm_chunks",
}


class FAISSManager:
    """FAISS 向量存储 — 内存索引 + 文件持久化"""

    def __init__(self, data_dir: str = DATA_DIR):
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._indices = {}       # collection_name -> faiss index
        self._documents = {}     # collection_name -> list of texts
        self._metadatas = {}     # collection_name -> list of metadata dicts
        self._loaded = set()

    def _path(self, name: str) -> str:
        return os.path.join(self._data_dir, f"{name}.pkl")

    def has_collection(self, name: str) -> bool:
        if name in self._loaded:
            return True
        return os.path.exists(self._path(name))

    def _load(self, name: str):
        """惰性从磁盘加载"""
        if name in self._loaded:
            return
        path = self._path(name)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self._indices[name] = data['index']
            self._documents[name] = data['documents']
            self._metadatas[name] = data['metadatas']
            self._loaded.add(name)

    def _save(self, name: str):
        path = self._path(name)
        with open(path, 'wb') as f:
            pickle.dump({
                'index': self._indices[name],
                'documents': self._documents[name],
                'metadatas': self._metadatas[name],
            }, f)

    def create_collection(self, name: str):
        """创建新的 collection（如果已有则覆盖）"""
        self._indices[name] = faiss.IndexFlatIP(1024)  # Inner Product (需先 normalize)
        self._documents[name] = []
        self._metadatas[name] = []
        self._loaded.add(name)

    def add_batch(self, name: str, documents: list, embeddings: list,
                  metadatas: list = None):
        """批量添加向量"""
        if name not in self._loaded:
            self._load(name)

        arr = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(arr)  # L2归一化 → 内积=余弦相似度
        self._indices[name].add(arr)
        self._documents[name].extend(documents)
        if metadatas:
            self._metadatas[name].extend(metadatas)
        else:
            self._metadatas[name].extend([{}] * len(documents))
        self._save(name)

    def search(self, name: str, query_embedding: list, top_k: int = 5) -> list:
        """向量检索"""
        if name not in self._loaded:
            self._load(name)
        if name not in self._indices or self._indices[name].ntotal == 0:
            return []

        qv = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(qv)
        D, I = self._indices[name].search(qv, min(top_k, self._indices[name].ntotal))

        hits = []
        for i in range(len(I[0])):
            idx = I[0][i]
            if idx < 0 or idx >= len(self._documents[name]):
                continue
            meta = self._metadatas[name][idx] if idx < len(self._metadatas[name]) else {}
            hits.append({
                "id": str(idx),
                "text": self._documents[name][idx],
                "score": round(float(D[0][i]), 4),
                "page": meta.get("page", 0),
                "source": meta.get("source", ""),
                "chunk_index": meta.get("chunk_index", idx),
                "book_name": meta.get("book_name", ""),
            })
        return hits

    def count(self, name: str) -> int:
        if name not in self._loaded:
            if not os.path.exists(self._path(name)):
                return 0
            self._load(name)
        return len(self._documents.get(name, []))

    def delete_collection(self, name: str) -> bool:
        try:
            self._indices.pop(name, None)
            self._documents.pop(name, None)
            self._metadatas.pop(name, None)
            self._loaded.discard(name)
            path = self._path(name)
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False

    def list_collections(self) -> list:
        return [f[:-4] for f in os.listdir(self._data_dir) if f.endswith('.pkl')]


# 全局单例
_faiss_instance: FAISSManager | None = None


def get_milvus() -> FAISSManager:
    global _faiss_instance
    if _faiss_instance is None:
        _faiss_instance = FAISSManager()
    return _faiss_instance
