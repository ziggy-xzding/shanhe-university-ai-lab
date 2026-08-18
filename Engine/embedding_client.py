"""Local Ollama embedding client for Chinese knowledge-base chunks."""

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv


load_dotenv()
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL", "bge-m3"))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))


class EmbeddingClient:
    """Encode chunks through current or legacy Ollama embedding endpoints."""

    def __init__(self, api_key: str | None = None):
        self.provider = os.getenv("EMBEDDING_PROVIDER", EMBEDDING_PROVIDER).lower()
        self.model = os.getenv("OLLAMA_EMBEDDING_MODEL", EMBEDDING_MODEL)
        self.base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL).rstrip("/")
        self.dimension = int(os.getenv("EMBEDDING_DIM", str(EMBEDDING_DIM)))

    def _ollama_request(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model, "input": texts}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
                body = json.loads(response.read().decode("utf-8"))
            vectors = body.get("embeddings") or []
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise RuntimeError(f"Ollama 向量接口返回 HTTP {exc.code}") from exc
            vectors = self._ollama_legacy_request(texts)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接 Ollama：{exc.reason}") from exc
        if len(vectors) != len(texts):
            raise RuntimeError(f"Ollama 返回 {len(vectors)} 条向量，预期 {len(texts)} 条")
        for vector in vectors:
            if len(vector) != self.dimension:
                raise ValueError(f"Ollama 模型 {self.model} 返回 {len(vector)} 维，当前配置要求 {self.dimension} 维")
        return vectors

    def _ollama_legacy_request(self, texts: list[str]) -> list[list[float]]:
        """Fallback for Ollama versions that expose /api/embeddings only."""
        vectors = []
        for text in texts:
            payload = json.dumps({"model": self.model, "prompt": text}, ensure_ascii=False).encode("utf-8")
            request = urllib.request.Request(
                f"{self.base_url}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
                    body = json.loads(response.read().decode("utf-8"))
                vector = body.get("embedding") or []
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"Ollama 新旧向量接口均不可用，旧接口返回 HTTP {exc.code}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"无法连接 Ollama：{exc.reason}") from exc
            vectors.append(vector)
        return vectors

    def _request(self, texts: list[str]) -> list[list[float]]:
        if self.provider != "ollama":
            raise RuntimeError("当前项目已切换为本地 Ollama 向量模型，请将 EMBEDDING_PROVIDER 设置为 ollama")
        return self._ollama_request(texts)

    def encode(self, text: str) -> list[float]:
        return self._request([text])[0]

    def encode_batch(self, texts: list[str], batch_size: int = 10, retry_delay: float = 0) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("待向量化文本必须是非空字符串")
        vectors = []
        for start in range(0, len(texts), max(1, batch_size)):
            vectors.extend(self._request(texts[start : start + max(1, batch_size)]))
        return vectors


_embedding_instance: EmbeddingClient | None = None


def get_embedding() -> EmbeddingClient:
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = EmbeddingClient()
    return _embedding_instance
