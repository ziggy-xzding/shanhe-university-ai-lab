"""Embedding client with local Ollama as the default provider."""

import json
import time
import urllib.error
import urllib.request
from typing import Any

from openai import OpenAI

from rag_core.config import RAGSettings, get_settings
from rag_core.errors import RAGConfigurationError, RAGServiceUnavailableError


class EmbeddingClient:
    """提供批量向量化、维度校验和本地 Ollama 调用。"""

    def __init__(
        self,
        settings: RAGSettings | None = None,
        *,
        client: Any | None = None,
        max_retries: int = 3,
    ):
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self._client = client
        if self._client is None and self.settings.embedding_provider != "ollama":
            raise RAGConfigurationError("EMBEDDING_PROVIDER 当前必须为 ollama")
        self._ollama_url = self.settings.ollama_base_url.rstrip("/")
        self._ollama_model = self.settings.ollama_embedding_model

    def _request_openai(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
            dimensions=self.settings.embedding_dim,
            encoding_format="float",
        )
        items = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in items]

    def _request_ollama(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps(
            {"model": self._ollama_model, "input": texts}, ensure_ascii=False
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self._ollama_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接 Ollama：{exc.reason}") from exc
        vectors = body.get("embeddings") or []
        if len(vectors) != len(texts):
            raise RuntimeError(f"Ollama 返回 {len(vectors)} 条向量，预期 {len(texts)} 条")
        return vectors

    def _request(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                vectors = self._request_openai(texts) if self._client is not None else self._request_ollama(texts)
                for vector in vectors:
                    if len(vector) != self.settings.embedding_dim:
                        raise ValueError(
                            f"Embedding 维度为 {len(vector)}，预期 {self.settings.embedding_dim}"
                        )
                if len(vectors) != len(texts):
                    raise ValueError(f"Embedding 返回 {len(vectors)} 条，预期 {len(texts)} 条")
                return vectors
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(min(2**attempt, 4))
        raise RAGServiceUnavailableError(f"调用 Ollama 向量服务失败：{last_error}") from last_error

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("待向量化文本必须是非空字符串")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.settings.batch_size):
            vectors.extend(self._request(texts[start : start + self.settings.batch_size]))
        return vectors

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
