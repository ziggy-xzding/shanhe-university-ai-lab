"""Environment-backed configuration for the optional Milvus RAG service."""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NOVEL_SOURCE_DIR = PROJECT_ROOT / "data" / "novels"


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer; got {raw!r}") from exc


def _as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number; got {raw!r}") from exc


@dataclass(frozen=True)
class RAGSettings:
    """Runtime settings for the optional Milvus-backed RAG pipeline."""

    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    embedding_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "bge-m3"
    # Deprecated aliases kept for compatibility with older callers.
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://api.deepseek.com"
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024
    llm_model: str = "deepseek-chat"
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_database: str = "ai0522"
    milvus_timeout_seconds: float = 3.0
    novel_source_dir: Path = DEFAULT_NOVEL_SOURCE_DIR
    chunk_size: int = 500
    chunk_overlap: int = 80
    batch_size: int = 10
    default_top_k: int = 5
    rrf_k: int = 60

    @classmethod
    def from_env(cls) -> "RAGSettings":
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY", "")
        base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        ollama_embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
        source_dir = Path(os.getenv("NOVEL_SOURCE_DIR", str(DEFAULT_NOVEL_SOURCE_DIR)))
        settings = cls(
            llm_api_key=key.strip(),
            llm_base_url=base_url,
            embedding_provider=embedding_provider,
            ollama_base_url=ollama_base_url,
            ollama_embedding_model=ollama_embedding_model,
            dashscope_api_key=key.strip(),
            dashscope_base_url=base_url,
            embedding_model=os.getenv("EMBEDDING_MODEL", ollama_embedding_model),
            embedding_dim=_as_int("EMBEDDING_DIM", 1024),
            llm_model=os.getenv("LLM_MODEL", "deepseek-chat"),
            milvus_uri=os.getenv("MILVUS_URI", "http://localhost:19530"),
            milvus_token=os.getenv("MILVUS_TOKEN", "").strip(),
            milvus_database=os.getenv("MILVUS_DATABASE", "ai0522"),
            milvus_timeout_seconds=_as_float("MILVUS_TIMEOUT_SECONDS", 3.0),
            novel_source_dir=source_dir,
            chunk_size=_as_int("RAG_CHUNK_SIZE", 500),
            chunk_overlap=_as_int("RAG_CHUNK_OVERLAP", 80),
            batch_size=_as_int("RAG_BATCH_SIZE", 10),
            default_top_k=_as_int("RAG_DEFAULT_TOP_K", 5),
            rrf_k=_as_int("RAG_RRF_K", 60),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.embedding_dim != 1024:
            raise ValueError("EMBEDDING_DIM must be 1024 for the current Milvus schema")
        if self.chunk_size <= 0:
            raise ValueError("RAG_CHUNK_SIZE must be greater than 0")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be in [0, RAG_CHUNK_SIZE)")
        if self.batch_size < 1 or self.batch_size > 10:
            raise ValueError("RAG_BATCH_SIZE must be between 1 and 10")
        if not 1 <= self.default_top_k <= 20:
            raise ValueError("RAG_DEFAULT_TOP_K must be between 1 and 20")
        if self.milvus_timeout_seconds <= 0:
            raise ValueError("MILVUS_TIMEOUT_SECONDS must be greater than 0")
        if self.embedding_provider not in {"ollama"}:
            raise ValueError("EMBEDDING_PROVIDER currently supports only ollama")


@lru_cache(maxsize=1)
def get_settings() -> RAGSettings:
    return RAGSettings.from_env()

